from flask import Flask, render_template, request, jsonify, send_file, make_response
import os
import sys
import tempfile
import shutil
import zipfile
import uuid
from werkzeug.utils import secure_filename
import logging
from pathlib import Path
import json
from datetime import datetime
import concurrent.futures
import threading
import time
import argparse
import gc
import psutil
from tools_config import get_active_tools

# Import the video processing functions
from video_converter import (
    process_video,
    get_video_metadata,
    create_square_video,
    create_square_blur_video,
    create_landscape_video,
    create_vertical_blur_video
)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB max file size (reduced for memory)

# Use a persistent directory for uploads instead of temp directory
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Disable Flask's default request logging for cleaner output
import logging as flask_logging
flask_logging.getLogger('werkzeug').setLevel(flask_logging.ERROR)

# Set up logging - reduce verbosity for production
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Create a custom logger for our app
app_logger = logging.getLogger('video_converter')
app_logger.setLevel(logging.INFO)

# Store processing jobs in memory (in production, use Redis or similar)
processing_jobs = {}
job_lock = threading.Lock()
# Store active processing threads for cleanup
active_processing_threads = {}
thread_lock = threading.Lock()

ALLOWED_EXTENSIONS = {'mp4', 'mov'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_job_id():
    return str(uuid.uuid4())

def get_memory_usage():
    """Get current memory usage in MB"""
    try:
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024  # MB
    except:
        return 0

def check_memory_and_cleanup():
    """Check memory usage and force cleanup if needed"""
    memory_mb = get_memory_usage()
    if memory_mb > 1500:  # If over 1.5GB, force cleanup
        app_logger.warning(f"High memory usage detected: {memory_mb:.1f}MB - forcing cleanup")
        gc.collect()
        return True
    return False

def log_memory_usage(context=""):
    """Log current memory usage"""
    memory_mb = get_memory_usage()
    app_logger.info(f"Memory usage {context}: {memory_mb:.1f}MB")

@app.route('/')
def index():
    from tools_config import TOOLS_CONFIG
    tools = get_active_tools()
    return render_template('index.html', tools=tools, tools_config=TOOLS_CONFIG)

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.now().isoformat(),
        'port': request.environ.get('SERVER_PORT', 'unknown')
    })

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files' not in request.files:
        return jsonify({'error': 'No files uploaded'}), 400
    
    files = request.files.getlist('files')
    formats = request.form.getlist('formats')
    
    if not files or not formats:
        return jsonify({'error': 'No files or formats selected'}), 400
    
    # No file count limit - processing is sequential anyway
    
    # Validate files
    valid_files = []
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            valid_files.append(file)
    
    if not valid_files:
        return jsonify({'error': 'No valid video files uploaded'}), 400
    
    # Generate job ID
    job_id = generate_job_id()
    
    # Create job directory
    job_dir = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    # Save uploaded files
    input_files = []
    for i, file in enumerate(valid_files):
        filename = secure_filename(file.filename)
        input_path = os.path.join(job_dir, f"input_{i}_{filename}")
        file.save(input_path)
        input_files.append({
            'path': input_path,
            'original_name': filename
        })
    
    # Initialize job status
    with job_lock:
        processing_jobs[job_id] = {
            'status': 'queued',
            'progress': 0,
            'total_tasks': len(input_files) * len(formats),
            'completed_tasks': 0,
            'results': [],
            'errors': [],
            'created_at': datetime.now().isoformat()
        }
    
    # Start processing in background
    thread = threading.Thread(
        target=process_videos_background,
        args=(job_id, input_files, formats, job_dir)
    )
    thread.daemon = True
    
    # Store thread reference for cleanup
    with thread_lock:
        active_processing_threads[job_id] = thread
    
    thread.start()
    
    return jsonify({'job_id': job_id})

def process_videos_background(job_id, input_files, formats, job_dir):
    """Process videos in background thread"""
    log_memory_usage("before processing")
    
    def should_cancel():
        """Check if processing should be cancelled"""
        with job_lock:
            return job_id not in processing_jobs or processing_jobs[job_id].get('cancel_requested', False)
    
    def print_terminal_progress(progress, task_name="Processing"):
        """Print progress in terminal with single line update"""
        bar_length = 30
        filled_length = int(bar_length * progress // 100)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        print(f'\r🎥 {task_name}: |{bar}| {progress:.1f}% ', end='', flush=True)
        if progress >= 100:
            print()  # New line when complete
    
    try:
        with job_lock:
            processing_jobs[job_id]['status'] = 'processing'
        
        print(f"🎬 Starting video conversion job: {job_id}")
        print_terminal_progress(0, "Initializing")
        
        output_dir = os.path.join(job_dir, 'outputs')
        os.makedirs(output_dir, exist_ok=True)
        
        # Prepare conversion tasks
        conversion_tasks = []
        for input_file in input_files:
            base_name = os.path.splitext(input_file['original_name'])[0]
            
            for format_type in formats:
                if format_type == 'square':
                    output_filename = f"{base_name}_square.mp4"
                    format_name = "Square (1080x1080)"
                elif format_type == 'square_blur':
                    output_filename = f"{base_name}_square_blur.mp4"
                    format_name = "Square with Blur (1080x1080)"
                elif format_type == 'landscape':
                    output_filename = f"{base_name}_landscape_blur.mp4"
                    format_name = "Landscape with Blur (1920x1080)"
                elif format_type == 'vertical':
                    output_filename = f"{base_name}_vertical_blur.mp4"
                    format_name = "Vertical with Blur (1080x1920)"
                else:
                    continue
                
                output_path = os.path.join(output_dir, output_filename)
                conversion_tasks.append((
                    input_file['path'],
                    output_path,
                    format_type,
                    output_filename,
                    input_file['original_name'],
                    format_name
                ))
        
        # Process videos one at a time (all formats for each video in parallel)
        # This is more robust and prevents resource overload
        
        # Group tasks by input video
        tasks_by_video = {}
        for task in conversion_tasks:
            input_path, output_path, format_type, output_filename, original_name, format_name = task
            if input_path not in tasks_by_video:
                tasks_by_video[input_path] = []
            tasks_by_video[input_path].append(task)
        
        # Process each video sequentially, but all formats for that video in parallel
        for video_idx, (video_path, video_tasks) in enumerate(tasks_by_video.items()):
            # Check for cancellation
            if should_cancel():
                print(f"\n❌ Processing cancelled for job: {job_id}")
                return
                
            video_name = os.path.basename(video_path)
            app_logger.info(f"Processing video: {video_name} ({len(video_tasks)} formats)")
            
            # Process all formats for this video in parallel (max 2 concurrent to save memory)
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(2, len(video_tasks))) as executor:
                futures = []
                for task in video_tasks:
                    input_path, output_path, format_type, output_filename, original_name, format_name = task
                    future = executor.submit(process_video, input_path, output_path, format_type)
                    futures.append((future, output_filename, output_path, original_name, format_name))
                
                # Wait for all formats of this video to complete
                for future, output_filename, output_path, original_name, format_name in futures:
                    # Check for cancellation
                    if should_cancel():
                        print(f"\n❌ Processing cancelled for job: {job_id}")
                        return
                        
                    try:
                        success = future.result()
                        
                        # Check memory usage and cleanup if needed
                        check_memory_and_cleanup()
                        
                        with job_lock:
                            processing_jobs[job_id]['completed_tasks'] += 1
                            progress = (processing_jobs[job_id]['completed_tasks'] / processing_jobs[job_id]['total_tasks']) * 100
                            processing_jobs[job_id]['progress'] = progress
                            
                            # Update terminal progress
                            print_terminal_progress(progress, f"Converting {video_name}")
                            
                            if success and os.path.exists(output_path):
                                # Get video metadata
                                try:
                                    metadata = get_video_metadata(output_path)
                                except:
                                    metadata = {}
                                
                                processing_jobs[job_id]['results'].append({
                                    'filename': output_filename,
                                    'path': output_path,
                                    'original_name': original_name,
                                    'format_name': format_name,
                                    'metadata': metadata
                                })
                            else:
                                processing_jobs[job_id]['errors'].append(f"Failed to process {original_name} to {format_name}")
                                
                    except Exception as e:
                        with job_lock:
                            processing_jobs[job_id]['completed_tasks'] += 1
                            processing_jobs[job_id]['errors'].append(f"Error processing {original_name} to {format_name}: {str(e)}")
                        app_logger.error(f"Error in video processing: {str(e)}")
            
            app_logger.info(f"Completed processing video: {video_name}")
        
        # Mark job as completed
        with job_lock:
            processing_jobs[job_id]['status'] = 'completed'
            processing_jobs[job_id]['progress'] = 100
            
        print_terminal_progress(100, "Completed")
        print(f"✅ Job {job_id} completed successfully!")
            
    except Exception as e:
        with job_lock:
            processing_jobs[job_id]['status'] = 'error'
            processing_jobs[job_id]['errors'].append(f"Processing failed: {str(e)}")
        app_logger.error(f"Background processing error: {str(e)}")
        print(f"\n❌ Job {job_id} failed: {str(e)}")
    finally:
        # Clean up thread reference
        with thread_lock:
            if job_id in active_processing_threads:
                del active_processing_threads[job_id]

@app.route('/status/<job_id>')
def get_job_status(job_id):
    with job_lock:
        if job_id not in processing_jobs:
            return jsonify({'error': 'Job not found'}), 404
        
        job_data = processing_jobs[job_id].copy()
        # Don't send file paths to client for security, but keep them in the original data
        if 'results' in job_data:
            job_data['results'] = []
            for result in processing_jobs[job_id]['results']:
                safe_result = result.copy()
                safe_result.pop('path', None)  # Remove path from the copy only
                job_data['results'].append(safe_result)
        
        return jsonify(job_data)

@app.route('/download/<job_id>/<filename>')
def download_file(job_id, filename):
    try:
        with job_lock:
            if job_id not in processing_jobs:
                app_logger.warning(f"Download attempted for non-existent job: {job_id}")
                return jsonify({'error': 'Job not found'}), 404
            
            job = processing_jobs[job_id]
            
            # Find the file in results
            file_path = None
            for result in job['results']:
                if result['filename'] == filename:
                    file_path = result.get('path')
                    break
            
            if not file_path:
                app_logger.warning(f"File {filename} not found in job {job_id} results")
                return jsonify({'error': 'File not found in job results'}), 404
                
            if not os.path.exists(file_path):
                app_logger.error(f"File path does not exist: {file_path}")
                return jsonify({'error': 'File no longer exists on server'}), 404
            
            app_logger.info(f"Downloading file: {filename} from {file_path}")
            return send_file(file_path, as_attachment=True, download_name=filename)
            
    except Exception as e:
        app_logger.error(f"Download error for {filename}: {str(e)}")
        return jsonify({'error': 'Download failed'}), 500

@app.route('/download_zip/<job_id>')
def download_zip(job_id):
    try:
        with job_lock:
            if job_id not in processing_jobs:
                app_logger.warning(f"ZIP download attempted for non-existent job: {job_id}")
                return jsonify({'error': 'Job not found'}), 404
            
            job = processing_jobs[job_id]
            
            if job['status'] != 'completed' or not job['results']:
                app_logger.warning(f"ZIP download attempted for incomplete job {job_id}: status={job['status']}, results_count={len(job.get('results', []))}")
                return jsonify({'error': 'No files ready for download'}), 400
            
            # Create ZIP file
            zip_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_videos.zip")
            
            files_added = 0
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for result in job['results']:
                    # Use the stored path directly from the job data
                    file_path = result.get('path')
                    if file_path and os.path.exists(file_path):
                        try:
                            zipf.write(file_path, arcname=result['filename'])
                            files_added += 1
                            app_logger.info(f"Added {result['filename']} to ZIP")
                        except Exception as e:
                            app_logger.error(f"Failed to add {result['filename']} to ZIP: {str(e)}")
                    else:
                        app_logger.warning(f"File not found for ZIP: {file_path}")
            
            if files_added == 0:
                app_logger.error(f"No files could be added to ZIP for job {job_id}")
                return jsonify({'error': 'No valid files found'}), 404
            
            app_logger.info(f"Created ZIP with {files_added} files: {zip_path}")
            return send_file(zip_path, as_attachment=True, download_name="converted_videos.zip")
            
    except Exception as e:
        app_logger.error(f"ZIP download error for job {job_id}: {str(e)}")
        return jsonify({'error': 'ZIP creation failed'}), 500

@app.route('/cleanup/<job_id>', methods=['POST'])
def cleanup_job(job_id):
    """Clean up job files and data"""
    with job_lock:
        if job_id in processing_jobs:
            # Mark job for cancellation if still processing
            if processing_jobs[job_id]['status'] == 'processing':
                processing_jobs[job_id]['cancel_requested'] = True
                print(f"🛑 Cancellation requested for job: {job_id}")
            
            # Remove job directory
            job_dir = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
            if os.path.exists(job_dir):
                shutil.rmtree(job_dir)
            
            # Remove from memory
            del processing_jobs[job_id]
            
            return jsonify({'message': 'Job cleaned up successfully'})
        else:
            return jsonify({'error': 'Job not found'}), 404

@app.route('/cancel/<job_id>', methods=['POST'])
def cancel_job(job_id):
    """Cancel an active processing job"""
    with job_lock:
        if job_id in processing_jobs:
            if processing_jobs[job_id]['status'] == 'processing':
                processing_jobs[job_id]['cancel_requested'] = True
                processing_jobs[job_id]['status'] = 'cancelled'
                print(f"🛑 Job {job_id} cancelled by user request")
                return jsonify({'message': 'Job cancellation requested'})
            else:
                return jsonify({'message': 'Job is not currently processing'}), 400
        else:
            return jsonify({'error': 'Job not found'}), 404

# Cleanup old jobs periodically (in production, use a proper task queue)
def cleanup_old_jobs():
    """Remove jobs older than 1 hour"""
    cutoff_time = datetime.now().timestamp() - 3600  # 1 hour ago
    
    with job_lock:
        jobs_to_remove = []
        for job_id, job_data in processing_jobs.items():
            job_time = datetime.fromisoformat(job_data['created_at']).timestamp()
            if job_time < cutoff_time:
                jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            job_dir = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
            if os.path.exists(job_dir):
                shutil.rmtree(job_dir)
            del processing_jobs[job_id]
            app_logger.info(f"Cleaned up old job: {job_id}")

# Schedule cleanup every hour
def schedule_cleanup():
    while True:
        time.sleep(3600)  # 1 hour
        cleanup_old_jobs()

cleanup_thread = threading.Thread(target=schedule_cleanup)
cleanup_thread.daemon = True
cleanup_thread.start()

if __name__ == '__main__':
    # For Railway deployment, use PORT environment variable
    # For local development, use command line args
    port = int(os.environ.get('PORT', 8000))
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=port, help='Port to run the server on')
    args = parser.parse_args()
    
    # Use Railway's PORT if available, otherwise use command line args
    final_port = int(os.environ.get('PORT', args.port))
    
    print(f"Starting Video Converter Flask app on port {final_port}")
    print(f"Environment PORT: {os.environ.get('PORT', 'Not set')}")
    
    try:
        app.run(host='0.0.0.0', port=final_port, debug=False)
    except Exception as e:
        print(f"Failed to start Flask app: {e}")
        raise 