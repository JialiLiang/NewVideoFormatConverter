import moviepy.editor as mp
from moviepy.editor import VideoClip, VideoFileClip
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
import os
import tempfile
import shutil
import time
import subprocess
import concurrent.futures
from functools import partial
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Set up ffmpeg path - try to use imageio-ffmpeg binary if system ffmpeg is not available
try:
    # Try running ffmpeg to see if it's available
    subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True)
except (subprocess.SubprocessError, FileNotFoundError):
    # If ffmpeg is not found, use imageio-ffmpeg binary
    import imageio_ffmpeg
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    # Update subprocess env path for all calls
    os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + str(Path(ffmpeg_path).parent)
    print(f"Using ffmpeg from imageio-ffmpeg: {ffmpeg_path}")

# Check for hardware acceleration support
def check_hw_accel():
    """Check if hardware acceleration is available"""
    try:
        # Check for NVIDIA GPU
        nvidia_result = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
        if nvidia_result.returncode == 0:
            return "h264_nvenc"  # NVIDIA GPU available
    except:
        pass
    
    try:
        # Check for Intel Quick Sync
        intel_result = subprocess.run(["vainfo"], capture_output=True, text=True)
        if "VAEntrypointEncSlice" in intel_result.stdout:
            return "h264_qsv"  # Intel Quick Sync available
    except:
        pass
    
    return None  # No hardware acceleration available

# Get optimal FFmpeg parameters based on available hardware
def get_ffmpeg_params_for_processing():
    """Get optimized FFmpeg parameters for video processing operations"""
    hw_accel = check_hw_accel()
    
    if hw_accel == "h264_nvenc":
        return {
            "codec": "h264_nvenc",
            "preset": "p2",  # Fastest NVIDIA preset
            "crf": "28",
            "extra_params": ["-gpu", "0"]
        }
    elif hw_accel == "h264_qsv":
        return {
            "codec": "h264_qsv", 
            "preset": "veryfast",
            "crf": "28",
            "extra_params": ["-hwaccel", "qsv"]
        }
    else:
        return {
            "codec": "libx264",
            "preset": "veryfast",
            "crf": "28", 
            "extra_params": ["-threads", str(os.cpu_count() or 4)]
        }

# Process a single video with the given format
def process_video(input_path, output_path, format_type, progress_callback=None):
    """Process a single video with the given format"""
    try:
        # Force garbage collection before processing to free memory
        import gc
        gc.collect()
        
        logging.info(f"Starting conversion to {format_type} format: {os.path.basename(input_path)}")
        
        if format_type == "square":
            create_square_video(input_path, output_path)
        elif format_type == "square_blur":
            create_square_blur_video(input_path, output_path)
        elif format_type == "landscape":
            create_landscape_video(input_path, output_path)
        elif format_type == "vertical":
            create_vertical_blur_video(input_path, output_path)
        else:
            raise ValueError(f"Unsupported format type: {format_type}")
        
        if progress_callback:
            progress_callback()
        
        # Force garbage collection after processing to free memory
        gc.collect()
        
        logging.info(f"Successfully converted to {format_type}: {os.path.basename(output_path)}")
        return True, None
    except Exception as e:
        error_message = str(e)
        logging.error(f"Error processing video {os.path.basename(input_path)}: {error_message}")
        # Force cleanup on error
        import gc
        gc.collect()
        return False, error_message

# Patch moviepy's resize function to use the correct Pillow constant
def patched_resize(clip, newsize=None, height=None, width=None, apply_to_mask=True):
    """
    Patched version of moviepy's resize function that works with newer Pillow versions.
    """
    from PIL import Image
    
    # Determine the target size
    if newsize is not None:
        w, h = newsize
    else:
        w = clip.w if width is None else width
        h = clip.h if height is None else height
    
    # Define the resizer function
    def resizer(pic, newsize):
        # Convert to PIL Image
        pilim = Image.fromarray(pic)
        
        # Use LANCZOS instead of ANTIALIAS for newer Pillow versions
        try:
            # Try the new constant first (Pillow 10.0+)
            resized_pil = pilim.resize(newsize[::-1], Image.Resampling.LANCZOS)
        except AttributeError:
            try:
                # Try the old constant (Pillow 9.x)
                resized_pil = pilim.resize(newsize[::-1], Image.ANTIALIAS)
            except AttributeError:
                # Fallback to default
                resized_pil = pilim.resize(newsize[::-1])
        
        # Convert back to numpy array
        return np.array(resized_pil)
    
    # Apply the resize
    if clip.ismask:
        fl = lambda pic: 1.0*resizer((255 * pic).astype('uint8'), (w, h))
    else:
        fl = lambda pic: resizer(pic.astype('uint8'), (w, h))
    
    newclip = clip.fl_image(fl)
    
    if apply_to_mask and clip.mask is not None:
        newclip.mask = patched_resize(clip.mask, newsize=(w, h), apply_to_mask=False)
    
    return newclip

# Apply the patched resize function to moviepy if needed
# This is a fallback in case the direct resize method has issues
# Fix: Use the correct approach for patching moviepy's resize function
try:
    # Try to patch the resize function directly on the VideoClip class
    VideoClip.resize = patched_resize
except AttributeError:
    # If that fails, we'll use the patched function directly in our code
    pass

def create_square_video(input_path, output_path):
    # Load the video
    video = VideoFileClip(input_path)
    
    # Force video to 30 FPS and calculate adjusted duration
    video = video.set_fps(30)
    frame_duration = 1.0/30  # Duration of one frame at 30fps
    exact_duration = video.duration - (4 * frame_duration)  # Remove 2 frames worth of duration
    
    # Target dimensions (square)
    target_size = 1080
    
    # For portrait videos, we'll crop the center portion
    # Calculate the crop dimensions to maintain aspect ratio
    if video.w > video.h:  # If wider than tall
        crop_width = int(video.h)  # Use height as width
        crop_height = int(video.h)
        x_center = (video.w - crop_width) // 2
        y_center = 0
    else:  # If taller than wide
        crop_width = int(video.w)  # Use width as height
        crop_height = int(video.w)
        x_center = 0
        y_center = (video.h - crop_height) // 2
    
    # Crop the video to square format
    cropped_video = video.crop(x1=x_center, y1=y_center, 
                             x2=x_center + crop_width, 
                             y2=y_center + crop_height)
    
    # Resize to exact target size
    cropped_video = cropped_video.resize((target_size, target_size))
    
    # Set the duration of the final video to match the adjusted duration
    cropped_video = cropped_video.set_duration(exact_duration)
    
    # Write output with high quality settings
    try:
        cropped_video.write_videofile(
            str(output_path),
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            fps=30,
            bitrate='6000k',  # High bitrate for better quality
            audio_bitrate='320k',  # High audio bitrate
            preset='veryfast',  # Faster encoding for better performance
            threads=4,  # Use multiple threads for faster processing
            verbose=False,  # Suppress MoviePy verbose output
            logger=None,    # Disable MoviePy progress bars
            ffmpeg_params=[
                '-profile:v', 'high',  # High profile for better quality
                '-level', '4.1',  # Higher level for better quality
                '-crf', '28',  # Higher CRF value for faster processing (range 0-51, higher is faster)
                '-movflags', '+faststart'  # Enable fast start for web playback
            ]
        )
    except Exception as e:
        # Clean up resources
        video.close()
        cropped_video.close()
        if Path(output_path).exists():
            Path(output_path).unlink()
        raise e
    finally:
        # Clean up resources
        video.close()
        cropped_video.close()

def create_square_blur_video_direct(input_path, output_path):
    """Create a square video with blurred background by directly calling ffmpeg."""
    # Get ffmpeg command
    ffmpeg_cmd = get_ffmpeg_path()
    ffprobe_cmd = get_ffprobe_path()
    
    try:
        # Create a temporary directory for intermediate files
        temp_dir = tempfile.mkdtemp()
        
        # Paths for intermediate files
        blurred_bg = os.path.join(temp_dir, "blurred_bg.mp4")
        resized_center = os.path.join(temp_dir, "resized_center.mp4")
        audio_file = os.path.join(temp_dir, "audio.aac")
        
        # Check if video has audio stream
        has_audio = False
        try:
            probe_cmd = [ffprobe_cmd, "-v", "error", "-select_streams", "a", 
                        "-show_entries", "stream=codec_type", "-of", "csv=s=x:p=0", 
                        input_path]
            result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
            has_audio = "audio" in result.stdout
        except subprocess.CalledProcessError:
            has_audio = False
        
        # 1. Extract audio if present
        if has_audio:
            try:
                subprocess.run([
                    ffmpeg_cmd, "-i", input_path, "-vn", "-acodec", "copy", 
                    audio_file
                ], check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                logging.error(f"Error extracting audio: {e.stderr}")
                raise
        
        # 2. Get video dimensions - with better error handling
        try:
            probe_cmd = [ffprobe_cmd, "-v", "error", "-select_streams", "v:0", 
                       "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", 
                       input_path]
            result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
            orig_width, orig_height = map(int, result.stdout.strip().split('x'))
        except subprocess.CalledProcessError as e:
            logging.error(f"Error getting video dimensions: {e.stderr}")
            raise
        except ValueError as e:
            logging.error(f"Error parsing video dimensions: {result.stdout}")
            raise
        
        # Target size is 1080x1080
        target_size = 1080
        
        # Calculate dimensions for center video - smart logic for any input size
        aspect_ratio = orig_width / orig_height
        
        if aspect_ratio > 1:  # Landscape video (wider than tall)
            # Scale to fit the width of the square, center vertically
            visible_width = target_size
            visible_height = int(visible_width / aspect_ratio)
            x_offset = 0  # No horizontal offset since width is full
            y_offset = (target_size - visible_height) // 2
        else:  # Portrait or square video (taller than wide or equal)
            # Scale to fit the height of the square, center horizontally
            visible_height = target_size
            visible_width = int(visible_height * aspect_ratio)
            x_offset = (target_size - visible_width) // 2
            y_offset = 0  # No vertical offset since height is full
        
        # Ensure dimensions are even (required by H.264)
        visible_width = visible_width if visible_width % 2 == 0 else visible_width + 1
        visible_height = visible_height if visible_height % 2 == 0 else visible_height + 1
        
        # 3. Create blurred background - with better error handling
        try:
            subprocess.run([
                ffmpeg_cmd, "-i", input_path, "-vf", 
                "scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080,boxblur=20:3", 
                "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", 
                "-threads", str(os.cpu_count() or 4),  # Use all CPU cores
                "-loglevel", "error",  # Only show errors
                blurred_bg
            ], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Error creating blurred background: {e.stderr}")
            raise
        
        # 4. Create centered video - with better error handling
        try:
            subprocess.run([
                ffmpeg_cmd, "-i", input_path, "-vf", 
                f"scale={visible_width}:{visible_height}", 
                "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", 
                "-threads", str(os.cpu_count() or 4),  # Use all CPU cores
                resized_center
            ], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Error creating centered video: {e.stderr}")
            raise
        
        # 5. Overlay centered video on blurred background - with better error handling
        try:
            if has_audio:
                subprocess.run([
                    ffmpeg_cmd, "-i", blurred_bg, "-i", resized_center, "-i", audio_file,
                    "-filter_complex", f"[0:v][1:v] overlay={x_offset}:{y_offset} [outv]", 
                    "-map", "[outv]", "-map", "2:a", "-c:v", "libx264", "-c:a", "aac",
                    "-shortest", output_path
                ], check=True, capture_output=True, text=True)
            else:
                subprocess.run([
                    ffmpeg_cmd, "-i", blurred_bg, "-i", resized_center,
                    "-filter_complex", f"[0:v][1:v] overlay={x_offset}:{y_offset} [outv]", 
                    "-map", "[outv]", "-c:v", "libx264",
                    "-shortest", output_path
                ], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Error overlaying videos: {e.stderr}")
            raise
        
    except subprocess.CalledProcessError as e:
        # Clean up and raise an error with more details
        error_msg = f"FFmpeg error: {e.stderr if hasattr(e, 'stderr') else 'Unknown error'}"
        logging.error(error_msg)
        if Path(output_path).exists():
            Path(output_path).unlink()
        raise Exception(error_msg)
    except Exception as e:
        # Handle other exceptions
        logging.error(f"Unexpected error: {str(e)}")
        if Path(output_path).exists():
            Path(output_path).unlink()
        raise
    finally:
        # Clean up temp files
        for file in [blurred_bg, resized_center, audio_file]:
            if Path(file).exists():
                Path(file).unlink()
        if Path(temp_dir).exists():
            Path(temp_dir).rmdir()

def create_square_blur_video(input_path, output_path):
    """
    Create a square video with blurred background (wrapper for the direct implementation).
    This function maintains backwards compatibility.
    """
    # Just call the direct implementation
    create_square_blur_video_direct(input_path, output_path)

def create_landscape_video_direct(input_path, output_path):
    """Create a landscape video by directly calling ffmpeg."""
    # Get ffmpeg command
    ffmpeg_cmd = get_ffmpeg_path()
    ffprobe_cmd = get_ffprobe_path()
    
    try:
        # Create a temporary directory for intermediate files
        temp_dir = tempfile.mkdtemp()
        
        # Paths for intermediate files
        blurred_bg = os.path.join(temp_dir, "blurred_bg.mp4")
        resized_center = os.path.join(temp_dir, "resized_center.mp4")
        audio_file = os.path.join(temp_dir, "audio.aac")
        
        # Check if video has audio stream
        has_audio = False
        try:
            probe_cmd = [ffprobe_cmd, "-v", "error", "-select_streams", "a", 
                        "-show_entries", "stream=codec_type", "-of", "csv=s=x:p=0", 
                        input_path]
            result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
            has_audio = "audio" in result.stdout
        except subprocess.CalledProcessError:
            has_audio = False
        
        # 1. Extract audio if present
        if has_audio:
            try:
                subprocess.run([
                    ffmpeg_cmd, "-i", input_path, "-vn", "-acodec", "copy", 
                    audio_file
                ], check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                logging.error(f"Error extracting audio: {e.stderr}")
                raise
        
        # 2. Get video dimensions - with better error handling
        try:
            probe_cmd = [ffprobe_cmd, "-v", "error", "-select_streams", "v:0", 
                       "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", 
                       input_path]
            result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
            orig_width, orig_height = map(int, result.stdout.strip().split('x'))
        except subprocess.CalledProcessError as e:
            logging.error(f"Error getting video dimensions: {e.stderr}")
            raise
        except ValueError as e:
            logging.error(f"Error parsing video dimensions: {result.stdout}")
            raise
        
        # Target dimensions for landscape (1920x1080)
        canvas_width = 1920
        canvas_height = 1080
        
        # Calculate dimensions for center video while maintaining aspect ratio
        # For landscape format, we want to preserve the original video size as much as possible
        # and add blurred areas on the sides if needed
        aspect_ratio = orig_width / orig_height
        
        # Scale the video to fit the height of the canvas (1080), preserving aspect ratio
        target_height = canvas_height  # Always use full height (1080)
        target_width = int(target_height * aspect_ratio)
        
        # If the scaled width is larger than canvas width, scale down to fit
        if target_width > canvas_width:
            target_width = canvas_width
            target_height = int(target_width / aspect_ratio)
        
        # Ensure dimensions are even (required by H.264)
        target_width = target_width if target_width % 2 == 0 else target_width + 1
        target_height = target_height if target_height % 2 == 0 else target_height + 1
        
        # 3. Create blurred background - with better error handling
        try:
            subprocess.run([
                ffmpeg_cmd, "-i", input_path, "-vf", 
                f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,boxblur=20:5", 
                "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", 
                "-threads", str(os.cpu_count() or 4),  # Use all CPU cores
                blurred_bg
            ], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Error creating blurred background: {e.stderr}")
            raise
        
        # 4. Create centered video - with better error handling
        try:
            subprocess.run([
                ffmpeg_cmd, "-i", input_path, "-vf", 
                f"scale={target_width}:{target_height}", 
                "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", 
                "-threads", str(os.cpu_count() or 4),  # Use all CPU cores
                resized_center
            ], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Error creating centered video: {e.stderr}")
            raise
        
        # 5. Overlay centered video on blurred background
        # Calculate position for centered overlay
        x_offset = (canvas_width - target_width) // 2
        y_offset = (canvas_height - target_height) // 2
        
        # Composite videos - with better error handling
        try:
            if has_audio:
                subprocess.run([
                    ffmpeg_cmd, "-i", blurred_bg, "-i", resized_center, "-i", audio_file,
                    "-filter_complex", f"[0:v][1:v] overlay={x_offset}:{y_offset} [outv]", 
                    "-map", "[outv]", "-map", "2:a", "-c:v", "libx264", "-c:a", "aac",
                    "-shortest", output_path
                ], check=True, capture_output=True, text=True)
            else:
                subprocess.run([
                    ffmpeg_cmd, "-i", blurred_bg, "-i", resized_center,
                    "-filter_complex", f"[0:v][1:v] overlay={x_offset}:{y_offset} [outv]", 
                    "-map", "[outv]", "-c:v", "libx264",
                    "-shortest", output_path
                ], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Error overlaying videos: {e.stderr}")
            raise
        
    except subprocess.CalledProcessError as e:
        # Clean up and raise an error with more details
        error_msg = f"FFmpeg error: {e.stderr if hasattr(e, 'stderr') else 'Unknown error'}"
        logging.error(error_msg)
        if Path(output_path).exists():
            Path(output_path).unlink()
        raise Exception(error_msg)
    except Exception as e:
        # Handle other exceptions
        logging.error(f"Unexpected error: {str(e)}")
        if Path(output_path).exists():
            Path(output_path).unlink()
        raise
    finally:
        # Clean up temp files
        for file in [blurred_bg, resized_center, audio_file]:
            if Path(file).exists():
                Path(file).unlink()
        if Path(temp_dir).exists():
            Path(temp_dir).rmdir()

def create_landscape_video(input_path, output_path):
    """
    Create a landscape video (wrapper for the direct implementation).
    This function maintains backwards compatibility.
    """
    # Just call the direct implementation
    create_landscape_video_direct(input_path, output_path)

def get_video_metadata(video_path):
    """Get metadata for a video file"""
    try:
        video = VideoFileClip(video_path)
        duration = video.duration
        size_mb = os.path.getsize(video_path) / (1024 * 1024)
        video.close()
        return {
            "duration": f"{duration:.2f} seconds",
            "size": f"{size_mb:.2f} MB"
        }
    except Exception as e:
        return {
            "duration": "Unknown",
            "size": "Unknown"
        }

# Cache for ffmpeg and ffprobe paths to avoid repeated detection
_ffmpeg_cache = None
_ffprobe_cache = None

def get_ffmpeg_path():
    """Get the ffmpeg binary path - use system-installed ffmpeg from nixpacks."""
    global _ffmpeg_cache
    
    # Return cached result if available
    if _ffmpeg_cache is not None:
        return _ffmpeg_cache
    
    import shutil
    import logging
    
    # Try environment variable first
    env_ffmpeg = os.environ.get('FFMPEG_BINARY')
    if env_ffmpeg and os.path.exists(env_ffmpeg):
        logging.info(f"Found ffmpeg via environment: {env_ffmpeg}")
        _ffmpeg_cache = env_ffmpeg
        return _ffmpeg_cache
    
    # Try system PATH (Railway's nixpacks installs ffmpeg here)
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        logging.info(f"Found ffmpeg in PATH: {ffmpeg_path}")
        _ffmpeg_cache = ffmpeg_path
        return _ffmpeg_cache
    
    # Try common locations
    common_paths = [
        "/usr/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        "/opt/homebrew/bin/ffmpeg",
        "/nix/store/*/bin/ffmpeg"  # Nix store location
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            logging.info(f"Found ffmpeg at: {path}")
            _ffmpeg_cache = path
            return _ffmpeg_cache
    
    logging.error("Could not find ffmpeg anywhere!")
    raise FileNotFoundError("ffmpeg not found. Please ensure ffmpeg is installed via nixpacks.")

def get_ffprobe_path():
    """Get the ffprobe binary path - use system-installed ffprobe from nixpacks."""
    global _ffprobe_cache
    
    # Return cached result if available
    if _ffprobe_cache is not None:
        return _ffprobe_cache
    
    import shutil
    import logging
    
    # Try environment variable first
    env_ffprobe = os.environ.get('FFPROBE_BINARY')
    if env_ffprobe and os.path.exists(env_ffprobe):
        logging.info(f"Found ffprobe via environment: {env_ffprobe}")
        _ffprobe_cache = env_ffprobe
        return _ffprobe_cache
    
    # Try system PATH (Railway's nixpacks installs ffprobe here)
    ffprobe_path = shutil.which("ffprobe")
    if ffprobe_path:
        logging.info(f"Found ffprobe in PATH: {ffprobe_path}")
        _ffprobe_cache = ffprobe_path
        return _ffprobe_cache
    
    # Try common locations
    common_paths = [
        "/usr/bin/ffprobe",
        "/usr/local/bin/ffprobe", 
        "/opt/homebrew/bin/ffprobe",
        "/nix/store/*/bin/ffprobe"  # Nix store location
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            logging.info(f"Found ffprobe at: {path}")
            _ffprobe_cache = path
            return _ffprobe_cache
    
    # If ffprobe is not available, we can use ffmpeg for probing
    logging.warning("ffprobe not found, using ffmpeg as fallback")
    try:
        ffmpeg_path = get_ffmpeg_path()
        _ffprobe_cache = ffmpeg_path
        return _ffprobe_cache
    except FileNotFoundError:
        logging.error("Could not find ffprobe or ffmpeg anywhere!")
        raise FileNotFoundError("ffprobe not found. Please ensure ffmpeg is installed via nixpacks.")
    
def use_ffmpeg_for_probe(ffprobe_cmd, input_path):
    """Helper function to use ffmpeg for probing when ffprobe is not available."""
    ffmpeg_cmd = get_ffmpeg_path()
    
    # Check if we're using ffmpeg as ffprobe
    if ffprobe_cmd == ffmpeg_cmd:
        # Replace ffprobe commands with equivalent ffmpeg commands
        return True
    return False

def create_vertical_blur_video_direct(input_path, output_path):
    """Create a vertical video with blurred background by directly calling ffmpeg."""
    # Get ffmpeg command
    ffmpeg_cmd = get_ffmpeg_path()
    ffprobe_cmd = get_ffprobe_path()
    
    try:
        # Create a temporary directory for intermediate files
        temp_dir = tempfile.mkdtemp()
        
        # Paths for intermediate files
        blurred_bg = os.path.join(temp_dir, "blurred_bg.mp4")
        resized_center = os.path.join(temp_dir, "resized_center.mp4")
        audio_file = os.path.join(temp_dir, "audio.aac")
        
        # Check if video has audio stream
        has_audio = False
        try:
            probe_cmd = [ffprobe_cmd, "-v", "error", "-select_streams", "a", 
                        "-show_entries", "stream=codec_type", "-of", "csv=s=x:p=0", 
                        input_path]
            result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
            has_audio = "audio" in result.stdout
        except subprocess.CalledProcessError:
            has_audio = False
        
        # 1. Extract audio if present
        if has_audio:
            try:
                subprocess.run([
                    ffmpeg_cmd, "-i", input_path, "-vn", "-acodec", "copy", 
                    audio_file
                ], check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                logging.error(f"Error extracting audio: {e.stderr}")
                raise
        
        # 2. Get video dimensions - with better error handling
        try:
            probe_cmd = [ffprobe_cmd, "-v", "error", "-select_streams", "v:0", 
                       "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", 
                       input_path]
            result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
            orig_width, orig_height = map(int, result.stdout.strip().split('x'))
        except subprocess.CalledProcessError as e:
            logging.error(f"Error getting video dimensions: {e.stderr}")
            raise
        except ValueError as e:
            logging.error(f"Error parsing video dimensions: {result.stdout}")
            raise
        
        # Target dimensions for vertical (1080x1920)
        canvas_width = 1080
        canvas_height = 1920
        
        # Calculate dimensions for center video while maintaining aspect ratio
        # For vertical format, we want to preserve the original video size as much as possible
        # and add blurred areas on the top/bottom if needed
        aspect_ratio = orig_width / orig_height
        
        # Scale the video to fit the width of the canvas (1080), preserving aspect ratio
        visible_width = canvas_width  # Always use full width (1080)
        visible_height = int(visible_width / aspect_ratio)
        
        # If the scaled height is larger than canvas height, scale down to fit
        if visible_height > canvas_height:
            visible_height = canvas_height
            visible_width = int(visible_height * aspect_ratio)
        
        # Ensure dimensions are even (required by H.264)
        visible_width = visible_width if visible_width % 2 == 0 else visible_width + 1
        visible_height = visible_height if visible_height % 2 == 0 else visible_height + 1
        
        # Calculate position to center the video
        x_offset = (canvas_width - visible_width) // 2
        y_offset = (canvas_height - visible_height) // 2
        
        # 3. Create blurred background - with better error handling
        try:
            subprocess.run([
                ffmpeg_cmd, "-i", input_path, "-vf", 
                f"scale={canvas_width}:{canvas_height}:force_original_aspect_ratio=increase,crop={canvas_width}:{canvas_height},boxblur=20:3", 
                "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", 
                "-threads", str(os.cpu_count() or 4),  # Use all CPU cores
                blurred_bg
            ], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Error creating blurred background: {e.stderr}")
            raise
        
        # 4. Create centered video - with better error handling
        try:
            subprocess.run([
                ffmpeg_cmd, "-i", input_path, "-vf", 
                f"scale={visible_width}:{visible_height}", 
                "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", 
                "-threads", str(os.cpu_count() or 4),  # Use all CPU cores
                resized_center
            ], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Error creating centered video: {e.stderr}")
            raise
        
        # 5. Overlay centered video on blurred background - with better error handling
        try:
            if has_audio:
                subprocess.run([
                    ffmpeg_cmd, "-i", blurred_bg, "-i", resized_center, "-i", audio_file,
                    "-filter_complex", f"[0:v][1:v] overlay={x_offset}:{y_offset} [outv]", 
                    "-map", "[outv]", "-map", "2:a", "-c:v", "libx264", "-c:a", "aac",
                    "-shortest", output_path
                ], check=True, capture_output=True, text=True)
            else:
                subprocess.run([
                    ffmpeg_cmd, "-i", blurred_bg, "-i", resized_center,
                    "-filter_complex", f"[0:v][1:v] overlay={x_offset}:{y_offset} [outv]", 
                    "-map", "[outv]", "-c:v", "libx264",
                    "-shortest", output_path
                ], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Error overlaying videos: {e.stderr}")
            raise
        
    except subprocess.CalledProcessError as e:
        # Clean up and raise an error with more details
        error_msg = f"FFmpeg error: {e.stderr if hasattr(e, 'stderr') else 'Unknown error'}"
        logging.error(error_msg)
        if Path(output_path).exists():
            Path(output_path).unlink()
        raise Exception(error_msg)
    except Exception as e:
        # Handle other exceptions
        logging.error(f"Unexpected error: {str(e)}")
        if Path(output_path).exists():
            Path(output_path).unlink()
        raise
    finally:
        # Clean up temp files
        for file in [blurred_bg, resized_center, audio_file]:
            if Path(file).exists():
                Path(file).unlink()
        if Path(temp_dir).exists():
            Path(temp_dir).rmdir()

def create_vertical_blur_video(input_path, output_path):
    """
    Create a vertical video with blurred background (wrapper for the direct implementation).
    This function maintains backwards compatibility.
    """
    # Just call the direct implementation
    create_vertical_blur_video_direct(input_path, output_path) 
