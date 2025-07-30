from flask import request, jsonify, send_file, session
import os
import logging
from pathlib import Path
import json
from datetime import datetime
import re
import uuid
import io
import zipfile
from openai import OpenAI
from dotenv import load_dotenv
import requests
import subprocess
import ffmpeg

# Import vocal models configuration
from vocal_models_config import (
    get_model_config, 
    get_available_models, 
    get_default_model,
    validate_model_id
)

# Load environment variables
load_dotenv()

# Get API keys for AdLocalizer
def get_secret(key):
    """Get secret from environment variable"""
    value = os.getenv(key)
    if not value:
        logging.warning(f"Missing API Key: {key} - AdLocalizer features will not work")
        return None
    return value

# Initialize API clients (only if keys are available)
openai_client = None
eleven_labs_client = None

try:
    openai_api_key = get_secret("OPENAI_API_KEY")
    elevenlabs_api_key = get_secret("ELEVENLABS_API_KEY")
    
    if openai_api_key:
        openai_client = OpenAI(api_key=openai_api_key)
    if elevenlabs_api_key:
        from elevenlabs.client import ElevenLabs
        eleven_labs_client = ElevenLabs(api_key=elevenlabs_api_key)
        
except Exception as e:
    logging.warning(f"Error initializing API clients: {e}")

# Voice options for AdLocalizer
VOICES = {
    "1": {"name": "Tom Cruise", "id": "g60FwKJuhCJqbDCeuXjm"},
    "2": {"name": "Doja Cat", "id": "E1c1pVuZVvPrme6B9ryw"},
    "3": {"name": "Chris", "id": "iP95p4xoKVk53GoZ742B"}
}

# Language codes and names for AdLocalizer
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

def get_enhanced_system_message(target_language, mode="faithful"):
    """Get enhanced system message for more localized translations"""
    if mode == "faithful":
        base_message = f"""You are a professional translator and localization expert for {target_language}, specializing in video scripts and voiceovers. Follow these guidelines carefully:

1. Translate the text super naturally, as a native speaker from the target region would.
2. Adapt idioms, expressions, and cultural references to suit the local audience authentically.
3. Use appropriate tone and formality for the cultural and situational context.
4. Keep brand names, product names, and proper nouns in English.
5. Keep the translation concise and natural-sounding to avoid significantly longer delivery times than the original.
6. Return the translation as a single, continuous paragraph—no line breaks or multiple paragraphs.
7. Provide only the translated text, with no explanations, annotations, or formatting.

Important: The translation should read fluidly in {target_language}, feel culturally localized, and be reasonably aligned in pacing for video or audio use."""
    
    elif mode == "creative":
        base_message = f"""You are a creative translator and cultural expert for {target_language} who specializes in highly engaging, localized content. Your goal is to make the translation sound EXTREMELY NATIVE, as if originally created by a local for locals. Follow these guidelines:

1. Focus on capturing the core message and emotional impact rather than literal translation.
2. Use popular slang, colloquial expressions, and regional phrases that are currently trendy in {target_language}-speaking regions.
3. Transform cultural references to local equivalents that will resonate deeply with native speakers.
4. Maintain the hook/key message of the first sentence, but feel free to creatively adapt the rest.
5. Match the speaking style of a native influencer or content creator from the region.
6. Use the exact tone, rhythm, and speech patterns that are distinctly characteristic of the culture.
7. Keep brand names in English but adapt surrounding language to sound natural.
8. Return only the translated text as a single paragraph with no explanations.
9. Keep the translation length SIMILAR to the original text

Important: The translation should sound completely authentic to native speakers, as if it was originally conceived in their language and culture - NOT like a translation at all. Use expressions only locals would know and appreciate."""
    
    return base_message

def translate_text(text, target_language, translation_mode="faithful"):
    """Translation using OpenAI"""
    if not openai_client:
        return None
        
    try:
        system_message = get_enhanced_system_message(target_language, translation_mode)
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": text}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Error translating to {target_language}: {str(e)}")
        return None

def generate_elevenlabs_voice(text, language_code, output_directory, english_identifier, voice_id):
    """Generate voice using ElevenLabs API"""
    if not eleven_labs_client:
        return None
        
    try:
        voice_name = next((v["name"] for v in VOICES.values() if v["id"] == voice_id), "Unknown")
        safe_name = f"{voice_name}_{language_code}_{english_identifier}"
        output_file = f"{output_directory}/{safe_name}.mp3"
        
        elevenlabs_api_key = get_secret("ELEVENLABS_API_KEY")
        if not elevenlabs_api_key:
            return None
            
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": elevenlabs_api_key
        }
        
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 200:
            with open(output_file, "wb") as f:
                f.write(response.content)
            return output_file
        else:
            logging.error(f"Error from ElevenLabs API: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logging.error(f"Error generating voice: {str(e)}")
        return None

def extract_audio_from_video(video_path, output_audio_path):
    """Extract audio from video using ffmpeg"""
    try:
        (
            ffmpeg
            .input(str(video_path))
            .output(str(output_audio_path), acodec='pcm_s16le', ac=1, ar='16000')
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        return True
    except ffmpeg.Error as e:
        logging.error(f"Error extracting audio: {e.stderr.decode() if e.stderr else str(e)}")
        return False
    except Exception as e:
        logging.error(f"Error extracting audio: {str(e)}")
        return False

def transcribe_audio(audio_file_path):
    """Transcribe audio using OpenAI Whisper"""
    if not openai_client:
        return None
        
    try:
        with open(audio_file_path, "rb") as audio_file:
            transcription = openai_client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-1",
                response_format="text",
                prompt="This is a marketing video or advertisement. Please transcribe accurately."
            )
        return transcription
    except Exception as e:
        logging.error(f"Error transcribing audio: {str(e)}")
        return None

def transcribe_video(video_file_path):
    """Complete transcription workflow for video file"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        temp_dir = Path("temp_transcription")
        temp_dir.mkdir(exist_ok=True)
        
        temp_audio_path = temp_dir / f"temp_audio_{timestamp}.wav"
        
        if not extract_audio_from_video(video_file_path, temp_audio_path):
            return None
        
        transcription = transcribe_audio(temp_audio_path)
        
        # Clean up temporary files
        try:
            os.remove(temp_audio_path)
            if temp_dir.exists() and not any(temp_dir.iterdir()):
                temp_dir.rmdir()
        except Exception as e:
            logging.warning(f"Error cleaning up temp files: {str(e)}")
        
        return transcription
        
    except Exception as e:
        logging.error(f"Error in transcribe_video function: {str(e)}")
        return None

def mix_audio_with_video(audio_file, video_file, output_file, original_volume=0.8, voiceover_volume=1.3, use_instrumental=False):
    """Mix audio with video using ffmpeg-python"""
    try:
        video = ffmpeg.input(str(video_file))
        audio = ffmpeg.input(str(audio_file))
        
        # If using instrumental version, we don't need to lower the original volume as much
        if use_instrumental:
            original_volume = min(original_volume * 1.5, 1.0)  # Boost instrumental audio a bit
        
        mixed_audio = ffmpeg.filter([
            ffmpeg.filter(video.audio, 'volume', original_volume),
            ffmpeg.filter(audio, 'volume', voiceover_volume)
        ], 'amix', inputs=2, duration='first')
        
        ffmpeg.output(
            video.video,
            mixed_audio,
            str(output_file),
            acodec='aac',
            vcodec='copy'
        ).overwrite_output().run(capture_stdout=True, capture_stderr=True)
        
        return True
    except ffmpeg.Error as e:
        logging.error(f"Error in audio mixing: {e.stderr.decode() if e.stderr else str(e)}")
        return False
    except Exception as e:
        logging.error(f"Error in audio mixing: {str(e)}")
        return False

# ===== ADLOCALIZER ROUTES =====

def translate():
    try:
        # Debug logging
        logging.info("=== TRANSLATE FUNCTION CALLED ===")
        
        data = request.get_json()
        logging.info(f"Request data: {data}")
        
        text = data.get('text', '').strip()
        languages = data.get('languages', [])
        translation_mode = data.get('translation_mode', 'faithful')
        
        logging.info(f"Text: '{text[:100]}...' (length: {len(text)})")
        logging.info(f"Languages: {languages}")
        logging.info(f"Translation mode: {translation_mode}")
        
        if not text or not languages:
            logging.error("Missing text or languages in request")
            return jsonify({'error': 'Text and languages are required'}), 400
        
        # Check if OpenAI client is available
        logging.info(f"OpenAI client available: {openai_client is not None}")
        if not openai_client:
            logging.error("OpenAI client not initialized")
            return jsonify({'error': 'OpenAI API key not configured. Please set OPENAI_API_KEY environment variable.'}), 500
        
        translations = {}
        for lang_code in languages:
            if lang_code in LANGUAGES:
                lang_name = LANGUAGES[lang_code]
                logging.info(f"Translating to {lang_name} ({lang_code})")
                translation = translate_text(text, lang_name, translation_mode)
                if translation:
                    logging.info(f"Translation successful for {lang_code}: '{translation[:50]}...'")
                    translations[lang_code] = translation
                else:
                    logging.error(f"Translation failed for {lang_code}")
            else:
                logging.warning(f"Unknown language code: {lang_code}")
        
        if not translations:
            logging.error("No translations were generated")
            return jsonify({'error': 'No translations were generated. Please check your OpenAI API key.'}), 500
        
        logging.info(f"Returning {len(translations)} translations")
        return jsonify({'translations': translations})
    except Exception as e:
        logging.error(f"Translation error: {str(e)}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

def generate_voice():
    try:
        data = request.get_json()
        translations = data.get('translations', {})
        voice_id = data.get('voice_id')
        
        if not translations or not voice_id:
            return jsonify({'error': 'Translations and voice_id are required'}), 400
        
        # Check if ElevenLabs client is available
        if not eleven_labs_client:
            return jsonify({'error': 'ElevenLabs API key not configured. Please set ELEVENLABS_API_KEY environment variable.'}), 500
        
        # Create session-specific directories
        session_id = session.get('session_id', str(uuid.uuid4()))
        session['session_id'] = session_id
        
        base_dir = Path(f"temp_files/{session_id}")
        audio_dir = base_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        
        audio_files = {}
        # Create a clean identifier from the first translation (max 20 chars)
        raw_text = list(translations.values())[0][:20]
        # Replace sequences of non-alphanumeric characters with single underscore
        english_identifier = re.sub(r'[^a-zA-Z0-9]+', '_', raw_text.strip())
        # Remove leading/trailing underscores
        english_identifier = english_identifier.strip('_')
        
        for lang_code, translation in translations.items():
            output_file = generate_elevenlabs_voice(
                translation, lang_code, str(audio_dir), english_identifier, voice_id
            )
            if output_file:
                audio_files[lang_code] = output_file
        
        if not audio_files:
            return jsonify({'error': 'No audio files were generated. Please check your ElevenLabs API key.'}), 500
        
        session['audio_files'] = audio_files
        return jsonify({'audio_files': audio_files})
    except Exception as e:
        logging.error(f"Voice generation error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def upload_video():
    try:
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400
        
        video_file = request.files['video']
        if video_file.filename == '':
            return jsonify({'error': 'No video file selected'}), 400
        
        # Create session-specific directories
        session_id = session.get('session_id', str(uuid.uuid4()))
        session['session_id'] = session_id
        
        base_dir = Path(f"temp_files/{session_id}")
        video_dir = base_dir / "video"
        video_dir.mkdir(parents=True, exist_ok=True)
        
        # Save video file
        video_path = video_dir / video_file.filename
        video_file.save(str(video_path))
        
        session['video_path'] = str(video_path)
        return jsonify({'success': True, 'filename': video_file.filename})
    except Exception as e:
        logging.error(f"Video upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def separate_vocals_demucs(audio_file, output_dir):
    """Separate vocals from audio using Demucs"""
    try:
        # Create output directory for stems
        stems_dir = Path(output_dir) / "stems"
        stems_dir.mkdir(parents=True, exist_ok=True)
        
        # Run demucs separation with better error handling - use high quality model
        cmd = [
            'python3', '-m', 'demucs.separate',
            '-n', 'htdemucs_ft',  # Use high quality DEMUCS v4 model
            '--two-stems', 'vocals',  # Only separate vocals vs instrumental
            '--out', str(stems_dir),
            '--mp3',  # Use MP3 format which is more reliable
            '--mp3-bitrate', '320',  # High quality
            str(audio_file)
        ]
        
        logging.info(f"Running Demucs command: {' '.join(cmd)}")
        
        # Start the process and log progress
        logging.info("Starting Demucs vocal separation process...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)  # Increase to 10 minute timeout
        
        if result.returncode != 0:
            logging.error(f"Demucs command failed with return code {result.returncode}")
            logging.error(f"Demucs stderr: {result.stderr}")
            logging.error(f"Demucs stdout: {result.stdout}")
            return None
        
        # Find the generated instrumental file
        audio_name = Path(audio_file).stem
        
        # Try multiple possible paths - htdemucs_ft first since we're using the high quality model
        possible_paths = [
            stems_dir / "htdemucs_ft" / audio_name / "no_vocals.mp3",
            stems_dir / "htdemucs_ft" / audio_name / "no_vocals.wav",
            stems_dir / "htdemucs" / audio_name / "no_vocals.mp3",  # Fallback
            stems_dir / "htdemucs" / audio_name / "no_vocals.wav",  # Fallback
            stems_dir / "mdx_extra" / audio_name / "no_vocals.mp3",
            stems_dir / "mdx_extra" / audio_name / "no_vocals.wav"
        ]
        
        for instrumental_file in possible_paths:
            if instrumental_file.exists():
                logging.info(f"Found instrumental file: {instrumental_file}")
                return str(instrumental_file)
        
        # If no standard file found, list what was actually created
        logging.error(f"Instrumental file not found. Contents of stems directory:")
        for root, dirs, files in os.walk(stems_dir):
            for file in files:
                file_path = os.path.join(root, file)
                logging.error(f"  Found: {file_path}")
        
        return None
            
    except subprocess.TimeoutExpired:
        logging.error("Demucs process timed out after 10 minutes")
        return None
    except Exception as e:
        logging.error(f"Error in vocal separation: {str(e)}")
        return None

def separate_vocals_replicate(audio_file, output_dir, model_config):
    """Separate vocals using Replicate API with timeout handling"""
    try:
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Import replicate (lazy import to avoid issues if not installed)
        try:
            import replicate
            import time
            import threading
        except ImportError as e:
            logging.error(f"replicate not installed: {e}")
            logging.error("Falling back to DEMUCS v4 for vocal separation")
            return separate_vocals_demucs(audio_file, output_dir)
        
        # Check for Replicate API token
        api_token = os.environ.get('REPLICATE_API_TOKEN')
        if not api_token:
            logging.error("REPLICATE_API_TOKEN not set")
            logging.error("Falling back to DEMUCS v4 for vocal separation")
            return separate_vocals_demucs(audio_file, output_dir)
        
        logging.info(f"Starting Replicate vocal separation with {model_config['model_name']}...")
        
        # Start prediction with timeout handling
        prediction = None
        output = None
        
        try:
            # Use the correct Replicate API format with direct file upload
            import replicate
            
            logging.info(f"Starting Replicate vocal separation with model: {model_config['model_name']}")
            
            # Call Replicate API with direct file upload
            with open(audio_file, 'rb') as f:
                output = replicate.run(
                    "erickluis00/all-in-one-audio:f2a8516c9084ef460592deaa397acd4a97f60f18c3d15d273644c72500cdff0e",
                    input={
                        "model": model_config['params'].get('model', 'harmonix-all'),
                        "sonify": False,
                        "visualize": False,
                        "music_input": f,
                        "audioSeparator": True,
                        "include_embeddings": False,
                        "audioSeparatorModel": model_config['params'].get('audioSeparatorModel', 'Kim_Vocal_2.onnx'),
                        "include_activations": False
                    }
                )
            
            logging.info(f"Replicate API call completed successfully")
            logging.info(f"Output type: {type(output)}")
            logging.info(f"Output: {output}")
            
        except Exception as e:
            logging.error(f"Replicate API error: {str(e)}")
            return None
        
        if not output:
            logging.error("Replicate API returned no output")
            return None
        
        # Handle the Replicate output - it should be a list of URLs
        instrumental_url = None
        logging.info(f"Replicate output: {output}")
        
        # The all-in-one-audio model returns a list of URLs
        if isinstance(output, list):
            for url in output:
                logging.info(f"Checking URL: {url}")
                if "mdx_instrumental" in url.lower():
                    instrumental_url = url
                    logging.info(f"Found mdx_instrumental URL: {instrumental_url}")
                    break
                elif "instrumental" in url.lower() or "no_vocals" in url.lower():
                    instrumental_url = url
                    logging.info(f"Found instrumental URL: {instrumental_url}")
                    break
        elif isinstance(output, dict):
            # Handle case where output might be a dictionary
            logging.info(f"Output is dictionary: {output}")
            if "instrumental" in output:
                instrumental_url = output["instrumental"]
            elif "mdx_instrumental" in output:
                instrumental_url = output["mdx_instrumental"]
        
        if not instrumental_url:
            logging.error("No instrumental file found in Replicate output")
            logging.error(f"Available URLs: {output}")
            return None
        
        # Download the file
        import requests
        response = requests.get(instrumental_url)
        if response.status_code != 200:
            logging.error(f"Failed to download instrumental file: {response.status_code}")
            return None
        
        # Save to output directory
        audio_name = Path(audio_file).stem
        instrumental_path = output_path / f"{audio_name}_instrumental_replicate.mp3"
        
        with open(instrumental_path, "wb") as f:
            f.write(response.content)
        
        logging.info(f"Downloaded instrumental file: {instrumental_path}")
        return str(instrumental_path)
        
    except Exception as e:
        logging.error(f"Error in Replicate vocal separation: {str(e)}")
        return None

def separate_vocals_with_model(audio_file, output_dir, model_id="uvr_mdx"):
    """Separate vocals using the specified model"""
    try:
        # Validate model ID
        if not validate_model_id(model_id):
            logging.error(f"Invalid model ID: {model_id}")
            return None
        
        # Get model configuration
        model_config = get_model_config(model_id)
        if not model_config:
            logging.error(f"Could not get configuration for model: {model_id}")
            return None
        
        logging.info(f"Using model: {model_config['name']} ({model_config['description']})")
        
        # Route to appropriate engine
        if model_config["engine"] == "demucs":
            return separate_vocals_demucs_model(audio_file, output_dir, model_config)
        elif model_config["engine"] == "replicate":
            result = separate_vocals_replicate(audio_file, output_dir, model_config)
            if result is None:
                logging.warning(f"Replicate API failed for {model_id}, trying fallback to DEMUCS v4")
                # If Replicate fails, fall back to high-quality DEMUCS v4
                return separate_vocals_demucs(audio_file, output_dir)
            return result
        else:
            logging.error(f"Unknown engine: {model_config['engine']}")
            return None
            
    except Exception as e:
        logging.error(f"Error in vocal separation with model {model_id}: {str(e)}")
        return None

def separate_vocals_demucs_model(audio_file, output_dir, model_config):
    """Separate vocals using DEMUCS with specified model configuration"""
    try:
        # Create output directory for stems
        stems_dir = Path(output_dir) / "stems"
        stems_dir.mkdir(parents=True, exist_ok=True)
        
        # Build command based on model configuration
        cmd = ['python3', '-m', 'demucs.separate']
        
        # Add model name
        cmd.extend(['-n', model_config["model_name"]])
        
        # Add parameters from config
        params = model_config.get("params", {})
        for key, value in params.items():
            if isinstance(value, bool) and value:
                cmd.append(key)
            elif not isinstance(value, bool):
                cmd.extend([key, str(value)])
        
        # Add output directory and input file
        cmd.extend(['--out', str(stems_dir), str(audio_file)])
        
        logging.info(f"Running DEMUCS command: {' '.join(cmd)}")
        
        # Start the process with better logging
        logging.info(f"Starting DEMUCS process with timeout of 300 seconds...")
        logging.info(f"Input file: {audio_file}")
        logging.info(f"Output directory: {stems_dir}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                logging.error(f"DEMUCS command failed with return code {result.returncode}")
                logging.error(f"DEMUCS stderr: {result.stderr}")
                logging.error(f"DEMUCS stdout: {result.stdout}")
                return None
            else:
                logging.info("DEMUCS process completed successfully")
                
        except subprocess.TimeoutExpired:
            logging.error("DEMUCS process timed out after 300 seconds")
            return None
        except Exception as e:
            logging.error(f"DEMUCS process failed with exception: {str(e)}")
            return None
        
        # Find the generated instrumental file
        audio_name = Path(audio_file).stem
        model_name = model_config["model_name"]
        
        # Try multiple possible paths based on the model
        possible_paths = [
            stems_dir / model_name / audio_name / "no_vocals.mp3",
            stems_dir / model_name / audio_name / "no_vocals.wav",
            stems_dir / "htdemucs" / audio_name / "no_vocals.mp3",
            stems_dir / "htdemucs" / audio_name / "no_vocals.wav"
        ]
        
        for instrumental_file in possible_paths:
            if instrumental_file.exists():
                logging.info(f"Found instrumental file: {instrumental_file}")
                return str(instrumental_file)
        
        # If no standard file found, list what was actually created
        logging.error(f"Instrumental file not found. Contents of stems directory:")
        for root, dirs, files in os.walk(stems_dir):
            for file in files:
                file_path = os.path.join(root, file)
                logging.error(f"  Found: {file_path}")
        
        return None
            
    except subprocess.TimeoutExpired:
        logging.error("DEMUCS process timed out after 10 minutes")
        return None
    except Exception as e:
        logging.error(f"Error in DEMUCS vocal separation: {str(e)}")
        return None

def remove_vocals_from_video(video_path, output_directory, model_id=None):
    """Complete workflow to remove vocals from video and return instrumental version"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Extract audio from video
        temp_audio_path = Path(output_directory) / f"temp_audio_{timestamp}.wav"
        if not extract_audio_from_video(video_path, temp_audio_path):
            return None
        
        # Use specified model or default
        if model_id is None:
            model_id = get_default_model()
        
        # Separate vocals using the specified model
        instrumental_path = separate_vocals_with_model(temp_audio_path, output_directory, model_id)
        
        if not instrumental_path:
            return None
        
        # Create video with instrumental audio
        instrumental_video_path = Path(output_directory) / f"instrumental_video_{timestamp}.mp4"
        
        video = ffmpeg.input(str(video_path))
        audio = ffmpeg.input(str(instrumental_path))
        
        ffmpeg.output(
            video.video,
            audio,
            str(instrumental_video_path),
            acodec='aac',
            vcodec='copy'
        ).overwrite_output().run(capture_stdout=True, capture_stderr=True)
        
        # Clean up temporary audio
        try:
            os.remove(temp_audio_path)
        except:
            pass
        
        return str(instrumental_video_path)
        
    except Exception as e:
        logging.error(f"Error removing vocals from video: {str(e)}")
        return None

def remove_vocals():
    try:
        # Debug logging
        logging.info("=== VOCAL REMOVAL FUNCTION CALLED ===")
        logging.info(f"Session ID: {session.get('session_id')}")
        logging.info(f"Video path: {session.get('video_path')}")
        logging.info(f"Transcription video path: {session.get('transcription_video_path')}")
        
        # Get model selection from request data (if any)
        data = request.get_json() if request.is_json else {}
        model_id = data.get('model_id') if data else None
        
        # Validate model if provided
        if model_id and not validate_model_id(model_id):
            logging.error(f"Invalid model ID provided: {model_id}")
            return jsonify({'error': f'Invalid vocal removal model: {model_id}'}), 400
        
        # Use default model if none specified
        if not model_id:
            model_id = get_default_model()
        
        logging.info(f"Using vocal removal model: {model_id}")
        
        # Get video path from session (try multiple possible keys)
        video_path = (session.get('video_path') or 
                     session.get('transcription_video_path') or 
                     session.get('uploaded_video_path'))
        
        # Debug logging to see what's in the session
        logging.info(f"Session keys: {list(session.keys())}")
        logging.info(f"video_path: {session.get('video_path')}")
        logging.info(f"transcription_video_path: {session.get('transcription_video_path')}")
        logging.info(f"uploaded_video_path: {session.get('uploaded_video_path')}")
        
        if not video_path:
            logging.error("No video path found in session")
            return jsonify({'error': 'No video available for vocal removal. Please upload a video first.'}), 400
        
        if not os.path.exists(video_path):
            logging.error(f"Video file not found at path: {video_path}")
            return jsonify({'error': 'Video file not found'}), 404
        
        # Create session-specific directories
        session_id = session.get('session_id', str(uuid.uuid4()))
        session['session_id'] = session_id
        
        base_dir = Path(f"temp_files/{session_id}")
        vocal_removal_dir = base_dir / "vocal_removal"
        vocal_removal_dir.mkdir(parents=True, exist_ok=True)
        
        # Get model info for response
        model_config = get_model_config(model_id)
        model_name = model_config['name'] if model_config else model_id
        
        # Remove vocals and create instrumental version
        logging.info(f"Starting vocal removal for video: {video_path} using model: {model_name}")
        instrumental_video_path = remove_vocals_from_video(video_path, str(vocal_removal_dir), model_id)
        
        if instrumental_video_path:
            logging.info(f"Vocal removal successful! Instrumental video created: {instrumental_video_path}")
            session['instrumental_video_path'] = instrumental_video_path
            return jsonify({
                'success': True,
                'message': f'Vocals removed successfully using {model_name}',
                'instrumental_video_path': instrumental_video_path,
                'model_used': model_name,
                'model_id': model_id
            })
        else:
            logging.error("Vocal removal failed - no instrumental video path returned")
            return jsonify({'error': 'Failed to remove vocals. Please ensure Demucs is installed and try again.'}), 500
        
    except Exception as e:
        logging.error(f"Vocal removal error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def mix_audio():
    try:
        data = request.get_json()
        original_volume = data.get('original_volume', 0.8)
        voiceover_volume = data.get('voiceover_volume', 1.3)
        use_vocal_removal = data.get('use_vocal_removal', False)
        
        audio_files = session.get('audio_files', {})
        video_path = session.get('video_path')
        
        if not audio_files or not video_path:
            return jsonify({'error': 'Audio files and video path are required'}), 400
        
        # Use instrumental video if vocal removal was requested and is available
        if use_vocal_removal:
            instrumental_video_path = session.get('instrumental_video_path')
            if instrumental_video_path and os.path.exists(instrumental_video_path):
                video_path = instrumental_video_path
            else:
                return jsonify({'error': 'Instrumental video not available. Please run vocal removal first.'}), 400
        
        # Create export directory
        session_id = session.get('session_id')
        base_dir = Path(f"temp_files/{session_id}")
        export_dir = base_dir / "export"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        mixed_videos = {}
        video_filename = Path(video_path).name
        
        for lang_code, audio_file in audio_files.items():
            suffix = "_instrumental" if use_vocal_removal else ""
            output_file = export_dir / f"{video_filename.split('.')[0]}_{lang_code}{suffix}.mp4"
            if mix_audio_with_video(audio_file, video_path, str(output_file), original_volume, voiceover_volume, use_vocal_removal):
                mixed_videos[lang_code] = str(output_file)
        
        session['mixed_videos'] = mixed_videos
        session['used_vocal_removal'] = use_vocal_removal
        return jsonify({'mixed_videos': mixed_videos})
    except Exception as e:
        logging.error(f"Audio mixing error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def transcribe():
    try:
        # Accept both 'video' and 'audio' file parameters for backward compatibility and new functionality
        media_file = None
        if 'video' in request.files:
            media_file = request.files['video']
        elif 'audio' in request.files:
            media_file = request.files['audio']
        elif 'file' in request.files:
            media_file = request.files['file']
        
        if not media_file:
            return jsonify({'error': 'No media file provided. Please upload a video or audio file.'}), 400
        
        if media_file.filename == '':
            return jsonify({'error': 'No media file selected'}), 400
        
        # Determine file type based on extension
        file_extension = media_file.filename.lower().split('.')[-1]
        video_extensions = {'mp4', 'mov', 'avi', 'mkv', 'webm', 'flv', 'm4v'}
        audio_extensions = {'mp3', 'wav', 'm4a', 'aac', 'ogg', 'flac', 'wma'}
        
        is_video = file_extension in video_extensions
        is_audio = file_extension in audio_extensions
        
        if not (is_video or is_audio):
            return jsonify({'error': f'Unsupported file format: .{file_extension}. Please upload a video file (mp4, mov, avi, mkv, webm, flv, m4v) or audio file (mp3, wav, m4a, aac, ogg, flac, wma).'}), 400
        
        # Create session-specific directories
        session_id = session.get('session_id', str(uuid.uuid4()))
        session['session_id'] = session_id
        
        base_dir = Path(f"temp_files/{session_id}")
        transcription_dir = base_dir / "transcription"
        transcription_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Check if OpenAI client is available
        if not openai_client:
            return jsonify({'error': 'OpenAI API key not configured. Please set OPENAI_API_KEY environment variable.'}), 500
        
        # Check file size (limit to 100MB for practical upload limits)
        file_size_mb = len(media_file.read()) / (1024 * 1024)
        media_file.seek(0)  # Reset file pointer
        
        if file_size_mb > 100:
            return jsonify({
                'error': f'File size ({file_size_mb:.1f}MB) exceeds 100MB limit. Please use a smaller file.'
            }), 400
        
        transcription = None
        video_available_for_vocal_removal = False
        
        if is_video:
            # Handle video files (existing workflow)
            temp_video_path = transcription_dir / f"transcription_video_{timestamp}_{media_file.filename}"
            media_file.save(str(temp_video_path))
            
            # Store the transcription video path for later use
            session['transcription_video_path'] = str(temp_video_path)
            video_available_for_vocal_removal = True
            
            # Transcribe video (extracts audio first)
            transcription = transcribe_video(temp_video_path)
            
        elif is_audio:
            # Handle audio files directly
            temp_audio_path = transcription_dir / f"transcription_audio_{timestamp}_{media_file.filename}"
            media_file.save(str(temp_audio_path))
            
            # Store the transcription audio path for reference
            session['transcription_audio_path'] = str(temp_audio_path)
            
            # Transcribe audio directly
            transcription = transcribe_audio(temp_audio_path)
        
        if transcription:
            return jsonify({
                'transcription': transcription,
                'video_available_for_vocal_removal': video_available_for_vocal_removal,
                'file_type': 'video' if is_video else 'audio'
            })
        else:
            file_type = 'video' if is_video else 'audio'
            return jsonify({'error': f'Failed to transcribe {file_type}. Please check your OpenAI API key and try again.'}), 500
    except Exception as e:
        logging.error(f"Transcription error: {str(e)}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

def download_adlocalizer_file(filename):
    try:
        session_id = session.get('session_id')
        if not session_id:
            return jsonify({'error': 'No session found'}), 404
        
        file_path = Path(f"temp_files/{session_id}/export/{filename}")
        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(str(file_path), as_attachment=True)
    except Exception as e:
        logging.error(f"Download error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def serve_audio(filepath):
    """Serve audio files for preview"""
    try:
        session_id = session.get('session_id')
        if not session_id:
            return jsonify({'error': 'No session found'}), 404
        
        # Remove any directory traversal attempts
        safe_path = Path(filepath).name
        file_path = Path(f"temp_files/{session_id}/audio/{safe_path}")
        
        if not file_path.exists():
            return jsonify({'error': 'Audio file not found'}), 404
        
        return send_file(str(file_path), mimetype='audio/mpeg')
    except Exception as e:
        logging.error(f"Audio serve error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def serve_video(filepath):
    """Serve video files for preview"""
    try:
        session_id = session.get('session_id')
        if not session_id:
            return jsonify({'error': 'No session found'}), 404
        
        # Remove any directory traversal attempts
        safe_path = Path(filepath).name
        file_path = Path(f"temp_files/{session_id}/export/{safe_path}")
        
        if not file_path.exists():
            return jsonify({'error': 'Video file not found'}), 404
        
        return send_file(str(file_path), mimetype='video/mp4')
    except Exception as e:
        logging.error(f"Video serve error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def download_all_adlocalizer():
    try:
        session_id = session.get('session_id')
        if not session_id:
            return jsonify({'error': 'No session found'}), 404
        
        mixed_videos = session.get('mixed_videos', {})
        if not mixed_videos:
            return jsonify({'error': 'No videos to download'}), 404
        
        # Create zip file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for lang_code, video_path in mixed_videos.items():
                if os.path.exists(video_path):
                    zip_file.write(video_path, os.path.basename(video_path))
        
        zip_buffer.seek(0)
        
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name='localized_videos.zip'
        )
    except Exception as e:
        logging.error(f"Download all error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Create necessary directories for AdLocalizer
Path("temp_files").mkdir(exist_ok=True)
Path("temp_transcription").mkdir(exist_ok=True) 