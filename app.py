from flask import Flask, render_template, request, jsonify, send_file, make_response
import os
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

# Import the video processing functions from the original file
from video_converter import (
    process_video,
    get_video_metadata,
    create_square_video,
    create_square_blur_video,
    create_landscape_video,
    create_vertical_blur_video
)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
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

ALLOWED_EXTENSIONS = {'mp4', 'mov'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_job_id():
    return str(uuid.uuid4())

@app.route('/')
def index():
    return render_template('index.html')

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
    thread.start()
    
    return jsonify({'job_id': job_id})

def process_videos_background(job_id, input_files, formats, job_dir):
    """Process videos in background thread"""
    try:
        with job_lock:
            processing_jobs[job_id]['status'] = 'processing'
        
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
        for video_path, video_tasks in tasks_by_video.items():
            app_logger.info(f"Processing video: {os.path.basename(video_path)} ({len(video_tasks)} formats)")
            
            # Process all formats for this video in parallel (max 4 concurrent)
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(video_tasks))) as executor:
                futures = []
                for task in video_tasks:
                    input_path, output_path, format_type, output_filename, original_name, format_name = task
                    future = executor.submit(process_video, input_path, output_path, format_type)
                    futures.append((future, output_filename, output_path, original_name, format_name))
                
                # Wait for all formats of this video to complete
                for future, output_filename, output_path, original_name, format_name in futures:
                    try:
                        success = future.result()
                        
                        with job_lock:
                            processing_jobs[job_id]['completed_tasks'] += 1
                            progress = (processing_jobs[job_id]['completed_tasks'] / processing_jobs[job_id]['total_tasks']) * 100
                            processing_jobs[job_id]['progress'] = progress
                            
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
            
            app_logger.info(f"Completed processing video: {os.path.basename(video_path)}")
        
        # Mark job as completed
        with job_lock:
            processing_jobs[job_id]['status'] = 'completed'
            processing_jobs[job_id]['progress'] = 100
            
    except Exception as e:
        with job_lock:
            processing_jobs[job_id]['status'] = 'error'
            processing_jobs[job_id]['errors'].append(f"Processing failed: {str(e)}")
        app_logger.error(f"Background processing error: {str(e)}")

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
    with job_lock:
        if job_id not in processing_jobs:
            return "Job not found", 404
        
        job = processing_jobs[job_id]
        
        # Find the file in results
        file_path = None
        for result in job['results']:
            if result['filename'] == filename:
                file_path = result.get('path')
                break
        
        if not file_path or not os.path.exists(file_path):
            return "File not found", 404
        
        return send_file(file_path, as_attachment=True, download_name=filename)

@app.route('/download_zip/<job_id>')
def download_zip(job_id):
    with job_lock:
        if job_id not in processing_jobs:
            return "Job not found", 404
        
        job = processing_jobs[job_id]
        
        if job['status'] != 'completed' or not job['results']:
            return "No files to download", 400
        
        # Create ZIP file
        zip_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_videos.zip")
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for result in job['results']:
                # Use the stored path directly from the job data
                file_path = result.get('path')
                if file_path and os.path.exists(file_path):
                    zipf.write(file_path, arcname=result['filename'])
        
        return send_file(zip_path, as_attachment=True, download_name="converted_videos.zip")

@app.route('/cleanup/<job_id>', methods=['POST'])
def cleanup_job(job_id):
    """Clean up job files and data"""
    with job_lock:
        if job_id in processing_jobs:
            # Remove job directory
            job_dir = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
            if os.path.exists(job_dir):
                shutil.rmtree(job_dir)
            
            # Remove from memory
            del processing_jobs[job_id]
            
            return jsonify({'message': 'Job cleaned up successfully'})
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
    
    print(f"Starting Flask app on port {final_port}")
    print(f"Environment PORT: {os.environ.get('PORT', 'Not set')}")
    
    try:
        app.run(host='0.0.0.0', port=final_port, debug=False)
    except Exception as e:
        print(f"Failed to start Flask app: {e}")
        raise 