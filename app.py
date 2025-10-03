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
from datetime import datetime, timedelta
import concurrent.futures
import threading
import time
import argparse
from typing import Optional
from tools_config import get_active_tools
from youtube_upload import build_plan, FEATURE_ALIASES, LANGUAGE_CODES, LANGUAGE_MAP
from youtube_upload.runner import process_plans, write_results_csv
from youtube_upload.uploader import YoutubeUploadClient, CredentialSetupError
from auth import init_auth

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, continue without it

# OpenAI client for creative name correction
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Simple post-check normalizer for creative names
import re

DEFAULT_CREATORS = ["Jiali", "Houda", "Kaja"]

FEATURES = {"AIBG","IGSTORY","LOGO","ANIM","MIX","AIFILL","RETOUCH",
            "IMGT-CHANGE","IMGT-MODEL","IMGT-STAGE","IMGT-BEAUTIFY","RnD"}
DIMS = {"PO","SQ","LS"}


UPLOAD_PASSWORD = (
    os.environ.get('YOUTUBE_UPLOAD_PASSWORD')
    or os.environ.get('YOUTUBE_PLAYLIST_PASSWORD')
    or 'PhotoroomUA2025'
).strip()


def _check_upload_password(provided: Optional[str]) -> tuple[bool, dict[str, str]]:
    """Validate the shared password required for YouTube bulk uploads."""

    if not UPLOAD_PASSWORD:
        return True, {}

    if (provided or '').strip() == UPLOAD_PASSWORD:
        return True, {}

    app_logger.warning('Invalid password attempt for YouTube upload endpoint')
    return False, {
        'success': False,
        'error': 'Unauthorized: invalid password provided.'
    }



app = Flask(__name__)
try:
    _youtube_upload_max_mb = int(os.environ.get('YOUTUBE_UPLOAD_MAX_MB', '0'))
except (TypeError, ValueError):
    _youtube_upload_max_mb = 0

if _youtube_upload_max_mb and _youtube_upload_max_mb > 0:
    app.config['MAX_CONTENT_LENGTH'] = _youtube_upload_max_mb * 1024 * 1024
else:
    # Set to None to disable the upload size limit
    app.config['MAX_CONTENT_LENGTH'] = None
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_NAME'] = os.environ.get('SESSION_COOKIE_NAME', 'pr_session')

session_secure_flag = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() in {'1', 'true', 'yes', 'on'}
app.config['SESSION_COOKIE_SECURE'] = session_secure_flag

try:
    session_days = int(os.environ.get('SESSION_LIFETIME_DAYS', '7'))
except (TypeError, ValueError):
    session_days = 7
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=max(session_days, 1))

app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')
app.config['GOOGLE_REDIRECT_URI'] = os.environ.get('GOOGLE_REDIRECT_URI')
app.config['FRONTEND_URL'] = os.environ.get('FRONTEND_URL')
app.config['FRONTEND_APP_PATH'] = os.environ.get('FRONTEND_APP_PATH', '/app')
app.config['FRONTEND_LOGIN_PATH'] = os.environ.get('FRONTEND_LOGIN_PATH', '/login')
app.config['BACKEND_URL'] = os.environ.get('BACKEND_URL')

# Shared rules fed to the model (kept crisp + deterministic)
NAMING_RULES = """
You are a strict formatter for Photoroom AdManage creative names. You must output ONLY a single JSON object:
{"corrected":"<final_name>","reasoning":"<very short explanation>"}
No prose outside JSON. temperature=0.

ACCEPTED OUTPUTS
- AdManage (ID at start). With filename:
  [id]_[creator]_[creator-type]_[filename]_[HOOK-…]_[VO-…]_[MUSIC-…]_[DIM]_[feature]_[language][_date]
  (date only if a valid DDMMYYYY is present in input)
- AdManage (compressed, non-internal when filename is missing/ambiguous):
  [id]_[creator]_[{type}-{CreatorName[-num]}]_[HOOK-…]_[VO-…]_[MUSIC-…]_[DIM]_[feature]_[language][_date]
- Basic (no ID at start):
  [creator-type]_[filename]_[HOOK-…]_[VO-…]_[MUSIC-…]_[DIM]_[feature]_[language]

HARD RULES
- "_" separates main fields; "-" separates details inside tags.
- Creator types: internal | freelancer | ramdam | influencer.
  • If non-internal, creator-type can be "{type}-{CreatorName}" (CreatorName in PascalCase).
  • If creator is missing for AdManage, choose from {Jiali, Houda, Kaja} (prefer Jiali).
  • If creator-type is missing/unclear, default to "internal".
- Filename: PascalCase. If clearly missing/ambiguous, and creator-type is non-internal, use the compressed 9-part AdManage variant and OMIT filename.
- Tags (always 4, in this exact order): HOOK → VO → MUSIC → DIM
  • DIM ∈ {PO, SQ, LS} (uppercase; default PO)
  • If HOOK/VO/MUSIC missing → "any"
- Feature & language MUST be bracketed: _[FEATURE]_[lang]
  • FEATURE ∈ {AIBG, IGSTORY, LOGO, ANIM, MIX, AIFILL, RETOUCH, IMGT-CHANGE, IMGT-MODEL, IMGT-STAGE, IMGT-BEAUTIFY, RnD}
  • lang is ISO 639-1 (prefer lowercase; uppercase allowed but still wrapped)
- Date (AdManage only): include if a valid DDMMYYYY exists in input; otherwise omit.

ITERATION RULES (VERY IMPORTANT)
- Iteration tokens are recognized ONLY when they include a number, e.g., "ITE_2", "ITE-2".
  • Apply iteration on the filename as a suffix: <Filename>[-<baseNum>]-ITE-<iterNum>.
  • If a plain number appears adjacent to ITE (e.g., "... _1_ITE_2 ..."), treat that as a base variation and add "-1" before "-ITE-2".
  • If the filename already ends with "-<num>", keep it, then append "-ITE-<iterNum>".
- Lone "ITE" without a number MUST be ignored (do not treat as iteration; do not turn into [it]; do not place after language).

TOKEN NORMALIZATION / MAPPING
- Map obvious feature tokens (case/format-insensitive):
  "logo" → [LOGO], "imgt_model"|"IMGT_MODEL"|"imgt-model" → [IMGT-MODEL], etc.
- Map "noVO"/"novo" → VO-any.
- Creator & filename → PascalCase; DIM → uppercase; known tag tokens normalized.
- Language must come from the language slot only (not from filename or arbitrary tokens).

ABSOLUTE "DO NOT"s
- Do NOT output "-" placeholders anywhere.
- Do NOT duplicate or reorder the 4 tags; exactly HOOK, then VO, then MUSIC, then DIM.
- Do NOT place any tokens after [language], except an optional valid date (DDMMYYYY).
- Do NOT transform "ITE" into "[it]" unless input explicitly contains the Italian language code.

OUTPUT CONTRACT (STRICT)
Return only:
{"corrected":"<final_name>","reasoning":"<very short explanation>"}

Examples (input → corrected):

"10254_SideHussle_3_long_IMGT_MODEL_noVO"
→ "10254_Jiali_internal_Sidehussle_HOOK-any_VO-any_MUSIC-any_PO_[IMGT-MODEL]_[en]"

"11804_houda_Faustine_freelancer_IMGT_MODEL_21_EN"
→ "11804_Houda_freelancer-Faustine-21_HOOK-any_VO-any_MUSIC-any_PO_[IMGT-MODEL]_[en]"

"10853_houda_yellowshirt_dont_emoji_music_IMGT_MODEL_1_ITE_2"
→ "10853_Houda_internal_Yellowshirt-1-ITE-2_HOOK-dont_VO-any_MUSIC-emoji_PO_[IMGT-MODEL]_[en]"

"10767_jiali_Realestate_logo_camdensdigitaldiary_ramdam_hooks_ITE_26082025"
→ "10767_Jiali_ramdam-Camdensdigitaldiary_Realestate_HOOK-hooks_VO-any_MUSIC-any_PO_[LOGO]_[en]_26082025"

"ITE ABC 10946_Jiali_internal_Stanley_HOOK-any_VO-any_MUSIC-any_PO_[ANIM]_[en]"
→ "10946_Jiali_internal_Stanley_HOOK-any_VO-any_MUSIC-any_PO_[ANIM]_[en]"

"internal  blue   hoodie"
→ "internal_BlueHoodie_HOOK-any_VO-any_MUSIC-any_PO_[AIBG]_[en]"
"""

# Use a persistent directory for uploads instead of temp directory
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

init_auth(app)

# Disable Flask's default request logging for cleaner output
import logging as flask_logging
flask_logging.getLogger('werkzeug').setLevel(flask_logging.ERROR)


_CORS_PREFIXES = ('/api/', '/upload', '/status', '/download', '/cancel')


@app.before_request
def handle_preflight_requests():
    if request.method != 'OPTIONS':
        return None

    if not request.path.startswith(_CORS_PREFIXES):
        return None

    response = make_response('', 204)
    origin = request.headers.get('Origin')
    frontend_origin = app.config.get('FRONTEND_URL')
    if origin and frontend_origin and origin.rstrip('/') == frontend_origin.rstrip('/'):
        response.headers['Access-Control-Allow-Origin'] = frontend_origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Headers'] = request.headers.get(
            'Access-Control-Request-Headers', 'Content-Type'
        )
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
        response.headers.add('Vary', 'Origin')
    return response


@app.after_request
def apply_cors_headers(response):
    origin = request.headers.get('Origin')
    frontend_origin = app.config.get('FRONTEND_URL')
    if (
        origin
        and frontend_origin
        and origin.rstrip('/') == frontend_origin.rstrip('/')
        and request.path.startswith(_CORS_PREFIXES)
    ):
        response.headers['Access-Control-Allow-Origin'] = frontend_origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers.setdefault('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        response.headers.setdefault('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Vary', 'Origin')
    return response

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
    """Main landing page - show all Photoroom UA creative tools"""
    from tools_config import TOOLS_CONFIG
    tools = get_active_tools()
    return render_template('index.html', tools=tools, tools_config=TOOLS_CONFIG)

@app.route('/video-converter')
def video_converter():
    """Video converter tool"""
    from tools_config import TOOLS_CONFIG
    tools = get_active_tools()
    return render_template('video_converter.html', tools=tools, tools_config=TOOLS_CONFIG)

@app.route('/adlocalizer')
def adlocalizer():
    """AdLocalizer tool"""
    from tools_config import TOOLS_CONFIG
    tools = get_active_tools()
    
    # Import centralized language configuration
    from language_config import LANGUAGES, get_all_languages_for_display
    
    # Create a clean format for the template (code -> name mapping)
    template_languages = {code: info['name'] for code, info in LANGUAGES.items()}
    
    VOICES = {
        "1": {"name": "Tom Cruise", "id": "g60FwKJuhCJqbDCeuXjm"},
        "2": {"name": "Doja Cat", "id": "E1c1pVuZVvPrme6B9ryw"},
        "3": {"name": "Chris", "id": "iP95p4xoKVk53GoZ742B"}
    }
    
    return render_template('adlocalizer.html', languages=template_languages, voices=VOICES, tools=tools, tools_config=TOOLS_CONFIG)



@app.route('/health')
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'port': request.environ.get('SERVER_PORT', os.environ.get('PORT', 'unknown')),
        'services': ['video-converter', 'adlocalizer']
    })

@app.route('/api/test')
def api_test():
    return jsonify({'message': 'API routes are working', 'timestamp': datetime.now().isoformat()})

@app.route("/api/correct-creative-name", methods=["POST"])
def correct_creative_name():
    """Correct creative names using OpenAI to match Photoroom naming conventions"""
    if not OPENAI_AVAILABLE:
        return jsonify({"error": "OpenAI functionality not available"}), 500
    
    # Get API key from environment (try different formats)
    api_key = (
        os.environ.get("OPENAI_API_KEY") or 
        os.environ.get("openai_api_key") or 
        os.environ.get("OPENAI_KEY")
    )
    
    if not api_key:
        return jsonify({"error": "OpenAI API key not configured"}), 500
    
    # Initialize client with the API key
    try:
        client = OpenAI(api_key=api_key)
    except Exception as e:
        app_logger.error(f"Failed to initialize OpenAI client: {e}")
        return jsonify({"error": "OpenAI client initialization failed"}), 500
    
    data = request.get_json(silent=True) or {}
    raw = (data.get("name") or "").strip()
    if not raw:
        return jsonify({"error": "Missing 'name'"}), 400

    try:
        # Use structured output for reliable JSON parsing
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": NAMING_RULES},
                {"role": "user", "content": f"INPUT:\n```\n{raw}\n```\nOutput the JSON object per contract."}
            ],
            temperature=0,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "creative_name_correction",
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "corrected": {"type": "string", "minLength": 5},
                            "reasoning": {"type": "string", "minLength": 3}
                        },
                        "required": ["corrected", "reasoning"]
                    }
                }
            }
        )

        # Extract the structured output
        payload = response.choices[0].message.content
        if isinstance(payload, str):
            payload = json.loads(payload)

        corrected = payload.get("corrected") or ""
        reasoning = payload.get("reasoning") or "Adjusted to match Photoroom naming rules."

        if not corrected:
            return jsonify({"error": "No suggestion produced"}), 422

        return jsonify({"corrected": corrected, "reasoning": reasoning})

    except json.JSONDecodeError as e:
        app_logger.error(f"JSON decode error in correct_creative_name: {e}")
        return jsonify({"error": "Invalid response format from AI"}), 500
    except Exception as e:
        app_logger.error(f"Error in correct_creative_name: {e}")
        # Don't leak internals
        return jsonify({"error": "Model call failed"}), 500

# Import video converter routes
from video_converter_app import (
    upload_files, get_job_status, download_file, download_zip, 
    cleanup_job, cancel_job, process_videos_background, debug_job
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
    """Vocal removal is currently disabled; return an empty payload."""
    return jsonify({
        'success': True,
        'models': {},
        'default_model': None,
        'message': 'Vocal removal is disabled in this deployment.',
    })


@app.route('/api/voices', methods=['GET'])
def api_get_voices():
    try:
        from adlocalizer_app import list_voices
        return list_voices()
    except ImportError:
        return jsonify({'error': 'AdLocalizer functionality not available'}), 500

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

@app.route('/api/download-all-voiceovers')
def api_download_all_voiceovers():
    try:
        from adlocalizer_app import download_all_voiceovers
        return download_all_voiceovers()
    except ImportError:
        return jsonify({'error': 'AdLocalizer functionality not available'}), 500


@app.route('/adlocalizer/subtitles/<path:filename>')
def api_download_subtitle(filename):
    try:
        from adlocalizer_app import download_subtitle_file
        return download_subtitle_file(filename)
    except ImportError:
        return jsonify({'error': 'AdLocalizer functionality not available'}), 500


@app.route('/api/subtitles/reburn', methods=['POST'])
def api_reburn_subtitles():
    try:
        from adlocalizer_app import reburn_subtitles
        return reburn_subtitles()
    except ImportError:
        return jsonify({'error': 'AdLocalizer functionality not available'}), 500


@app.route('/api/subtitles/retry', methods=['POST'])
def api_retry_subtitles():
    try:
        from adlocalizer_app import retry_subtitles
        return retry_subtitles()
    except ImportError:
        return jsonify({'error': 'AdLocalizer functionality not available'}), 500

@app.route('/api/extract-playlist', methods=['POST'])
def api_extract_playlist():
    """Extract video IDs from YouTube playlist"""
    try:
        from youtube_playlist_app import process_playlist
        return process_playlist()
    except ImportError:
        return jsonify({'error': 'YouTube playlist functionality not available'}), 500


@app.route('/api/youtube-playlists/create', methods=['POST'])
def api_create_youtube_playlists():
    try:
        from youtube_playlist_app import create_playlists
        return create_playlists()
    except ImportError:
        return jsonify({'error': 'YouTube playlist functionality not available'}), 500


@app.route('/api/youtube-uploads', methods=['POST'])
def api_youtube_uploads():
    files = request.files.getlist('files')
    if not files:
        return jsonify({'success': False, 'error': 'No files uploaded'}), 400

    is_valid, error_payload = _check_upload_password(request.form.get('password'))
    if not is_valid:
        return jsonify(error_payload), 401

    upload_temp_dir = Path(tempfile.mkdtemp(prefix='youtube_upload_', dir=app.config['UPLOAD_FOLDER']))
    rows = []
    saved_paths = []

    try:
        overrides_raw = request.form.get('overrides')
        overrides = {}
        if overrides_raw:
            try:
                overrides = json.loads(overrides_raw)
            except json.JSONDecodeError:
                return jsonify({'success': False, 'error': 'Invalid overrides payload'}), 400

        for idx, file in enumerate(files, start=1):
            original_name = file.filename or f'upload_{idx}.mp4'
            safe_name = secure_filename(original_name)
            if not safe_name:
                safe_name = f'upload_{idx}.mp4'

            saved_path = upload_temp_dir / safe_name
            file.save(saved_path)
            saved_paths.append(saved_path)

            hint = Path(original_name).stem
            rows.append({'file_path': str(saved_path), 'playlist_hint': hint, 'original_name': original_name})

        plans = build_plan(rows, csv_dir=upload_temp_dir)

        try:
            uploader = YoutubeUploadClient()
        except Exception as exc:  # noqa: BLE001
            return jsonify({'success': False, 'error': f'Failed to initialize YouTube client: {exc}'}), 500

        normalized_overrides = {}
        for key, value in overrides.items():
            if not isinstance(key, str) or not isinstance(value, str):
                continue
            parts = key.split('|')
            if len(parts) != 2:
                continue
            normalized_overrides[f"{parts[0].upper()}|{parts[1].lower()}"] = value

        results = process_plans(plans, uploader=uploader, temp_dir=upload_temp_dir, overrides=normalized_overrides)

        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        report_dir = Path(app.config['UPLOAD_FOLDER']) / 'youtube_reports'
        report_path = report_dir / f'youtube_upload_results_{timestamp}.csv'
        write_results_csv(results, report_path)

        response_results = []
        for result in results:
            response_results.append({
                'index': result.index,
                'source': result.source,
                'status': result.status,
                'message': result.message,
                'playlist_name': result.playlist_name,
                'playlist_id': result.playlist_id,
                'video_id': result.video_id,
            })

        return jsonify({
            'success': True,
            'results': response_results,
            'report_url': f"/youtube-uploads/report/{report_path.name}",
        })
    finally:
        for path in saved_paths:
            try:
                path.unlink(missing_ok=True)
            except TypeError:
                if path.exists():
                    path.unlink()
        shutil.rmtree(upload_temp_dir, ignore_errors=True)


@app.route('/youtube-uploads/report/<path:filename>')
def download_youtube_upload_report(filename):
    report_dir = Path(app.config['UPLOAD_FOLDER']) / 'youtube_reports'
    target = report_dir / filename
    if not target.exists():
        return jsonify({'error': 'Report not found'}), 404
    return send_file(target, as_attachment=True)


@app.route('/api/youtube-playlists/suggest', methods=['POST'])
def api_youtube_playlist_suggest():
    data = request.get_json(silent=True) or {}
    items = data.get('items')
    if not isinstance(items, list) or not items:
        return jsonify({'success': False, 'error': 'No items provided'}), 400

    is_valid, error_payload = _check_upload_password(data.get('password'))
    if not is_valid:
        return jsonify(error_payload), 401

    try:
        uploader = YoutubeUploadClient(allow_browser=False)
    except CredentialSetupError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 401
    except Exception as exc:  # noqa: BLE001
        return jsonify({'success': False, 'error': f'Failed to initialize YouTube client: {exc}'}), 500

    uploader.refresh_playlist_cache()

    suggestions = []
    for item in items:
        base_tag = (item.get('base_tag') or '').upper()
        language = (item.get('language') or '').lower()
        date_code = (item.get('date') or '').strip()

        if not base_tag or not language:
            suggestions.append({
                'base_tag': base_tag,
                'language': language,
                'target_date': date_code,
                'planned_name': None,
                'suggested_name': None,
                'delta_days': None,
                'use_existing': False,
                'error': 'Missing base tag or language',
            })
            continue

        if not date_code or not date_code.isdigit() or len(date_code) != 8:
            date_code = datetime.utcnow().strftime('%d%m%Y')

        planned_name = f"[{base_tag}]_[{language}]_{date_code}"
        suggestion = uploader.find_closest_playlist(base_tag, language, date_code)

        entry = {
            'base_tag': base_tag,
            'language': language,
            'target_date': date_code,
            'planned_name': planned_name,
            'suggested_name': None,
            'suggested_date': None,
            'delta_days': None,
            'use_existing': False,
        }

        if suggestion:
            entry['suggested_name'] = suggestion['name']
            entry['suggested_date'] = suggestion['date']
            entry['delta_days'] = suggestion['delta_days']
            entry['use_existing'] = suggestion['name'] != planned_name

        suggestions.append(entry)

    return jsonify({'success': True, 'items': suggestions})

# Register video converter routes
app.add_url_rule('/upload', 'upload_files', upload_files, methods=['POST'])
app.add_url_rule('/status/<job_id>', 'get_job_status', get_job_status)
app.add_url_rule('/download/<job_id>/<filename>', 'download_file', download_file)
app.add_url_rule('/download_zip/<job_id>', 'download_zip', download_zip)
app.add_url_rule('/cleanup/<job_id>', 'cleanup_job', cleanup_job, methods=['POST'])
app.add_url_rule('/cancel/<job_id>', 'cancel_job', cancel_job, methods=['POST'])
app.add_url_rule('/debug/<job_id>', 'debug_job', debug_job)

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

@app.route('/name-generator')
def name_generator():
    from tools_config import TOOLS_CONFIG
    tools = get_active_tools()
    return render_template('name_generator.html', 
                         tools=tools, 
                         tools_config=TOOLS_CONFIG)

@app.route('/language-mapping')
def language_mapping():
    """Language code mapping reference page"""
    from tools_config import TOOLS_CONFIG
    tools = get_active_tools()
    return render_template('language_mapping.html', 
                         tools=tools, 
                         tools_config=TOOLS_CONFIG)

@app.route('/youtube-playlist')
def youtube_playlist():
    """YouTube Playlist Extractor tool"""
    from tools_config import TOOLS_CONFIG

    tools = get_active_tools()
    return render_template(
        'youtube_playlist.html',
        tools=tools,
        tools_config=TOOLS_CONFIG,
    )


@app.route('/youtube-playlist-batch')
def youtube_playlist_batch():
    """YouTube Playlist Batch Creator tool"""
    from tools_config import TOOLS_CONFIG
    from make_playlists import DEFAULT_LANGUAGES
    from language_config import LANGUAGES

    base_tag_options = ["AIBG", "ANIM", "IMGT-MODEL", "RND"]
    tools = get_active_tools()
    language_options = []
    for code in DEFAULT_LANGUAGES:
        meta = LANGUAGES.get(code, {})
        label = meta.get('name') or code.upper()
        language_options.append({'code': code, 'label': label})

    return render_template(
        'youtube_playlist_batch.html',
        tools=tools,
        tools_config=TOOLS_CONFIG,
        language_options=language_options,
        default_language_codes=list(DEFAULT_LANGUAGES),
        base_tag_options=base_tag_options,
    )


@app.route('/youtube-uploader')
def youtube_uploader_page():
    from tools_config import TOOLS_CONFIG

    tools = get_active_tools()
    return render_template(
        'youtube_uploader.html',
        tools=tools,
        tools_config=TOOLS_CONFIG,
        language_codes=sorted(LANGUAGE_CODES),
        language_map={k: v for k, v in LANGUAGE_MAP.items()},
        feature_aliases=FEATURE_ALIASES,
    )

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
