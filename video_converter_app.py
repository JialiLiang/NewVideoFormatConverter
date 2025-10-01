from flask import Flask, render_template, request, jsonify, send_file, make_response, Response
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
import io
import glob
from collections import deque
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
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

# Resolve upload limits & streaming settings from environment for large batches
try:
    _configured_max_upload_mb = int(os.environ.get('VIDEO_UPLOAD_MAX_MB', '2048'))
except (TypeError, ValueError):
    _configured_max_upload_mb = 2048  # Fallback to 2GB total payload

if _configured_max_upload_mb and _configured_max_upload_mb > 0:
    app.config['MAX_CONTENT_LENGTH'] = _configured_max_upload_mb * 1024 * 1024
else:
    # None removes Flask's request limit so chunked uploads can flow through
    app.config.pop('MAX_CONTENT_LENGTH', None)

try:
    _configured_chunk_mb = int(os.environ.get('VIDEO_UPLOAD_CHUNK_MB', '8'))
except (TypeError, ValueError):
    _configured_chunk_mb = 8

UPLOAD_CHUNK_BYTES = max(256 * 1024, _configured_chunk_mb * 1024 * 1024)

# Concurrency controls for background conversion jobs
_cpu_count = os.cpu_count() or 2
try:
    _configured_workers = int(os.environ.get('VIDEO_PROCESS_MAX_WORKERS', '0'))
except (TypeError, ValueError):
    _configured_workers = 0

if _configured_workers > 0:
    MAX_CONCURRENT_TASKS = max(1, _configured_workers)
else:
    # Default to a balanced number of workers to avoid overloading shared hosts
    MAX_CONCURRENT_TASKS = max(1, min(4, _cpu_count))

try:
    MAX_TASK_RETRIES = max(0, int(os.environ.get('VIDEO_PROCESS_MAX_RETRIES', '1')))
except (TypeError, ValueError):
    MAX_TASK_RETRIES = 1

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

def stream_save_file(file_storage, destination_path, chunk_size=UPLOAD_CHUNK_BYTES):
    """Persist an uploaded file to disk without loading the full payload into memory."""
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)

    file_stream = getattr(file_storage, 'stream', None)
    if file_stream and hasattr(file_stream, 'seek'):
        try:
            file_stream.seek(0)
        except (OSError, io.UnsupportedOperation):
            pass

    bytes_written = 0
    with open(destination_path, 'wb') as output_file:
        while True:
            chunk = file_storage.stream.read(chunk_size)
            if not chunk:
                break
            output_file.write(chunk)
            bytes_written += len(chunk)

    return bytes_written

def detect_naming_convention_and_replace(original_filename, target_format):
    """
    Detect if filename follows the creative naming convention and replace dimension accordingly.
    Format: [id]_[creator]_[creator-type-filename]_[HOOK-…_VO-…_MUSIC-…_DIM]_[feature]_[language]_[date]
    
    If the convention is detected, replace PO with the target format.
    If not detected, append the target format suffix to the end.
    
    Args:
        original_filename: The original filename without extension
        target_format: 'square', 'square_blur', 'landscape', 'vertical'
    
    Returns:
        tuple: (new_filename, format_name)
    """
    # Define format mappings
    format_mappings = {
        'square': ('SQ', 'Square (1080x1080)'),
        'square_blur': ('SQ', 'Square (1080x1080)'),
        'landscape': ('LS', 'Landscape (1920x1080)'),
        'vertical': ('PO', 'Portrait (1080x1920)')
    }
    
    target_dim_code, format_name = format_mappings[target_format]
    
    # Split filename by underscores
    parts = original_filename.split('_')
    
    # Look for dimension codes (PO, LS, SQ) in the parts
    # According to the convention, PO should be in the "last third place" of the creative tags section
    dimension_found = False
    dimension_index = -1
    
    # Search for existing dimension codes
    for i, part in enumerate(parts):
        if part in ['PO', 'LS', 'SQ']:
            dimension_found = True
            dimension_index = i
            break
    
    if dimension_found:
        # Replace the found dimension with the target dimension
        new_parts = parts.copy()
        new_parts[dimension_index] = target_dim_code
        new_filename = '_'.join(new_parts)
        app_logger.info(f"Detected naming convention: replaced {parts[dimension_index]} with {target_dim_code}")
    else:
        # Try to detect if it's a creative naming convention by looking for common patterns
        # Check if we have at least 3-4 parts and some contain typical creative naming elements
        creative_indicators = ['HOOK-', 'VO-', 'MUSIC-', 'AIBG', 'IGSTORY', 'LOGO', 'ANIM', 'MIX', 'AIFILL', 'RETOUCH', 'IMGT-CHANGE', 'IMGT-', 'RnD', '[AIBG]', '[IGSTORY]', '[LOGO]', '[ANIM]', '[MIX]', '[AIFILL]', '[RETOUCH]', '[RnD]']
        has_creative_indicators = any(any(indicator in part for indicator in creative_indicators) for part in parts)
        
        if len(parts) >= 3 and has_creative_indicators:
            # This looks like a creative naming convention but missing dimension
            # Insert the dimension code before what looks like the feature tag
            # Look for feature tags (AIBG, IGSTORY, etc.) - handle both bracketed and unbracketed formats
            feature_tags = ['AIBG', 'IGSTORY', 'LOGO', 'ANIM', 'MIX', 'AIFILL', 'RETOUCH', 'IMGT-CHANGE', 'RnD']
            feature_tags.extend([tag for tag in parts if tag.startswith('IMGT-')])
            
            feature_index = -1
            for i, part in enumerate(parts):
                # Check for unbracketed feature tags
                if part in feature_tags or part.startswith('IMGT-'):
                    feature_index = i
                    break
                # Check for bracketed feature tags [FEATURE]
                elif part.startswith('[') and part.endswith(']'):
                    bracketed_content = part[1:-1]  # Remove brackets
                    if bracketed_content in feature_tags or bracketed_content.startswith('IMGT-'):
                        feature_index = i
                        break
            
            if feature_index > 0:
                # Insert dimension before the feature tag
                new_parts = parts.copy()
                new_parts.insert(feature_index, target_dim_code)
                new_filename = '_'.join(new_parts)
                app_logger.info(f"Detected creative convention missing dimension: inserted {target_dim_code} before feature tag")
            else:
                # Fallback: append format suffix as before
                new_filename = f"{original_filename}_{target_format}"
                app_logger.info(f"Creative convention detected but no clear feature tag: appended {target_format}")
        else:
            # Not a creative naming convention, use legacy suffix approach
            legacy_suffixes = {
                'square': '_square',
                'square_blur': '_square', 
                'landscape': '_landscape',
                'vertical': '_PO'
            }
            suffix = legacy_suffixes.get(target_format, f'_{target_format}')
            new_filename = f"{original_filename}{suffix}"
            app_logger.info(f"No creative convention detected: using legacy suffix {suffix}")
    
    return new_filename, format_name

def generate_job_id():
    return str(uuid.uuid4())

def get_memory_usage():
    """Get current memory usage in MB"""
    if not PSUTIL_AVAILABLE:
        return 0
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


def format_duration(seconds):
    """Convert seconds into a compact human-readable string"""
    if seconds is None:
        return None

    total_seconds = max(0, int(round(seconds)))
    minutes, secs = divmod(total_seconds, 60)

    if minutes == 0:
        return f"{secs}s"

    hours, minutes = divmod(minutes, 60)
    if hours == 0:
        return f"{minutes}m {secs}s"

    days, hours = divmod(hours, 24)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")

    return ' '.join(parts) if parts else f"{secs}s"

# Routes are registered in app.py - these functions are imported there

def upload_files():
    if 'files' not in request.files:
        return jsonify({'error': 'No files uploaded'}), 400
    
    files = request.files.getlist('files')
    formats = request.form.getlist('formats')
    
    if not files or not formats:
        return jsonify({'error': 'No files or formats selected'}), 400
    
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
    
    # Save uploaded files using streaming writes to avoid memory spikes
    input_files = []
    for i, file in enumerate(valid_files):
        filename = secure_filename(file.filename)
        input_path = os.path.join(job_dir, f"input_{i}_{filename}")
        try:
            bytes_written = stream_save_file(file, input_path)
        except Exception as exc:
            app_logger.error(f"Failed to persist upload {filename}: {exc}")
            shutil.rmtree(job_dir, ignore_errors=True)
            return jsonify({'error': f'Could not save {filename}. Please try again.'}), 500

        input_files.append({
            'path': input_path,
            'original_name': filename,
            'size_bytes': bytes_written
        })
    
    # Initialize job status
    with job_lock:
        processing_jobs[job_id] = {
            'status': 'queued',
            'progress': 0,
            'total_tasks': len(input_files) * len(formats),
            'completed_tasks': 0,
            'failed_tasks': 0,
            'results': [],
            'errors': [],
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'started_at': None,
            'elapsed_time_seconds': 0,
            'elapsed_time_human': None,
            'estimated_time_remaining_seconds': None,
            'estimated_time_remaining_human': None,
            'average_task_duration_seconds': None,
            'status_message': 'Queued for processing',
            '_start_time_perf': None,
            'tasks': {},
            'task_order': [],
            'requested_formats': formats,
            'max_retries': MAX_TASK_RETRIES
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
    """Process videos in a background worker with limited concurrency and retries."""
    job_start_perf = None

    def should_cancel():
        """Check if processing should be cancelled."""
        with job_lock:
            job = processing_jobs.get(job_id)
            return job is None or job.get('cancel_requested', False)

    def print_terminal_progress(progress, task_name="Processing"):
        """Print progress in terminal with single line update."""
        bar_length = 30
        filled_length = int(bar_length * progress // 100) if progress is not None else 0
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        progress_display = f"{progress:.1f}%" if progress is not None else "--"
        print(f'\r🎥 {task_name}: |{bar}| {progress_display} ', end='', flush=True)
        if progress is not None and progress >= 100:
            print()

    def refresh_job_metrics_locked():
        """Recompute timing and progress metrics; caller must hold job_lock."""
        nonlocal job_start_perf

        job = processing_jobs.get(job_id)
        if not job:
            return

        total = max(job.get('total_tasks', 0) or 0, 0)
        completed = max(job.get('completed_tasks', 0), 0)
        failed = max(job.get('failed_tasks', 0), 0)
        success_count = max(completed - failed, 0)
        remaining = max(total - completed, 0)

        # Drive overall progress from counters rather than scattered updates
        if total > 0:
            job['progress'] = min(100.0, (completed / total) * 100)
        else:
            job['progress'] = 100.0 if completed else 0.0

        if job.get('_start_time_perf') is None:
            start_perf = time.perf_counter()
            job['_start_time_perf'] = start_perf
            job_start_perf = start_perf
            job['started_at'] = datetime.now().isoformat()
        else:
            start_perf = job['_start_time_perf']

        elapsed = max(0.0, time.perf_counter() - start_perf)
        job['elapsed_time_seconds'] = elapsed
        job['elapsed_time_human'] = format_duration(elapsed)

        if completed > 0:
            average = elapsed / completed
            job['average_task_duration_seconds'] = average
            eta_seconds = average * remaining if remaining > 0 else 0
            job['estimated_time_remaining_seconds'] = eta_seconds if remaining > 0 else 0
            job['estimated_time_remaining_human'] = format_duration(eta_seconds)
        else:
            job['average_task_duration_seconds'] = None
            job['estimated_time_remaining_seconds'] = None
            job['estimated_time_remaining_human'] = None

        if remaining > 0:
            job['status_message'] = f"Processing {success_count}/{total} conversions"
        elif failed:
            job['status_message'] = f"Completed with {failed} error(s)"
        else:
            job['status_message'] = f"Completed {success_count} conversion(s)"

        job['last_updated'] = datetime.now().isoformat()

    def prepare_tasks():
        output_dir = os.path.join(job_dir, 'outputs')
        os.makedirs(output_dir, exist_ok=True)

        prepared_tasks = []

        for input_index, input_file in enumerate(input_files):
            base_name = os.path.splitext(input_file['original_name'])[0]

            for format_type in formats:
                output_filename_base, format_name = detect_naming_convention_and_replace(base_name, format_type)
                output_filename = f"{output_filename_base}.mp4"
                output_path = os.path.join(output_dir, output_filename)
                task_id = f"{input_index}-{format_type}-{uuid.uuid4().hex[:8]}"

                prepared_tasks.append({
                    'task_id': task_id,
                    'input_path': input_file['path'],
                    'output_path': output_path,
                    'format_type': format_type,
                    'output_filename': output_filename,
                    'original_name': input_file['original_name'],
                    'format_name': format_name,
                    'status': 'queued',
                    'attempts': 0,
                    'error': None,
                    'started_at': None,
                    'completed_at': None,
                    'duration_seconds': None,
                    '_start_perf': None,
                    'input_size_bytes': input_file.get('size_bytes')
                })

        return prepared_tasks

    def run_single_task(task_snapshot):
        """Execute conversion for a single format."""
        # Ensure previous attempt artifacts are cleared
        try:
            if os.path.exists(task_snapshot['output_path']):
                os.remove(task_snapshot['output_path'])
        except OSError:
            pass

        success, error_message = process_video(
            task_snapshot['input_path'],
            task_snapshot['output_path'],
            task_snapshot['format_type']
        )

        return {
            'success': success,
            'error': error_message
        }

    def handle_task_completion(task_id, task_result):
        """Apply task result to job state. Returns (should_retry, progress, label)."""
        success = bool(task_result.get('success'))
        error_message = task_result.get('error')

        with job_lock:
            job = processing_jobs.get(job_id)
            if not job:
                return False, None, ""
            task = job['tasks'].get(task_id)
            if not task:
                return False, job.get('progress'), ""

            output_path = task['output_path']
            original_name = task['original_name']
            format_name = task['format_name']

        metadata = {}
        if success and os.path.exists(output_path):
            try:
                metadata = get_video_metadata(output_path)
            except Exception:
                metadata = {}

        with job_lock:
            job = processing_jobs.get(job_id)
            if not job:
                return False, None, ""
            task = job['tasks'].get(task_id)
            if not task:
                return False, job.get('progress'), ""

            start_perf = task.pop('_start_perf', None)
            if start_perf is not None:
                task['duration_seconds'] = max(0.0, time.perf_counter() - start_perf)

            label = f"{task['original_name']} ({task['format_name']})"

            if success:
                task['status'] = 'success'
                task['error'] = None
                task['completed_at'] = datetime.now().isoformat()
                job['results'].append({
                    'task_id': task_id,
                    'filename': task['output_filename'],
                    'path': task['output_path'],
                    'original_name': task['original_name'],
                    'format_name': task['format_name'],
                    'metadata': metadata
                })
                job['completed_tasks'] += 1
            else:
                task['error'] = error_message or 'Unknown error'

                if task['attempts'] <= MAX_TASK_RETRIES and not job.get('cancel_requested', False):
                    task['status'] = 'queued'
                    task['completed_at'] = None
                    job['status_message'] = f"Retrying {label}"
                    refresh_job_metrics_locked()
                    return True, job.get('progress'), label

                task['status'] = 'failed'
                task['completed_at'] = datetime.now().isoformat()
                job['failed_tasks'] += 1
                job['errors'].append(f"{task['original_name']} → {task['format_name']}: {task['error']}")
                job['completed_tasks'] += 1

            refresh_job_metrics_locked()
            progress = job.get('progress', 0)
            return False, progress, label

    try:
        prepared_tasks = prepare_tasks()

        if not prepared_tasks:
            with job_lock:
                job = processing_jobs.get(job_id)
                if job:
                    job['status'] = 'error'
                    job['status_message'] = 'No conversion tasks generated'
                    job['errors'].append('No conversion formats were requested.')
                    refresh_job_metrics_locked()
            return

        with job_lock:
            job = processing_jobs.get(job_id)
            if not job:
                return

            job['status'] = 'processing'
            job['started_at'] = datetime.now().isoformat()
            job['last_updated'] = datetime.now().isoformat()
            job_start_perf = time.perf_counter()
            job['_start_time_perf'] = job_start_perf
            job['task_order'] = [task['task_id'] for task in prepared_tasks]
            job['tasks'] = {task['task_id']: task for task in prepared_tasks}
            job['total_tasks'] = len(prepared_tasks)
            job['status_message'] = f"Processing 0/{len(prepared_tasks)} conversions"

        print(f"🎬 Starting video conversion job: {job_id}")
        print_terminal_progress(0.0, "Initializing")

        log_memory_usage("before processing job")

        tasks_queue = deque([task['task_id'] for task in prepared_tasks])
        futures = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT_TASKS) as executor:
            while (tasks_queue or futures) and not should_cancel():
                # Launch new tasks while capacity is available
                while tasks_queue and len(futures) < MAX_CONCURRENT_TASKS and not should_cancel():
                    task_id = tasks_queue.popleft()

                    with job_lock:
                        job = processing_jobs.get(job_id)
                        if not job:
                            break
                        task = job['tasks'].get(task_id)
                        if not task:
                            continue
                        task['status'] = 'running'
                        task['attempts'] += 1
                        task['started_at'] = datetime.now().isoformat()
                        task['_start_perf'] = time.perf_counter()
                        job['status_message'] = f"Processing {task['original_name']} ({task['format_name']})"

                        task_snapshot = {
                            'input_path': task['input_path'],
                            'output_path': task['output_path'],
                            'format_type': task['format_type']
                        }

                    future = executor.submit(run_single_task, task_snapshot)
                    futures[future] = task_id

                if not futures:
                    # No active futures and no tasks left to queue
                    break

                done, _ = concurrent.futures.wait(
                    futures.keys(),
                    timeout=1.0,
                    return_when=concurrent.futures.FIRST_COMPLETED
                )

                if not done:
                    continue

                for future in done:
                    task_id = futures.pop(future)

                    try:
                        result = future.result()
                    except Exception as exc:
                        app_logger.error(f"Exception while converting task {task_id}: {exc}")
                        result = {'success': False, 'error': str(exc)}

                    retry, progress, label = handle_task_completion(task_id, result)

                    if retry:
                        tasks_queue.append(task_id)
                        app_logger.warning(f"Retrying task {task_id} ({label})")
                        continue

                    print_terminal_progress(progress, f"Converting {label}")

                    # Opportunistic cleanup and GC to avoid memory bloat for long jobs
                    if check_memory_and_cleanup():
                        app_logger.info("Triggered memory cleanup during processing loop")

            if should_cancel():
                executor.shutdown(wait=False, cancel_futures=True)

        gc.collect()
        log_memory_usage("after processing job")

        cancelled = should_cancel()

        with job_lock:
            job = processing_jobs.get(job_id)
            if job:
                if cancelled:
                    job['status'] = 'cancelled'
                    job['status_message'] = 'Job cancelled by user'
                elif job.get('failed_tasks'):
                    job['status'] = 'completed_with_errors'
                    job['status_message'] = f"Completed with {job['failed_tasks']} error(s)"
                else:
                    job['status'] = 'completed'
                    job['status_message'] = 'Completed successfully'

                job['progress'] = 100.0 if job.get('total_tasks') else job.get('progress', 100.0)
                job['estimated_time_remaining_seconds'] = 0
                job['estimated_time_remaining_human'] = format_duration(0)
                job.pop('_start_time_perf', None)
                refresh_job_metrics_locked()

        if not cancelled:
            print_terminal_progress(100.0, "Completed")
            print(f"✅ Job {job_id} completed (errors: {processing_jobs.get(job_id, {}).get('failed_tasks', 0)})")
        else:
            print(f"\n❌ Job {job_id} cancelled")
            
    except Exception as e:
        with job_lock:
            job = processing_jobs.get(job_id)
            if job:
                job['status'] = 'error'
                job['status_message'] = 'Processing failed'
                job['errors'].append(f"Processing failed: {str(e)}")
                job.pop('_start_time_perf', None)
                refresh_job_metrics_locked()
        app_logger.exception(f"Background processing error for job {job_id}: {e}")
        print(f"\n❌ Job {job_id} failed: {str(e)}")
    finally:
        # Clean up thread reference
        with thread_lock:
            active_processing_threads.pop(job_id, None)

def get_job_status(job_id):
    with job_lock:
        if job_id not in processing_jobs:
            return jsonify({'error': 'Job not found'}), 404
        
        job_data = {}

        job = processing_jobs[job_id]

        for key, value in job.items():
            if key.startswith('_'):
                continue

            if key == 'results':
                job_data['results'] = []
                for result in value:
                    safe_result = result.copy()
                    safe_result.pop('path', None)
                    job_data['results'].append(safe_result)
            elif key == 'tasks':
                # Return task data in client-friendly order without exposing file paths
                task_list = []
                ordering = job.get('task_order') or list(value.keys())
                for task_id in ordering:
                    task = value.get(task_id)
                    if not task:
                        continue
                    task_list.append({
                        'task_id': task_id,
                        'original_name': task.get('original_name'),
                        'format_name': task.get('format_name'),
                        'format_type': task.get('format_type'),
                        'status': task.get('status'),
                        'attempts': task.get('attempts'),
                        'error': task.get('error'),
                        'started_at': task.get('started_at'),
                        'completed_at': task.get('completed_at'),
                        'duration_seconds': task.get('duration_seconds'),
                        'input_size_bytes': task.get('input_size_bytes')
                    })
                job_data['tasks'] = task_list
            else:
                job_data[key] = value

        return jsonify(job_data)

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

def download_zip(job_id):
    try:
        with job_lock:
            if job_id not in processing_jobs:
                app_logger.warning(f"ZIP download attempted for non-existent job: {job_id}")
                return jsonify({'error': 'Job not found'}), 404
            
            job = processing_jobs[job_id]
            
            if job['status'] not in ('completed', 'completed_with_errors') or not job['results']:
                app_logger.warning(f"ZIP download attempted for incomplete job {job_id}: status={job['status']}, results_count={len(job.get('results', []))}")
                return jsonify({'error': 'No files ready for download'}), 400
            
            # Debug: Log all job results
            app_logger.info(f"Job {job_id} results: {job['results']}")
            
            # Get valid files for ZIP
            valid_files = []
            for result in job['results']:
                file_path = result.get('path')
                filename = result.get('filename')
                app_logger.info(f"Checking file: {filename} at path: {file_path}")
                
                if file_path and os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    app_logger.info(f"Valid file found: {filename} ({file_size} bytes)")
                    valid_files.append((file_path, filename))
                else:
                    app_logger.warning(f"File not found for ZIP: {file_path}")
            
            if not valid_files:
                app_logger.error(f"No valid files found for job {job_id}")
                return jsonify({'error': 'No valid files found'}), 404
            
            app_logger.info(f"Creating streaming ZIP with {len(valid_files)} files for job {job_id}")
            
            # Try streaming ZIP response first, with fallback to simple ZIP creation
            try:
                return create_streaming_zip_response(valid_files, "converted_videos.zip")
            except Exception as e:
                app_logger.warning(f"Streaming ZIP failed, falling back to simple ZIP: {str(e)}")
                return create_simple_zip_response(job_id, valid_files, "converted_videos.zip")
            
    except Exception as e:
        app_logger.error(f"ZIP download error for job {job_id}: {str(e)}")
        import traceback
        app_logger.error(f"ZIP download traceback: {traceback.format_exc()}")
        return jsonify({'error': 'ZIP creation failed'}), 500

def create_streaming_zip_response(files, zip_name):
    """Create a truly streaming ZIP response using temporary file to avoid memory issues"""
    from flask import Response
    import tempfile
    
    def generate_zip():
        # Create a temporary file for the ZIP
        temp_zip_path = None
        files_added = 0
        
        try:
            # Create temporary file for ZIP
            temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            temp_zip_path = temp_zip.name
            temp_zip.close()
            
            app_logger.info(f"Creating ZIP file at: {temp_zip_path}")
            
            # Create ZIP file on disk (not in memory) - NO COMPRESSION for speed
            with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_STORED, compresslevel=0) as zipf:
                for file_path, archive_name in files:
                    try:
                        if not os.path.exists(file_path):
                            app_logger.warning(f"File does not exist: {file_path}")
                            continue
                            
                        app_logger.info(f"Adding file to ZIP: {archive_name} from {file_path}")
                        
                        # Use zipfile's built-in method for better compatibility
                        zipf.write(file_path, arcname=archive_name)
                        files_added += 1
                        
                        app_logger.info(f"Successfully added {archive_name} to ZIP")
                        
                        # Force garbage collection periodically
                        if check_memory_and_cleanup():
                            app_logger.warning("Memory cleanup triggered during ZIP creation")
                        
                    except Exception as e:
                        app_logger.error(f"Error adding {archive_name} to ZIP: {str(e)}")
                        continue
            
            app_logger.info(f"ZIP creation completed. Files added: {files_added}")
            
            if files_added == 0:
                app_logger.error("No files were added to ZIP")
                yield b''  # Return empty data
                return
                
            # Check if ZIP file was created and has content
            if not os.path.exists(temp_zip_path):
                app_logger.error("ZIP file was not created")
                yield b''
                return
                
            zip_size = os.path.getsize(temp_zip_path)
            app_logger.info(f"ZIP file size: {zip_size} bytes")
            
            if zip_size == 0:
                app_logger.error("ZIP file is empty")
                yield b''
                return
            
            # Stream the ZIP file back to client in chunks
            with open(temp_zip_path, 'rb') as zip_file:
                chunk_size = 256 * 1024  # 256KB chunks for faster streaming
                bytes_sent = 0
                while True:
                    chunk = zip_file.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
                    bytes_sent += len(chunk)
                    
                    # Periodic memory cleanup during streaming
                    if check_memory_and_cleanup():
                        app_logger.warning("Memory cleanup triggered during ZIP streaming")
                
                app_logger.info(f"ZIP streaming completed. Bytes sent: {bytes_sent}")
                
        except Exception as e:
            app_logger.error(f"Error creating streaming ZIP: {str(e)}")
            import traceback
            app_logger.error(f"ZIP creation traceback: {traceback.format_exc()}")
            yield b''  # Return empty data on error
        finally:
            # Cleanup temporary file
            try:
                if temp_zip_path and os.path.exists(temp_zip_path):
                    os.unlink(temp_zip_path)
                    app_logger.info("Cleaned up temporary ZIP file")
            except Exception as e:
                app_logger.warning(f"Could not clean up temp ZIP file: {str(e)}")
            
            # Force garbage collection
            gc.collect()
    
    # Create response with proper headers
    response = Response(
        generate_zip(),
        mimetype='application/zip',
        headers={
            'Content-Disposition': f'attachment; filename={zip_name}',
            'Content-Type': 'application/zip'
        }
    )
    
    return response

def create_simple_zip_response(job_id, files, zip_name):
    """Fallback ZIP creation method - creates ZIP in upload folder"""
    try:
        # Create ZIP in upload folder (not temp)
        zip_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_videos.zip")
        
        app_logger.info(f"Creating fallback ZIP at: {zip_path}")
        
        files_added = 0
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_STORED, compresslevel=0) as zipf:
            for file_path, archive_name in files:
                try:
                    if not os.path.exists(file_path):
                        app_logger.warning(f"File does not exist: {file_path}")
                        continue
                        
                    app_logger.info(f"Adding file to fallback ZIP: {archive_name}")
                    zipf.write(file_path, arcname=archive_name)
                    files_added += 1
                    
                    # Force garbage collection periodically
                    if check_memory_and_cleanup():
                        app_logger.warning("Memory cleanup triggered during fallback ZIP creation")
                        
                except Exception as e:
                    app_logger.error(f"Error adding {archive_name} to fallback ZIP: {str(e)}")
                    continue
        
        if files_added == 0:
            app_logger.error("No files were added to fallback ZIP")
            return jsonify({'error': 'No files could be added to ZIP'}), 500
        
        if not os.path.exists(zip_path):
            app_logger.error("Fallback ZIP file was not created")
            return jsonify({'error': 'ZIP file creation failed'}), 500
            
        zip_size = os.path.getsize(zip_path)
        app_logger.info(f"Fallback ZIP created successfully. Size: {zip_size} bytes, Files: {files_added}")
        
        return send_file(zip_path, as_attachment=True, download_name=zip_name)
        
    except Exception as e:
        app_logger.error(f"Fallback ZIP creation failed: {str(e)}")
        return jsonify({'error': 'ZIP creation failed'}), 500

def cleanup_job(job_id):
    """Clean up job files and data"""
    with job_lock:
        if job_id in processing_jobs:
            # Mark job for cancellation if still processing
            if processing_jobs[job_id]['status'] == 'processing':
                processing_jobs[job_id]['cancel_requested'] = True
                processing_jobs[job_id]['status_message'] = 'Cleanup requested while processing'
                print(f"🛑 Cancellation requested for job: {job_id}")
            
            # Clean up job directory and any ZIP files
            cleanup_job_files(job_id)
            
            # Remove from memory
            del processing_jobs[job_id]
            
            # Force garbage collection after cleanup
            gc.collect()
            
            return jsonify({'message': 'Job cleaned up successfully'})
        else:
            return jsonify({'error': 'Job not found'}), 404

def cleanup_job_files(job_id):
    """Clean up all files associated with a job"""
    try:
        # Remove job directory
        job_dir = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
        if os.path.exists(job_dir):
            shutil.rmtree(job_dir)
            app_logger.info(f"Removed job directory: {job_dir}")
        
        # Remove any ZIP files created for this job
        zip_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_videos.zip")
        if os.path.exists(zip_file):
            os.remove(zip_file)
            app_logger.info(f"Removed ZIP file: {zip_file}")
        
        # Clean up any temporary files that might be left over
        temp_pattern = f"*{job_id}*"
        import glob
        temp_files = glob.glob(os.path.join(tempfile.gettempdir(), temp_pattern))
        for temp_file in temp_files:
            try:
                if os.path.isfile(temp_file):
                    os.remove(temp_file)
                elif os.path.isdir(temp_file):
                    shutil.rmtree(temp_file)
                app_logger.info(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                app_logger.warning(f"Could not clean up temp file {temp_file}: {str(e)}")
        
    except Exception as e:
        app_logger.error(f"Error during job cleanup for {job_id}: {str(e)}")

def cancel_job(job_id):
    """Cancel an active processing job"""
    with job_lock:
        if job_id in processing_jobs:
            current_status = processing_jobs[job_id]['status']
            if current_status == 'processing':
                processing_jobs[job_id]['cancel_requested'] = True
                processing_jobs[job_id]['status'] = 'cancelled'
                processing_jobs[job_id]['status_message'] = 'Job cancellation requested'
                processing_jobs[job_id]['estimated_time_remaining_seconds'] = None
                processing_jobs[job_id]['estimated_time_remaining_human'] = None
                processing_jobs[job_id]['last_updated'] = datetime.now().isoformat()
                processing_jobs[job_id].pop('_start_time_perf', None)
                print(f"🛑 Job {job_id} cancelled by user request")
                return jsonify({'message': 'Job cancellation requested'})
            elif current_status in ['completed', 'error', 'cancelled']:
                # Job is already finished, return success instead of error
                return jsonify({'message': f'Job already {current_status}'})
            else:
                # Job is queued, mark as cancelled
                processing_jobs[job_id]['cancel_requested'] = True
                processing_jobs[job_id]['status'] = 'cancelled'
                processing_jobs[job_id]['status_message'] = 'Job cancelled before processing started'
                processing_jobs[job_id]['estimated_time_remaining_seconds'] = None
                processing_jobs[job_id]['estimated_time_remaining_human'] = None
                processing_jobs[job_id]['last_updated'] = datetime.now().isoformat()
                processing_jobs[job_id].pop('_start_time_perf', None)
                return jsonify({'message': 'Job cancelled before processing started'})
        else:
            return jsonify({'error': 'Job not found'}), 404

def debug_job(job_id):
    """Debug endpoint to check job files and status"""
    with job_lock:
        if job_id not in processing_jobs:
            return jsonify({'error': 'Job not found'}), 404
        
        job = processing_jobs[job_id]
        debug_info = {
            'job_id': job_id,
            'status': job['status'],
            'total_tasks': job.get('total_tasks', 0),
            'completed_tasks': job.get('completed_tasks', 0),
            'results_count': len(job.get('results', [])),
            'errors_count': len(job.get('errors', [])),
            'results': []
        }
        
        # Check each result file
        for result in job.get('results', []):
            file_path = result.get('path')
            file_info = {
                'filename': result.get('filename'),
                'path': file_path,
                'exists': os.path.exists(file_path) if file_path else False,
                'size': os.path.getsize(file_path) if file_path and os.path.exists(file_path) else 0,
                'format_name': result.get('format_name'),
                'original_name': result.get('original_name')
            }
            debug_info['results'].append(file_info)
        
        return jsonify(debug_info)

# Cleanup old jobs periodically (in production, use a proper task queue)
def cleanup_old_jobs():
    """Remove jobs older than 30 minutes (reduced for memory management)"""
    cutoff_time = datetime.now().timestamp() - 1800  # 30 minutes ago (reduced from 1 hour)
    
    with job_lock:
        jobs_to_remove = []
        for job_id, job_data in processing_jobs.items():
            job_time = datetime.fromisoformat(job_data['created_at']).timestamp()
            if job_time < cutoff_time:
                jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            cleanup_job_files(job_id)
            del processing_jobs[job_id]
            app_logger.info(f"Cleaned up old job: {job_id}")
        
        if jobs_to_remove:
            # Force garbage collection after cleanup
            gc.collect()
            app_logger.info(f"Cleaned up {len(jobs_to_remove)} old jobs")

def cleanup_orphaned_files():
    """Clean up any orphaned files in upload directory"""
    try:
        upload_dir = app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_dir):
            return
        
        # Get all subdirectories (job directories)
        for item in os.listdir(upload_dir):
            item_path = os.path.join(upload_dir, item)
            
            # Skip if it's not a directory and not a zip file
            if not os.path.isdir(item_path) and not item.endswith('.zip'):
                continue
            
            # Check if it's an old file/directory
            try:
                stat = os.stat(item_path)
                file_age = time.time() - stat.st_mtime
                
                # Remove files/directories older than 1 hour
                if file_age > 3600:  # 1 hour
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                    app_logger.info(f"Cleaned up orphaned file/directory: {item}")
            except Exception as e:
                app_logger.warning(f"Could not clean up {item}: {str(e)}")
                
    except Exception as e:
        app_logger.error(f"Error during orphaned file cleanup: {str(e)}")

# Schedule cleanup every 30 minutes (more frequent for memory management)
def schedule_cleanup():
    while True:
        time.sleep(1800)  # 30 minutes (reduced from 1 hour)
        try:
            cleanup_old_jobs()
            cleanup_orphaned_files()
            # Force memory cleanup after scheduled cleanup
            gc.collect()
            log_memory_usage("after scheduled cleanup")
        except Exception as e:
            app_logger.error(f"Error during scheduled cleanup: {str(e)}")

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
