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
import time
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

# Load environment variables (for local development)
load_dotenv()

# Configure logging for console output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),  # This ensures output goes to console
    ]
)

# Debug environment variables on startup
logging.info("🔧 Environment Variable Debug Info:")
logging.info(f"   - NODE_ENV: {os.getenv('NODE_ENV', 'Not set')}")
logging.info(f"   - RENDER: {os.getenv('RENDER', 'Not set')}")
logging.info(f"   - PYTHON_VERSION: {os.getenv('PYTHON_VERSION', 'Not set')}")
logging.info(f"   - Environment type: {'Production' if os.getenv('RENDER') else 'Local'}")

# List all environment variables that start with common prefixes (for debugging)
env_vars = dict(os.environ)
relevant_vars = []
for key in env_vars.keys():
    if any(prefix in key.upper() for prefix in ['OPENAI', 'ELEVEN', 'API', 'KEY', 'SECRET', 'TOKEN']):
        # Don't show the actual values for security
        relevant_vars.append(key)

if relevant_vars:
    logging.info(f"🔍 Found {len(relevant_vars)} potentially relevant environment variables:")
    for var in sorted(relevant_vars):
        logging.info(f"   - {var}: {'✅ Set' if os.getenv(var) else '❌ Empty'}")
else:
    logging.warning("⚠️  No API-related environment variables found")
    logging.info(f"📊 Total environment variables available: {len(env_vars)}")

# Get API keys for AdLocalizer
def get_secret(key):
    """Get secret from environment variable with enhanced debugging"""
    value = os.getenv(key)
    
    # Enhanced debugging for Render.com
    if not value:
        logging.warning(f"❌ Missing API Key: {key}")
        
        # Check if we're on Render.com
        if os.getenv('RENDER'):
            logging.warning(f"   🚨 Running on Render.com but {key} not found!")
            logging.warning(f"   💡 Please check your Render.com environment variables:")
            logging.warning(f"      1. Go to your Render.com dashboard")
            logging.warning(f"      2. Select your service")
            logging.warning(f"      3. Go to Environment tab")
            logging.warning(f"      4. Verify {key} is set correctly")
        else:
            logging.warning(f"   💡 Running locally - check your .env file or set {key} directly")
        
        logging.warning(f"   - AdLocalizer features will not work without {key}")
        return None
    else:
        # Mask the key for security (show first 8 characters)
        masked_key = value[:8] + "*" * (len(value) - 8) if len(value) > 8 else "*" * len(value)
        logging.info(f"✅ Found API Key: {key} = {masked_key}")
        return value

# Initialize API clients (only if keys are available)
openai_client = None
eleven_labs_client = None

logging.info("🚀 Initializing API clients...")

try:
    openai_api_key = get_secret("OPENAI_API_KEY")
    elevenlabs_api_key = get_secret("ELEVENLABS_API_KEY")
    
    if openai_api_key:
        logging.info("🤖 Initializing OpenAI client...")
        openai_client = OpenAI(api_key=openai_api_key)
        logging.info("✅ OpenAI client initialized successfully")
    else:
        logging.warning("⚠️  OpenAI client not initialized - missing API key")
        
    if elevenlabs_api_key:
        logging.info("🎙️  Initializing ElevenLabs client...")
        from elevenlabs.client import ElevenLabs
        eleven_labs_client = ElevenLabs(api_key=elevenlabs_api_key)
        logging.info("✅ ElevenLabs client initialized successfully")
    else:
        logging.warning("⚠️  ElevenLabs client not initialized - missing API key")
        
except Exception as e:
    logging.error(f"❌ Error initializing API clients: {e}")
    import traceback
    logging.error(f"🔍 Traceback: {traceback.format_exc()}")

# Summary of initialization
logging.info("📊 API Client Initialization Summary:")
logging.info(f"   - OpenAI client: {'✅ Ready' if openai_client else '❌ Not available'}")
logging.info(f"   - ElevenLabs client: {'✅ Ready' if eleven_labs_client else '❌ Not available'}")

if not openai_client and not eleven_labs_client:
    logging.warning("⚠️  NO API CLIENTS INITIALIZED - AdLocalizer features will be disabled")
elif openai_client and eleven_labs_client:
    logging.info("🎉 ALL API CLIENTS READY - Full AdLocalizer functionality available")
else:
    logging.info("⚡ PARTIAL API CLIENTS READY - Some AdLocalizer features available")

# Voice options for AdLocalizer
VOICES = {
    "1": {"name": "Tom Cruise", "id": "g60FwKJuhCJqbDCeuXjm"},
    "2": {"name": "Doja Cat", "id": "E1c1pVuZVvPrme6B9ryw"},
    "3": {"name": "Chris", "id": "iP95p4xoKVk53GoZ742B"}
}

# Import centralized language configuration
from language_config import (
    LANGUAGES, 
    get_legacy_language_dict, 
    get_language_name,
    get_iso_code_from_old,
    get_old_code_from_iso,
    validate_language_code
)

# For external API compatibility when needed
LEGACY_LANGUAGES = get_legacy_language_dict()

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
        # Get voice name
        voice_name = next((v["name"] for v in VOICES.values() if v["id"] == voice_id), "Unknown")
        voice_name = voice_name.replace(" ", "_")
        
        # Create a clean identifier from the text (max 30 chars)
        # First, split into words and take first few words
        words = text.split()
        identifier_words = []
        current_length = 0
        for word in words:
            if current_length + len(word) + 1 <= 30:  # +1 for underscore
                identifier_words.append(word)
                current_length += len(word) + 1
            else:
                break
        
        # Join words and clean the identifier
        text_identifier = "_".join(identifier_words)
        text_identifier = re.sub(r'[^a-zA-Z0-9]+', '_', text_identifier.strip())
        text_identifier = text_identifier.strip('_')
        
        # Create filename with text_identifier, voice_name, and language_code (with brackets)
        safe_name = f"{text_identifier}_{voice_name}_[{language_code}]"
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
        logging.info(f"🎵 Starting audio extraction from video: {Path(video_path).name}")
        logging.info(f"📂 Output audio path: {output_audio_path}")
        
        (
            ffmpeg
            .input(str(video_path))
            .output(str(output_audio_path), acodec='pcm_s16le', ac=1, ar='16000')
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        
        # Check if output file was created
        if Path(output_audio_path).exists():
            file_size = Path(output_audio_path).stat().st_size / (1024 * 1024)  # MB
            logging.info(f"✅ Audio extraction successful! Audio file size: {file_size:.2f} MB")
        else:
            logging.error("❌ Audio extraction failed - output file not created")
            return False
            
        return True
    except ffmpeg.Error as e:
        logging.error(f"❌ FFmpeg error during audio extraction: {e.stderr.decode() if e.stderr else str(e)}")
        return False
    except Exception as e:
        logging.error(f"❌ Error extracting audio: {str(e)}")
        return False

def transcribe_audio(audio_file_path):
    """Transcribe audio using OpenAI Whisper"""
    if not openai_client:
        logging.error("❌ OpenAI client not available for transcription")
        return None
        
    try:
        # Get file info
        file_size = Path(audio_file_path).stat().st_size / (1024 * 1024)  # MB
        logging.info(f"🎤 Starting audio transcription with OpenAI Whisper")
        logging.info(f"📁 Audio file: {Path(audio_file_path).name} ({file_size:.2f} MB)")
        logging.info(f"🤖 Using model: whisper-1")
        
        import time
        start_time = time.time()
        
        with open(audio_file_path, "rb") as audio_file:
            logging.info("📤 Sending audio to OpenAI Whisper API...")
            transcription = openai_client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-1",
                response_format="text",
                prompt="This is a marketing video or advertisement. Please transcribe accurately."
            )
        
        processing_time = time.time() - start_time
        transcription_length = len(transcription) if transcription else 0
        
        logging.info(f"✅ Transcription completed successfully!")
        logging.info(f"⏱️  Processing time: {processing_time:.2f} seconds")
        logging.info(f"📝 Transcription length: {transcription_length} characters")
        if transcription:
            preview = transcription[:100] + "..." if len(transcription) > 100 else transcription
            logging.info(f"📖 Preview: {preview}")
        
        return transcription
    except Exception as e:
        logging.error(f"❌ Error transcribing audio: {str(e)}")
        return None

def transcribe_video(video_file_path):
    """Complete transcription workflow for video file"""
    try:
        logging.info(f"🎬 Starting video transcription workflow")
        logging.info(f"📹 Input video: {Path(video_file_path).name}")
        
        # Get video file info
        video_size = Path(video_file_path).stat().st_size / (1024 * 1024)  # MB
        logging.info(f"📊 Video file size: {video_size:.2f} MB")
        
        import time
        workflow_start_time = time.time()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        temp_dir = Path("temp_transcription")
        temp_dir.mkdir(exist_ok=True)
        logging.info(f"📁 Created temp directory: {temp_dir}")
        
        temp_audio_path = temp_dir / f"temp_audio_{timestamp}.wav"
        
        # Step 1: Extract audio
        logging.info("🔄 Step 1/2: Extracting audio from video...")
        if not extract_audio_from_video(video_file_path, temp_audio_path):
            logging.error("❌ Audio extraction failed - aborting transcription")
            return None
        
        # Step 2: Transcribe audio
        logging.info("🔄 Step 2/2: Transcribing extracted audio...")
        transcription = transcribe_audio(temp_audio_path)
        
        # Clean up temporary files
        logging.info("🧹 Cleaning up temporary files...")
        try:
            if temp_audio_path.exists():
                os.remove(temp_audio_path)
                logging.info(f"🗑️  Removed temp audio file: {temp_audio_path.name}")
            
            if temp_dir.exists() and not any(temp_dir.iterdir()):
                temp_dir.rmdir()
                logging.info(f"🗑️  Removed empty temp directory")
        except Exception as e:
            logging.warning(f"⚠️  Error cleaning up temp files: {str(e)}")
        
        total_time = time.time() - workflow_start_time
        
        if transcription:
            logging.info(f"🎉 Video transcription completed successfully!")
            logging.info(f"⏱️  Total workflow time: {total_time:.2f} seconds")
        else:
            logging.error(f"❌ Video transcription failed after {total_time:.2f} seconds")
        
        return transcription
        
    except Exception as e:
        logging.error(f"❌ Error in transcribe_video function: {str(e)}")
        return None

def get_video_duration(video_file):
    """Get video duration in seconds"""
    try:
        probe = ffmpeg.probe(str(video_file))
        duration = float(probe['streams'][0]['duration'])
        return duration
    except Exception as e:
        logging.error(f"Error getting video duration: {str(e)}")
        return None



def mix_audio_with_video(audio_file, video_file, output_file, original_volume=0.8, voiceover_volume=1.3, use_instrumental=False, custom_music_file=None):
    """Mix audio with video using ffmpeg-python"""
    try:
        video = ffmpeg.input(str(video_file))
        audio = ffmpeg.input(str(audio_file)) if audio_file else None
        
        if custom_music_file:
            # Custom music mode: replace original audio entirely with custom music + voiceover
            # Get video duration to match music duration
            video_duration = get_video_duration(video_file)
            if video_duration is None:
                logging.error("Could not determine video duration, using original music duration")
                custom_music = ffmpeg.input(str(custom_music_file))
            else:
                # Process custom music to match video duration
                custom_music = ffmpeg.input(str(custom_music_file))
                
                # Get music duration
                try:
                    music_probe = ffmpeg.probe(str(custom_music_file))
                    music_duration = float(music_probe['streams'][0]['duration'])
                    
                    if music_duration < video_duration:
                        # Music is shorter than video - loop it
                        loops_needed = int(video_duration / music_duration) + 1
                        custom_music = ffmpeg.filter(custom_music, 'aloop', loop=loops_needed-1, size=2**31-1)
                        # Trim to exact video duration
                        custom_music = ffmpeg.filter(custom_music, 'atrim', duration=video_duration)
                    elif music_duration > video_duration:
                        # Music is longer than video - trim it
                        custom_music = ffmpeg.filter(custom_music, 'atrim', duration=video_duration)
                    # If durations match, use as-is
                    
                except Exception as e:
                    logging.warning(f"Could not process music duration, using original: {str(e)}")
                    custom_music = ffmpeg.input(str(custom_music_file))
            
            # Mix custom music with voiceover, ensuring final duration matches video
            if audio_file and Path(audio_file).exists() and audio:
                # Mix custom music with voiceover - music should play for full video duration
                mixed_audio = ffmpeg.filter([
                    ffmpeg.filter(custom_music, 'volume', original_volume),
                    ffmpeg.filter(audio, 'volume', voiceover_volume)
                ], 'amix', inputs=2, duration='first')  # Use 'first' to preserve music duration
            else:
                # No voiceover - just use custom music at specified volume
                mixed_audio = ffmpeg.filter(custom_music, 'volume', original_volume)
            
        else:
            # Original mode: mix voiceover with original/instrumental video audio
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
            # Support both old and new language codes
            if validate_language_code(lang_code):
                lang_name = get_language_name(lang_code)
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
        
        # Get file size info
        original_size_mb = video_path.stat().st_size / (1024 * 1024)
        logging.info(f"📹 Video uploaded: {video_file.filename} ({original_size_mb:.2f} MB)")
        
        session['video_path'] = str(video_path)
        return jsonify({
            'success': True, 
            'filename': video_file.filename,
            'size_mb': round(original_size_mb, 2)
        })
    except Exception as e:
        logging.error(f"Video upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def upload_custom_music():
    try:
        use_default = request.form.get('use_default', 'false').lower() == 'true'
        
        # Create session-specific directories
        session_id = session.get('session_id', str(uuid.uuid4()))
        session['session_id'] = session_id
        
        base_dir = Path(f"temp_files/{session_id}")
        music_dir = base_dir / "custom_music"
        music_dir.mkdir(parents=True, exist_ok=True)
        
        if use_default:
            # Get the selected default music file
            selected_music = request.form.get('default_music_file', 'rapbeatL.mp3')
            default_music_path = Path("static/music") / selected_music
            
            if not default_music_path.exists():
                return jsonify({'error': f'Default music file not found: {selected_music}'}), 404
            
            # Copy default music to session directory
            import shutil
            custom_music_path = music_dir / selected_music
            shutil.copy2(str(default_music_path), str(custom_music_path))
            
            session['custom_music_path'] = str(custom_music_path)
            session['custom_music_name'] = selected_music.split('.')[0]  # Store name without extension
            return jsonify({'success': True, 'filename': f'{selected_music} (default)', 'is_default': True})
        
        else:
            # Handle uploaded music file
            if 'music' not in request.files:
                return jsonify({'error': 'No music file provided'}), 400
            
            music_file = request.files['music']
            if music_file.filename == '':
                return jsonify({'error': 'No music file selected'}), 400
            
            # Validate file type
            file_extension = music_file.filename.lower().split('.')[-1]
            audio_extensions = {'mp3', 'wav', 'm4a', 'aac', 'ogg', 'flac', 'wma'}
            
            if file_extension not in audio_extensions:
                return jsonify({'error': f'Unsupported audio format: .{file_extension}. Please upload: {", ".join(audio_extensions)}'}), 400
            
            # Save music file
            custom_music_path = music_dir / music_file.filename
            music_file.save(str(custom_music_path))
            
            session['custom_music_path'] = str(custom_music_path)
            session['custom_music_name'] = music_file.filename.split('.')[0]  # Store name without extension
            return jsonify({'success': True, 'filename': music_file.filename, 'is_default': False})
    
    except Exception as e:
        logging.error(f"Custom music upload error: {str(e)}")
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
    """Handle vocal removal request - FEATURE DISABLED"""
    try:
        logging.warning("=== VOCAL REMOVAL FUNCTION CALLED BUT FEATURE IS DISABLED ===")
        
        # Return error message indicating feature is disabled
        return jsonify({
            'error': 'Vocal removal feature is currently disabled',
            'message': 'AI vocal removal has been temporarily disabled to reduce deployment size. The required dependencies (PyTorch, DEMUCS, etc.) have been removed.',
            'suggestion': 'Please use Option A (SFX-only video) or Option B (custom music) instead.',
            'success': False
        }), 503  # Service Unavailable
        
    except Exception as e:
        logging.error(f"Vocal removal disabled - error in handler: {str(e)}")
        return jsonify({
            'error': 'Vocal removal feature is disabled',
            'message': 'This feature has been temporarily disabled to reduce deployment size.',
            'success': False
        }), 503

def mix_audio():
    try:
        data = request.get_json()
        original_volume = data.get('original_volume', 0.8)
        voiceover_volume = data.get('voiceover_volume', 1.3)
        use_vocal_removal = data.get('use_vocal_removal', False)
        use_custom_music = data.get('use_custom_music', False)
        
        audio_files = session.get('audio_files', {})
        video_path = session.get('video_path')
        
        # For custom music, we don't need audio files - we can just replace the video's audio
        if use_custom_music:
            if not video_path:
                return jsonify({'error': 'Video path is required'}), 400
        else:
            if not audio_files or not video_path:
                return jsonify({'error': 'Audio files and video path are required'}), 400
        
        # Handle custom music option
        custom_music_path = None
        if use_custom_music:
            custom_music_path = session.get('custom_music_path')
            if not custom_music_path or not os.path.exists(custom_music_path):
                return jsonify({'error': 'Custom music not available. Please upload a music file first.'}), 400
        
        # Use instrumental video if vocal removal was requested and is available (not used with custom music)
        elif use_vocal_removal:
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
        
        # Handle custom music without voiceovers
        if use_custom_music and not audio_files:
            # Create a single output with just custom music (no voiceover)
            music_name = session.get('custom_music_name', 'custom_music')
            
            # Apply the same naming logic for consistency
            base_name = video_filename.split('.')[0]
            if base_name.upper().endswith('_EN'):
                # Replace _EN with music suffix for custom music files
                base_name = re.sub(r'_EN$', '', base_name, flags=re.IGNORECASE)
            
            # Format music name as music-{name}
            suffix = f"_music-{music_name}"
            output_file = export_dir / f"{base_name}{suffix}.mp4"
            # Use None as audio_file to indicate no voiceover
            if mix_audio_with_video(None, video_path, str(output_file), original_volume, voiceover_volume, use_vocal_removal, custom_music_path):
                mixed_videos['custom_music'] = str(output_file)
        else:
            # Normal case: loop through audio files (voiceovers)
            for lang_code, audio_file in audio_files.items():
                # Create output filename with smart language code replacement
                base_name = video_filename.split('.')[0]
                
                # Check if the filename ends with _EN or [en] and replace it with the target language
                # Handle case variations and ensure clean replacement
                if base_name.upper().endswith('_EN'):
                    # Replace _EN with the target language code (with brackets)
                    base_name = re.sub(r'_EN$', f'_[{lang_code}]', base_name, flags=re.IGNORECASE)
                elif re.search(r'\[en\]$', base_name, re.IGNORECASE):
                    # Replace [en] with the target language code (with brackets)
                    base_name = re.sub(r'\[en\]$', f'[{lang_code}]', base_name, flags=re.IGNORECASE)
                else:
                    # If no _EN or [en] found, append the language code as before (with brackets)
                    base_name = f"{base_name}_[{lang_code}]"
                
                # Add appropriate suffix based on options
                if use_custom_music:
                    music_name = session.get('custom_music_name', 'custom_music')
                    # Format music name as music-{name} instead of _{name}
                    suffix = f"_music-{music_name}"
                elif use_vocal_removal:
                    suffix = "_instrumental"  
                else:
                    suffix = ""
                    
                output_file = export_dir / f"{base_name}{suffix}.mp4"
                if mix_audio_with_video(audio_file, video_path, str(output_file), original_volume, voiceover_volume, use_vocal_removal, custom_music_path):
                    mixed_videos[lang_code] = str(output_file)
        
        session['mixed_videos'] = mixed_videos
        session['used_vocal_removal'] = use_vocal_removal
        session['used_custom_music'] = use_custom_music
        return jsonify({'mixed_videos': mixed_videos})
    except Exception as e:
        logging.error(f"Audio mixing error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def transcribe():
    try:
        logging.info("=" * 60)
        logging.info("🚀 TRANSCRIPTION REQUEST RECEIVED")
        logging.info("=" * 60)
        
        # Accept both 'video' and 'audio' file parameters for backward compatibility and new functionality
        media_file = None
        file_param_used = None
        
        if 'video' in request.files:
            media_file = request.files['video']
            file_param_used = 'video'
        elif 'audio' in request.files:
            media_file = request.files['audio']
            file_param_used = 'audio'
        elif 'file' in request.files:
            media_file = request.files['file']
            file_param_used = 'file'
        
        logging.info(f"📋 File parameter used: {file_param_used}")
        
        if not media_file:
            logging.error("❌ No media file provided in request")
            return jsonify({'error': 'No media file provided. Please upload a video or audio file.'}), 400
        
        if media_file.filename == '':
            logging.error("❌ Empty filename provided")
            return jsonify({'error': 'No media file selected'}), 400
        
        logging.info(f"📄 Original filename: {media_file.filename}")
        
        # Determine file type based on extension
        file_extension = media_file.filename.lower().split('.')[-1]
        video_extensions = {'mp4', 'mov', 'avi', 'mkv', 'webm', 'flv', 'm4v'}
        audio_extensions = {'mp3', 'wav', 'm4a', 'aac', 'ogg', 'flac', 'wma'}
        
        is_video = file_extension in video_extensions
        is_audio = file_extension in audio_extensions
        
        logging.info(f"🏷️  File extension: .{file_extension}")
        logging.info(f"📹 Is video: {is_video}")
        logging.info(f"🎵 Is audio: {is_audio}")
        
        if not (is_video or is_audio):
            logging.error(f"❌ Unsupported file format: .{file_extension}")
            return jsonify({'error': f'Unsupported file format: .{file_extension}. Please upload a video file (mp4, mov, avi, mkv, webm, flv, m4v) or audio file (mp3, wav, m4a, aac, ogg, flac, wma).'}), 400
        
        # Create session-specific directories
        session_id = session.get('session_id', str(uuid.uuid4()))
        session['session_id'] = session_id
        logging.info(f"🔑 Session ID: {session_id}")
        
        base_dir = Path(f"temp_files/{session_id}")
        transcription_dir = base_dir / "transcription"
        transcription_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"📁 Created transcription directory: {transcription_dir}")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        logging.info(f"⏰ Timestamp: {timestamp}")
        
        # Check if OpenAI client is available
        if not openai_client:
            logging.error("❌ OpenAI client not initialized - API key missing")
            return jsonify({'error': 'OpenAI API key not configured. Please set OPENAI_API_KEY environment variable.'}), 500
        
        logging.info("✅ OpenAI client is available")
        
        # Check file size (limit to 100MB for practical upload limits)
        logging.info("📏 Checking file size...")
        file_size_mb = len(media_file.read()) / (1024 * 1024)
        media_file.seek(0)  # Reset file pointer
        logging.info(f"📊 File size: {file_size_mb:.2f} MB")
        
        if file_size_mb > 100:
            logging.error(f"❌ File size ({file_size_mb:.1f}MB) exceeds 100MB limit")
            return jsonify({
                'error': f'File size ({file_size_mb:.1f}MB) exceeds 100MB limit. Please use a smaller file.'
            }), 400
        
        logging.info("✅ File size check passed")
        
        transcription = None
        video_available_for_vocal_removal = False
        
        import time
        processing_start_time = time.time()
        
        if is_video:
            logging.info("🎬 Processing VIDEO file...")
            # Handle video files (existing workflow)
            temp_video_path = transcription_dir / f"transcription_video_{timestamp}_{media_file.filename}"
            logging.info(f"💾 Saving video to: {temp_video_path}")
            media_file.save(str(temp_video_path))
            
            # Verify file was saved
            if temp_video_path.exists():
                saved_size = temp_video_path.stat().st_size / (1024 * 1024)  # MB
                logging.info(f"✅ Video saved successfully ({saved_size:.2f} MB)")
            else:
                logging.error("❌ Failed to save video file")
                return jsonify({'error': 'Failed to save uploaded video file'}), 500
            
            # Store the transcription video path for later use
            session['transcription_video_path'] = str(temp_video_path)
            video_available_for_vocal_removal = True
            
            # Transcribe video (extracts audio first)
            logging.info("🎵 Starting video transcription workflow...")
            transcription = transcribe_video(str(temp_video_path))
            
        elif is_audio:
            logging.info("🎵 Processing AUDIO file...")
            # Handle audio files directly
            temp_audio_path = transcription_dir / f"transcription_audio_{timestamp}_{media_file.filename}"
            logging.info(f"💾 Saving audio to: {temp_audio_path}")
            media_file.save(str(temp_audio_path))
            
            # Verify file was saved
            if temp_audio_path.exists():
                saved_size = temp_audio_path.stat().st_size / (1024 * 1024)  # MB
                logging.info(f"✅ Audio saved successfully ({saved_size:.2f} MB)")
            else:
                logging.error("❌ Failed to save audio file")
                return jsonify({'error': 'Failed to save uploaded audio file'}), 500
            
            # Store the transcription audio path for reference
            session['transcription_audio_path'] = str(temp_audio_path)
            
            # Transcribe audio directly
            logging.info("🎤 Starting audio transcription...")
            transcription = transcribe_audio(temp_audio_path)
        
        total_processing_time = time.time() - processing_start_time
        
        if transcription:
            logging.info("=" * 60)
            logging.info("🎉 TRANSCRIPTION COMPLETED SUCCESSFULLY!")
            logging.info(f"⏱️  Total processing time: {total_processing_time:.2f} seconds")
            logging.info(f"📝 Transcription length: {len(transcription)} characters")
            logging.info(f"🔧 Vocal removal available: {video_available_for_vocal_removal}")
            logging.info(f"📄 File type processed: {'video' if is_video else 'audio'}")
            logging.info("=" * 60)
            
            return jsonify({
                'transcription': transcription,
                'video_available_for_vocal_removal': video_available_for_vocal_removal,
                'file_type': 'video' if is_video else 'audio'
            })
        else:
            file_type = 'video' if is_video else 'audio'
            logging.error("=" * 60)
            logging.error("❌ TRANSCRIPTION FAILED!")
            logging.error(f"⏱️  Total processing time: {total_processing_time:.2f} seconds")
            logging.error(f"📄 File type: {file_type}")
            logging.error(f"💾 File size: {file_size_mb:.2f} MB")
            logging.error("=" * 60)
            
            return jsonify({'error': f'Failed to transcribe {file_type}. Please check your OpenAI API key and try again.'}), 500
    except Exception as e:
        logging.error("=" * 60)
        logging.error("💥 TRANSCRIPTION ERROR - EXCEPTION OCCURRED!")
        logging.error(f"❌ Error: {str(e)}")
        logging.error("🔍 Full traceback:")
        import traceback
        logging.error(traceback.format_exc())
        logging.error("=" * 60)
        return jsonify({'error': str(e)}), 500

def download_adlocalizer_file(filename):
    try:
        session_id = session.get('session_id')
        if not session_id:
            return jsonify({'error': 'No session found'}), 404
        
        file_path = Path(f"temp_files/{session_id}/export/{filename}")
        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404
        
        # Get file size for optimization
        file_size = file_path.stat().st_size
        logging.info(f"Downloading file: {filename} ({file_size} bytes)")
        
        # For large files (>10MB), use streaming response
        if file_size > 10 * 1024 * 1024:  # 10MB
            return create_streaming_download_response(str(file_path), filename)
        else:
            # For smaller files, use optimized send_file with better headers
            return send_file(
                str(file_path), 
                as_attachment=True,
                download_name=filename,
                mimetype='video/mp4',
                conditional=True,  # Enable conditional requests (range support)
                etag=True,         # Enable ETag for caching
                last_modified=True, # Enable last-modified headers
                max_age=3600       # Cache for 1 hour
            )
    except Exception as e:
        logging.error(f"Download error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def create_streaming_download_response(file_path, filename):
    """Create optimized streaming response for large file downloads"""
    import os
    from flask import Response
    
    def generate_file_chunks():
        chunk_size = 1024 * 1024  # 1MB chunks for optimal download speed
        bytes_sent = 0
        file_size = os.path.getsize(file_path)
        
        try:
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
                    bytes_sent += len(chunk)
                    
                    # Log progress every 10MB
                    if bytes_sent % (10 * 1024 * 1024) == 0:
                        progress = (bytes_sent / file_size) * 100
                        logging.info(f"Download progress for {filename}: {progress:.1f}% ({bytes_sent}/{file_size} bytes)")
                        
        except Exception as e:
            logging.error(f"Error streaming file {filename}: {str(e)}")
            yield b''  # End the stream on error
    
    file_size = os.path.getsize(file_path)
    
    # Create response with optimized headers for maximum download speed
    response = Response(
        generate_file_chunks(),
        mimetype='video/mp4',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type': 'video/mp4',
            'Content-Length': str(file_size),
            'Accept-Ranges': 'bytes',
            'Cache-Control': 'public, max-age=3600',  # Cache for 1 hour
            'Connection': 'keep-alive',
            'Transfer-Encoding': 'chunked'
        }
    )
    
    return response

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
    """Serve video files for preview with optimized streaming"""
    try:
        session_id = session.get('session_id')
        if not session_id:
            return jsonify({'error': 'No session found'}), 404
        
        # Remove any directory traversal attempts
        safe_path = Path(filepath).name
        file_path = Path(f"temp_files/{session_id}/export/{safe_path}")
        
        if not file_path.exists():
            return jsonify({'error': 'Video file not found'}), 404
        
        # Get file size
        file_size = file_path.stat().st_size
        
        # Use optimized serving with range support for video streaming
        return send_file(
            str(file_path), 
            mimetype='video/mp4',
            conditional=True,    # Enable range requests for video seeking
            etag=True,          # Enable ETag for browser caching
            last_modified=True, # Enable last-modified headers
            max_age=1800        # Cache for 30 minutes
        )
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
        
        # Get valid files for ZIP
        valid_files = []
        for lang_code, video_path in mixed_videos.items():
            if os.path.exists(video_path):
                valid_files.append((video_path, os.path.basename(video_path)))
        
        if not valid_files:
            return jsonify({'error': 'No valid videos found'}), 404
        
        logging.info(f"Creating streaming ZIP with {len(valid_files)} localized videos")
        
        # Try fast ZIP creation first
        try:
            return create_fast_adlocalizer_zip(valid_files, 'localized_videos.zip')
        except Exception as e:
            logging.warning(f"Fast ZIP creation failed, falling back to streaming: {str(e)}")
            return create_adlocalizer_streaming_zip_response(valid_files, 'localized_videos.zip')
        
    except Exception as e:
        logging.error(f"Download all error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def download_all_voiceovers():
    try:
        session_id = session.get('session_id')
        if not session_id:
            return jsonify({'error': 'No session found'}), 404
        
        audio_files = session.get('audio_files', {})
        if not audio_files:
            return jsonify({'error': 'No voiceovers to download'}), 404
        
        # Get valid files for ZIP
        valid_files = []
        for lang_code, audio_path in audio_files.items():
            if os.path.exists(audio_path):
                valid_files.append((audio_path, os.path.basename(audio_path)))
        
        if not valid_files:
            return jsonify({'error': 'No valid voiceover files found'}), 404
        
        logging.info(f"Creating streaming ZIP with {len(valid_files)} voiceover files")
        
        # Try fast ZIP creation first
        try:
            return create_fast_adlocalizer_zip(valid_files, 'voiceovers.zip')
        except Exception as e:
            logging.warning(f"Fast ZIP creation failed, falling back to streaming: {str(e)}")
            return create_adlocalizer_streaming_zip_response(valid_files, 'voiceovers.zip')
        
    except Exception as e:
        logging.error(f"Download all voiceovers error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def create_adlocalizer_streaming_zip_response(files, zip_name):
    """Create a truly streaming ZIP response for AdLocalizer using temporary file to avoid memory issues"""
    import gc
    import tempfile
    from flask import Response
    
    def generate_zip():
        # Create a temporary file for the ZIP
        temp_zip_path = None
        files_added = 0
        
        try:
            # Create temporary file for ZIP
            temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            temp_zip_path = temp_zip.name
            temp_zip.close()
            
            logging.info(f"Creating AdLocalizer ZIP file at: {temp_zip_path}")
            zip_start_time = time.time()
            
            # Create ZIP file on disk (not in memory) - NO COMPRESSION for speed
            with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_STORED, compresslevel=0) as zipf:
                for file_path, archive_name in files:
                    try:
                        if not os.path.exists(file_path):
                            logging.warning(f"File does not exist: {file_path}")
                            continue
                            
                        file_start_time = time.time()
                        file_size = os.path.getsize(file_path)
                        logging.info(f"Adding file to AdLocalizer ZIP: {archive_name} ({file_size} bytes) from {file_path}")
                        
                        # Use zipfile's built-in method for better compatibility
                        zipf.write(file_path, arcname=archive_name)
                        files_added += 1
                        
                        file_time = time.time() - file_start_time
                        logging.info(f"Successfully added {archive_name} to AdLocalizer ZIP in {file_time:.2f} seconds")
                        
                    except Exception as e:
                        logging.error(f"Error adding {archive_name} to AdLocalizer ZIP: {str(e)}")
                        continue
            
            zip_creation_time = time.time() - zip_start_time
            logging.info(f"AdLocalizer ZIP creation completed. Files added: {files_added} in {zip_creation_time:.2f} seconds")
            
            if files_added == 0:
                logging.error("No files were added to AdLocalizer ZIP")
                yield b''  # Return empty data
                return
                
            # Check if ZIP file was created and has content
            if not os.path.exists(temp_zip_path):
                logging.error("AdLocalizer ZIP file was not created")
                yield b''
                return
                
            zip_size = os.path.getsize(temp_zip_path)
            logging.info(f"AdLocalizer ZIP file size: {zip_size} bytes")
            
            if zip_size == 0:
                logging.error("AdLocalizer ZIP file is empty")
                yield b''
                return
            
            # Stream the ZIP file back to client in larger chunks for better performance
            with open(temp_zip_path, 'rb') as zip_file:
                chunk_size = 1024 * 1024  # 1MB chunks for faster streaming on Render.com
                bytes_sent = 0
                while True:
                    chunk = zip_file.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
                    bytes_sent += len(chunk)
                
                logging.info(f"AdLocalizer ZIP streaming completed. Bytes sent: {bytes_sent}")
                
        except Exception as e:
            logging.error(f"Error creating AdLocalizer streaming ZIP: {str(e)}")
            yield b''  # Return empty data on error
        finally:
            # Cleanup temporary file
            try:
                if temp_zip_path and os.path.exists(temp_zip_path):
                    os.unlink(temp_zip_path)
                    logging.info("Cleaned up AdLocalizer temporary ZIP file")
            except Exception as e:
                logging.warning(f"Could not clean up AdLocalizer temp ZIP file: {str(e)}")
            
            # Force garbage collection
            gc.collect()
    
    # Create response with optimized headers for better download performance
    response = Response(
        generate_zip(),
        mimetype='application/zip',
        headers={
            'Content-Disposition': f'attachment; filename={zip_name}',
            'Content-Type': 'application/zip',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Transfer-Encoding': 'chunked'
        }
    )
    
    return response

def create_fast_adlocalizer_zip(files, zip_name):
    """Ultra-fast ZIP creation - creates ZIP in memory and sends directly"""
    import io
    from flask import Response
    
    logging.info(f"Creating FAST AdLocalizer ZIP with {len(files)} files")
    zip_start_time = time.time()
    
    # Create ZIP in memory buffer
    zip_buffer = io.BytesIO()
    
    try:
        files_added = 0
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_STORED, compresslevel=0) as zipf:
            for file_path, archive_name in files:
                try:
                    if not os.path.exists(file_path):
                        logging.warning(f"File does not exist: {file_path}")
                        continue
                        
                    file_size = os.path.getsize(file_path)
                    logging.info(f"Adding to FAST ZIP: {archive_name} ({file_size} bytes)")
                    
                    zipf.write(file_path, arcname=archive_name)
                    files_added += 1
                    
                except Exception as e:
                    logging.error(f"Error adding {archive_name} to FAST ZIP: {str(e)}")
                    continue
        
        zip_creation_time = time.time() - zip_start_time
        logging.info(f"FAST ZIP creation completed. Files added: {files_added} in {zip_creation_time:.2f} seconds")
        
        if files_added == 0:
            logging.error("No files were added to FAST ZIP")
            return jsonify({'error': 'No valid videos found'}), 404
        
        # Get ZIP data
        zip_buffer.seek(0)
        zip_data = zip_buffer.getvalue()
        zip_size = len(zip_data)
        
        logging.info(f"FAST ZIP size: {zip_size} bytes")
        
        # Create response with optimized headers for maximum download speed
        response = Response(
            zip_data,
            mimetype='application/zip',
            headers={
                'Content-Disposition': f'attachment; filename={zip_name}',
                'Content-Type': 'application/zip',
                'Content-Length': str(zip_size),
                'Cache-Control': 'no-cache, must-revalidate',
                'Connection': 'keep-alive',
                'Accept-Ranges': 'bytes'
            }
        )
        
        return response
        
    except Exception as e:
        logging.error(f"FAST ZIP creation failed: {str(e)}")
        raise
    finally:
        zip_buffer.close()

# Create necessary directories for AdLocalizer
Path("temp_files").mkdir(exist_ok=True)
Path("temp_transcription").mkdir(exist_ok=True) 