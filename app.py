from flask import Flask, render_template, request, jsonify, send_file, make_response, session, redirect, url_for
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
from tools_config import get_active_tools

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB max file size (reduced for memory)

# Use a persistent directory for uploads instead of temp directory
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

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
app_logger = logging.getLogger('main_app')
app_logger.setLevel(logging.INFO)

@app.route('/')
def index():
    """Main landing page - redirect to video converter"""
    return redirect('/video-converter')

@app.route('/video-converter')
def video_converter():
    """Video converter tool"""
    from tools_config import TOOLS_CONFIG
    tools = get_active_tools()
    return render_template('index.html', tools=tools, tools_config=TOOLS_CONFIG)

@app.route('/adlocalizer')
def adlocalizer():
    """AdLocalizer tool"""
    from tools_config import TOOLS_CONFIG
    tools = get_active_tools()
    
    # Import AdLocalizer specific data
    LANGUAGES = {
        "JP": "Japanese",
        "CN": "Traditional Chinese",
        "DE": "German",
        "IN": "Hindi",
        "FR": "French",
        "KR": "Korean",
        "BR": "Brazilian Portuguese",
        "IT": "Italian",
        "ES": "Spanish",
        "ID": "Indonesian",
        "TR": "Turkish",
        "PH": "Filipino",
        "PL": "Polish",
        "SA": "Arabic",
        "MY": "Malay",
        "VN": "Vietnamese",
        "TH": "Thai"
    }
    
    VOICES = {
        "1": {"name": "Tom Cruise", "id": "g60FwKJuhCJqbDCeuXjm"},
        "2": {"name": "Doja Cat", "id": "E1c1pVuZVvPrme6B9ryw"},
        "3": {"name": "Chris", "id": "iP95p4xoKVk53GoZ742B"}
    }
    
    return render_template('adlocalizer.html', languages=LANGUAGES, voices=VOICES, tools=tools, tools_config=TOOLS_CONFIG)

@app.route('/vocal-removal-test')
def vocal_removal_test():
    """Direct vocal removal testing page"""
    return render_template('vocal_removal_test.html')

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.now().isoformat(),
        'port': request.environ.get('SERVER_PORT', 'unknown'),
        'services': ['video-converter', 'adlocalizer']
    })

@app.route('/api/test')
def api_test():
    return jsonify({'message': 'API routes are working', 'timestamp': datetime.now().isoformat()})

# Import video converter routes
from video_converter_app import (
    upload_files, get_job_status, download_file, download_zip, 
    cleanup_job, cancel_job, process_videos_background
)

# Import and register AdLocalizer routes directly
@app.route('/api/translate', methods=['POST'])
def api_translate():
    print("=== API TRANSLATE ENDPOINT CALLED ===")
    app.logger.info("API translate endpoint called")
    try:
        from adlocalizer_app import translate
        result = translate()
        print(f"Translation result: {result}")
        return result
    except ImportError as e:
        print(f"Import error in translate: {e}")
        return jsonify({'error': 'AdLocalizer functionality not available'}), 500
    except Exception as e:
        print(f"Unexpected error in translate: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-voice', methods=['POST'])
def api_generate_voice():
    try:
        from adlocalizer_app import generate_voice
        return generate_voice()
    except ImportError:
        return jsonify({'error': 'AdLocalizer functionality not available'}), 500

@app.route('/api/upload-video', methods=['POST'])
def api_upload_video():
    try:
        from adlocalizer_app import upload_video
        return upload_video()
    except ImportError:
        return jsonify({'error': 'AdLocalizer functionality not available'}), 500

@app.route('/api/remove-vocals', methods=['POST'])
def api_remove_vocals():
    print("=== API REMOVE VOCALS ENDPOINT CALLED ===")
    app.logger.info("API remove vocals endpoint called")
    try:
        from adlocalizer_app import remove_vocals
        result = remove_vocals()
        print(f"Vocal removal result: {result}")
        return result
    except ImportError as e:
        print(f"Import error: {e}")
        return jsonify({'error': 'AdLocalizer functionality not available'}), 500
    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/vocal-models', methods=['GET'])
def api_get_vocal_models():
    """Get available vocal removal models"""
    try:
        print("=== VOCAL MODELS API ENDPOINT CALLED ===")
        
        # Force clear any cached imports and reload
        import sys
        if 'vocal_models_config' in sys.modules:
            del sys.modules['vocal_models_config']
        
        import vocal_models_config
        from vocal_models_config import get_available_models, get_default_model, check_replicate_available, VOCAL_REMOVAL_MODELS
        
        print(f"DEBUG: All defined models: {list(VOCAL_REMOVAL_MODELS.keys())}")
        print(f"DEBUG: Replicate available: {check_replicate_available()}")
        
        models = get_available_models()
        default_model = get_default_model()
        
        print(f"DEBUG: Available models returned: {list(models.keys())}")
        print(f"DEBUG: Default model: {default_model}")
        
        return jsonify({
            'success': True,
            'models': models,
            'default_model': default_model
        })
    except ImportError as e:
        print(f"Import error: {e}")
        return jsonify({'error': 'Vocal models configuration not available'}), 500
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-vocal-removal', methods=['POST'])
def api_test_vocal_removal():
    """Test endpoint for vocal removal - direct testing without full workflow"""
    try:
        from adlocalizer_app import remove_vocals_from_video
        from vocal_models_config import get_available_models, get_default_model
        import tempfile
        import shutil
        
        # Get the uploaded video file
        if 'video' not in request.files:
            return jsonify({'error': 'No video file uploaded'}), 400
        
        video_file = request.files['video']
        if video_file.filename == '':
            return jsonify({'error': 'No video file selected'}), 400
        
        # Get model selection
        model_id = request.form.get('model_id', get_default_model())
        
        # Validate model
        available_models = get_available_models()
        if model_id not in available_models:
            return jsonify({'error': f'Invalid model: {model_id}'}), 400
        
        # Create temporary directory for processing
        temp_dir = tempfile.mkdtemp()
        video_path = os.path.join(temp_dir, secure_filename(video_file.filename))
        video_file.save(video_path)
        
        try:
            # Process vocal removal
            instrumental_path = remove_vocals_from_video(video_path, temp_dir, model_id)
            
            if instrumental_path and os.path.exists(instrumental_path):
                # Return the processed file
                return send_file(
                    instrumental_path,
                    as_attachment=True,
                    download_name=f"instrumental_{os.path.basename(video_file.filename)}"
                )
            else:
                return jsonify({'error': 'Vocal removal failed - no output file generated'}), 500
                
        finally:
            # Clean up temporary files
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
                
    except Exception as e:
        print(f"Test vocal removal error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/mix-audio', methods=['POST'])
def api_mix_audio():
    try:
        from adlocalizer_app import mix_audio
        return mix_audio()
    except ImportError:
        return jsonify({'error': 'AdLocalizer functionality not available'}), 500

@app.route('/api/upload-custom-music', methods=['POST'])
def api_upload_custom_music():
    try:
        from adlocalizer_app import upload_custom_music
        return upload_custom_music()
    except ImportError:
        return jsonify({'error': 'AdLocalizer functionality not available'}), 500

@app.route('/api/transcribe', methods=['POST'])
def api_transcribe():
    try:
        from adlocalizer_app import transcribe
        return transcribe()
    except ImportError as e:
        import traceback
        logging.error(f"Import error: {str(e)}")
        logging.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'AdLocalizer functionality not available: {str(e)}'}), 500
    except Exception as e:
        import traceback
        logging.error(f"Other error in api_transcribe: {str(e)}")
        logging.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/audio/<path:filepath>')
def api_serve_audio(filepath):
    try:
        from adlocalizer_app import serve_audio
        return serve_audio(filepath)
    except ImportError:
        return jsonify({'error': 'AdLocalizer functionality not available'}), 500

@app.route('/video/<path:filepath>')
def api_serve_video(filepath):
    try:
        from adlocalizer_app import serve_video
        return serve_video(filepath)
    except ImportError:
        return jsonify({'error': 'AdLocalizer functionality not available'}), 500

@app.route('/api/download-all')
def api_download_all():
    try:
        from adlocalizer_app import download_all_adlocalizer
        return download_all_adlocalizer()
    except ImportError:
        return jsonify({'error': 'AdLocalizer functionality not available'}), 500

# Register video converter routes
app.add_url_rule('/upload', 'upload_files', upload_files, methods=['POST'])
app.add_url_rule('/status/<job_id>', 'get_job_status', get_job_status)
app.add_url_rule('/download/<job_id>/<filename>', 'download_file', download_file)
app.add_url_rule('/download_zip/<job_id>', 'download_zip', download_zip)
app.add_url_rule('/cleanup/<job_id>', 'cleanup_job', cleanup_job, methods=['POST'])
app.add_url_rule('/cancel/<job_id>', 'cancel_job', cancel_job, methods=['POST'])

# Add AdLocalizer download route with different path to avoid conflicts
@app.route('/adlocalizer/download/<filename>')
def download_adlocalizer_file_route(filename):
    try:
        from adlocalizer_app import download_adlocalizer_file
        return download_adlocalizer_file(filename)
    except ImportError:
        return jsonify({'error': 'AdLocalizer functionality not available'}), 500

# Import WIP tool routes
@app.route('/static-generator')
def static_generator():
    from tools_config import TOOLS_CONFIG
    tools = get_active_tools()
    return render_template('wip_tool.html', 
                         tool_name="Static Generator", 
                         tool_description="Generate static content and assets",
                         tool_icon="fas fa-file-code",
                         tools=tools, 
                         tools_config=TOOLS_CONFIG)

@app.route('/hook-remixer')
def hook_remixer():
    from tools_config import TOOLS_CONFIG
    tools = get_active_tools()
    return render_template('wip_tool.html', 
                         tool_name="Hook Remixer", 
                         tool_description="AI-powered music hook generation and remixing",
                         tool_icon="fas fa-music",
                         tools=tools, 
                         tools_config=TOOLS_CONFIG)

@app.route('/montage-maker')
def montage_maker():
    from tools_config import TOOLS_CONFIG
    tools = get_active_tools()
    return render_template('wip_tool.html', 
                         tool_name="Montage Maker", 
                         tool_description="Automated video montage creation",
                         tool_icon="fas fa-film",
                         tools=tools, 
                         tools_config=TOOLS_CONFIG)

if __name__ == '__main__':
    # For Railway deployment, use PORT environment variable
    # For local development, use command line args
    port = int(os.environ.get('PORT', 8000))
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=port, help='Port to run the server on')
    args = parser.parse_args()
    
    # Use Railway's PORT if available, otherwise use command line args
    final_port = int(os.environ.get('PORT', args.port))
    
    print(f"Starting Main Flask app on port {final_port}")
    print(f"Environment PORT: {os.environ.get('PORT', 'Not set')}")
    print(f"Available services: Video Converter, AdLocalizer")
    
    try:
        app.run(host='0.0.0.0', port=final_port, debug=False)
    except Exception as e:
        print(f"Failed to start Flask app: {e}")
        raise 