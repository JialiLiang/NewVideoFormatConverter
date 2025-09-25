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

def enforce_min_shape(s: str) -> str:
    """Tiny post-check/normalizer as safety net"""
    parts = s.split("_")

    # Enforce brackets for feature & language (last 2 or 3 parts depending on date)
    def wrap_if_needed(x: str) -> str:
        return x if (x.startswith("[") and x.endswith("]")) else f"[{x}]"

    # Identify AdManage vs Basic quickly
    is_adm = bool(parts and parts[0].isdigit())

    # Locate feature/lang indexes from the end (… _[feature]_[lang][_date?])
    # Basic: 8 parts total; AdManage: 9/10/11
    if is_adm:
        # Date optional; feature = -3, lang = -2
        if len(parts) >= 2:
            parts[-2] = wrap_if_needed(parts[-2])  # lang
        if len(parts) >= 3:
            parts[-3] = wrap_if_needed(parts[-3])  # feature
    else:
        if len(parts) >= 2:
            parts[-2] = wrap_if_needed(parts[-2])  # lang
        if len(parts) >= 3:
            parts[-3] = wrap_if_needed(parts[-3])  # feature
    
    # Also wrap any remaining unbracketed features or languages
    for i in range(len(parts)):
        if parts[i] in FEATURES and not (parts[i].startswith("[") and parts[i].endswith("]")):
            parts[i] = f"[{parts[i]}]"
        elif re.fullmatch(r"[a-z]{2}|[A-Z]{2}", parts[i]) and not (parts[i].startswith("[") and parts[i].endswith("]")):
            parts[i] = f"[{parts[i]}]"

    # Fix DIM to uppercase and default if missing/invalid
    # DIM position: Basic index 5; AdManage with filename: index 7; AdManage 9-part (no filename): index 6
    dim_idx = None
    if not is_adm and len(parts) >= 6:
        dim_idx = 5
    elif is_adm:
        if len(parts) in (10, 11):       # with filename
            dim_idx = 7
        elif len(parts) in (9,):         # compressed creator-type case
            dim_idx = 6
    if dim_idx is not None and 0 <= dim_idx < len(parts):
        parts[dim_idx] = parts[dim_idx].upper()
        if parts[dim_idx] not in DIMS:
            parts[dim_idx] = "PO"

    # Ensure the three tag prefixes exist; if not, set to any
    def ensure_tag(p, prefix):
        return p if p.startswith(prefix + "-") else f"{prefix}-any"
    # Basic indices 2/3/4, AdManage-with-filename 4/5/6, AdManage-9part 3/4/5
    if not is_adm and len(parts) >= 5:
        parts[2] = ensure_tag(parts[2], "HOOK")
        parts[3] = ensure_tag(parts[3], "VO")
        parts[4] = ensure_tag(parts[4], "MUSIC")
    elif is_adm:
        if len(parts) in (10, 11):
            parts[4] = ensure_tag(parts[4], "HOOK")
            parts[5] = ensure_tag(parts[5], "VO")
            parts[6] = ensure_tag(parts[6], "MUSIC")
        elif len(parts) == 9:
            parts[3] = ensure_tag(parts[3], "HOOK")
            parts[4] = ensure_tag(parts[4], "VO")
            parts[5] = ensure_tag(parts[5], "MUSIC")

    return "_".join(parts)

def extract_iteration_hint(raw: str):
    """
    Returns (base_num, iter_num).
      ... _1_ITE_2 ...  -> (1, 2)
      ... ITE_3 ...     -> (None, 3)
      ... -ITE-4 ...    -> (None, 4)
    """
    # Look for pattern: _1_ITE_2 (base number before ITE, but not a date)
    m = re.search(r"(?:^|_)(\d{1,3})_ITE_(\d+)(?:_|$)", raw, re.I)
    if m:
        base_num = int(m.group(1))
        # Don't treat dates as base numbers (8 digits)
        if base_num < 1000:  # Only small numbers are base variations
            return base_num, int(m.group(2))
    
    # Look for pattern: ITE_3 or -ITE-3 (just iteration number)
    m = re.search(r"(?:^|_|-)[Ii][Tt][Ee][-_]?(\d+)(?:_|$)", raw)
    if m:
        return None, int(m.group(1))
    
    return None, None

def extract_lang_hint(raw: str):
    # Prefer bracketed language if present
    m = re.search(r"\[([a-z]{2})\]", raw, re.I)
    if m:
        return m.group(1).lower()
    # Fallback: standalone 2‑letter token bounded by underscores/boundaries
    m = re.search(r"(?:^|_)([a-z]{2})(?:_|$)", raw, re.I)
    if m:
        return m.group(1).lower()
    return None

def enforce_iteration_from_raw(raw: str, corrected: str) -> str:
    """
    1) If raw contains ITE info, put -ITE-<n> on the filename (or on creator-type-with-name in 9-part AdManage).
       If there is a bare number near ITE (e.g. _1_ITE_2), treat that as base '-1' before '-ITE-2'.
    2) Prevent 'ITE' turning into '[it]' unless INPUT explicitly asked for it.
    3) After language, allow only an optional date (DDMMYYYY). Drop everything else.
       Also strip any accidental '-ITE-<n>' suffix attached to the language token.
    """
    base_num, iter_num = extract_iteration_hint(raw)
    parts = corrected.split("_")
    if not parts:
        return corrected

    is_adm = bool(parts[0].isdigit())

    # --- (1) Place iteration on the correct slot ---
    if is_adm:
        if len(parts) in (10, 11):
            # AdManage with filename (no date: 10, with date: 11). Filename at index 3.
            filename_idx = 3
            filename = parts[filename_idx]
            # Remove any trailing ITE; we'll re-apply cleanly
            filename = re.sub(r"-ITE-\d+$", "", filename, flags=re.I)

            # Add base num if present and not already there
            if base_num is not None and not re.search(r"-\d+$", filename):
                filename = f"{filename}-{base_num}"
            elif base_num is None and iter_num is not None and not re.search(r"-\d+$", filename):
                # If we have iteration but no base number, default to base 1
                filename = f"{filename}-1"

            # Append ITE if present
            if iter_num is not None and not re.search(r"-ITE-\d+$", filename, flags=re.I):
                filename = f"{filename}-ITE-{iter_num}"

            parts[filename_idx] = filename

        elif len(parts) == 9:
            # Compressed non-internal case (no filename): slot 2 is "{type}-{CreatorName[-num]}"
            field2 = parts[2]
            # Check if iteration is already present
            if iter_num is not None and re.search(rf"-ITE-{iter_num}$", field2, flags=re.I):
                # Iteration already present, just clean up any stray suffixes
                pass
            else:
                # Apply iteration logic
                field2 = re.sub(r"-ITE-\d+$", "", field2, flags=re.I)
                if base_num is not None and not re.search(r"-\d+$", field2):
                    field2 = f"{field2}-{base_num}"
                elif base_num is None and iter_num is not None and not re.search(r"-\d+$", field2):
                    # If we have iteration but no base number, default to base 1
                    field2 = f"{field2}-1"
                if iter_num is not None and not re.search(r"-ITE-\d+$", field2, flags=re.I):
                    field2 = f"{field2}-ITE-{iter_num}"
            parts[2] = field2
    else:
        # Basic format: [creator-type]_[filename]_[HOOK]_[VO]_[MUSIC]_[DIM]_[feature]_[language]
        # Filename is at index 1
        if len(parts) >= 8:
            filename_idx = 1
            filename = parts[filename_idx]
            # Remove any trailing ITE; we'll re-apply cleanly
            filename = re.sub(r"-ITE-\d+$", "", filename, flags=re.I)

            # Add base num if present and not already there
            if base_num is not None and not re.search(r"-\d+$", filename):
                filename = f"{filename}-{base_num}"
            elif base_num is None and iter_num is not None and not re.search(r"-\d+$", filename):
                # If we have iteration but no base number, default to base 1
                filename = f"{filename}-1"

            # Append ITE if present
            if iter_num is not None and not re.search(r"-ITE-\d+$", filename, flags=re.I):
                filename = f"{filename}-ITE-{iter_num}"

            parts[filename_idx] = filename

    # --- (2) If model hallucinated [it] from ITE, undo unless input explicitly set Italian ---
    raw_lang = extract_lang_hint(raw)

    # Find the last bracketed language token (may have ITE suffix)
    lang_idx = None
    for i in range(len(parts) - 1, -1, -1):
        if re.match(r"\[[A-Za-z]{2}\]", parts[i]):
            lang_idx = i
            break

    if lang_idx is not None:
        if raw_lang != "it" and parts[lang_idx].lower() == "[it]":
            parts[lang_idx] = f"[{raw_lang or 'en'}]"

        # Remove any accidental '-ITE-<n>' suffix glued to the language token
        parts[lang_idx] = re.sub(r"\]-ITE-\d+$", "]", parts[lang_idx], flags=re.I)

    # --- (3) Nothing after language except optional date ---
    last = len(parts) - 1
    date_idx = last if re.fullmatch(r"\d{8}", parts[last] or "") else None

    if lang_idx is not None:
        if date_idx is not None and date_idx > lang_idx:
            # Keep everything up to lang, plus the date (drop anything between)
            parts = parts[:lang_idx + 1] + [parts[date_idx]]
        else:
            # No date → hard stop at language
            parts = parts[:lang_idx + 1]

    return "_".join(parts)


app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB max file size (reduced for memory)

# Shared rules fed to the model (kept crisp + deterministic)
NAMING_RULES = """
You are a strict formatter for Photoroom AdManage creative names.

Accepted outputs:
- AdManage (ID present at start):
  • 11 parts if date present, else 10 parts, OR a 9‑part edge case below.
  • With filename: [id]_[creator]_[creator-type]_[filename]_[HOOK-…]_[VO-…]_[MUSIC-…]_[DIM]_[feature]_[language][_date]
  • Edge (non‑internal only, when filename is missing or ambiguous): omit filename and encode creator handle (and optional number)
    inside creator-type as "{type}-{CreatorName[-num]}":
    [id]_[creator]_[{type}-{CreatorName[-num]}]_[HOOK-…]_[VO-…]_[MUSIC-…]_[DIM]_[feature]_[language][_date]
- Basic (no ID at start):
  [creator-type]_[filename]_[HOOK-…]_[VO-…]_[MUSIC-…]_[DIM]_[feature]_[language]

Rules:
- "_" separates main fields; "-" separates details inside tags.
- Creator types: internal | freelancer | ramdam | influencer.
  • If non‑internal and filename is missing/ambiguous, compress into "{type}-{CreatorName[-num]}" and omit filename (9-part AdManage).
  • If creator is missing in AdManage, choose one from {Jiali, Houda, Kaja} (prefer Jiali).
  • If creator-type is missing/unclear, default to "internal".
- Filename: PascalCase. If no reliable tokens, treat as missing (see non‑internal edge case).
- Tags (always 4, in order): HOOK → VO → MUSIC → DIM
  • DIM ∈ {PO, SQ, LS} (uppercase; default PO)
  • If HOOK/VO/MUSIC missing → "any"
  • Normalize common pseudo tokens:
    - "noVO" or "novo" → VO-any
- Feature & language MUST be bracketed: _[FEATURE]_[lang]
  • FEATURE ∈ {AIBG, IGSTORY, LOGO, ANIM, MIX, AIFILL, RETOUCH, IMGT-CHANGE, IMGT-MODEL, IMGT-STAGE, IMGT-BEAUTIFY, RnD}
  • lang = ISO 639-1 (lowercase preferred; uppercase allowed but still wrapped)
- Date (AdManage only): include if a valid DDMMYYYY is present; otherwise omit.
- Casing normalization:
  • Creator & filename → PascalCase
  • DIM → uppercase
  • Known tag keywords → normalized
- Iteration tokens:
  • If the INPUT contains an "ITE" token with a number (e.g., _ITE_2, ITE-2), this denotes an **iteration**.
  • Place the iteration on the **filename**, as a suffix: `<Filename>[-<baseNum>]-ITE-<iterNum>`.
    - If a plain integer appears near ITE (e.g., "… _1_ITE_2 …"), treat the plain integer as a **base variation** and add `-1` before `-ITE-2`.
    - If the filename already ends with `-<num>`, keep it and then append `-ITE-<iterNum>`.
  • Never treat "ITE" or "ite" as a language code. Language must come from the dedicated language slot only.
- Preservation & defaults:
  • Preserve trustworthy info from input; fill minimal defaults as above.

OUTPUT CONTRACT (STRICT):
Return only a single JSON object:
{"corrected":"<final_name>","reasoning":"<very short explanation>"}
No prose outside JSON. Never output "-" placeholders. Always include _[FEATURE]_[lang].

Examples (input → corrected):

"10254_SideHussle_3_long_IMGT_MODEL_noVO"
→ "10254_Jiali_internal_Sidehussle_HOOK-any_VO-any_MUSIC-any_PO_[IMGT-MODEL]_[en]"

"11804_houda_Faustine_freelancer_IMGT_MODEL_21_EN"
→ "11804_Houda_freelancer-Faustine-21_HOOK-any_VO-any_MUSIC-any_PO_[IMGT-MODEL]_[en]"

"internal  blue   hoodie"
→ "internal_BlueHoodie_HOOK-any_VO-any_MUSIC-any_PO_[AIBG]_[en]"

"10946_Jiali_internal_Stanley-1_HOOK-comehere_VO-tom_MUSIC-lofi_PO_[ANIM]_[en]_18092025"
→ "10946_Jiali_internal_Stanley-1_HOOK-comehere_VO-tom_MUSIC-lofi_PO_[ANIM]_[en]_18092025"

"10853_houda_yellowshirt_dont_emoji_music_IMGT_MODEL_1_ITE_2"
→ "10853_Houda_internal_Yellowshirt-1-ITE-2_HOOK-dont_VO-any_MUSIC-emoji_PO_[IMGT-MODEL]_[en]"

"10946_Jiali_internal_Stanley_HOOK-comehere_VO-tom_MUSIC-lofi_PO_[ANIM]_[en]_18092025  (append ITE-1)"
→ "10946_Jiali_internal_Stanley-1-ITE-1_HOOK-comehere_VO-tom_MUSIC-lofi_PO_[ANIM]_[en]_18092025"
"""

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

        # Apply post-processing to ensure brackets and order
        corrected = enforce_min_shape(corrected)
        
        # Apply iteration enforcement from raw input
        corrected = enforce_iteration_from_raw(raw, corrected)

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

@app.route('/api/extract-playlist', methods=['POST'])
def api_extract_playlist():
    """Extract video IDs from YouTube playlist"""
    try:
        from youtube_playlist_app import process_playlist
        return process_playlist()
    except ImportError:
        return jsonify({'error': 'YouTube playlist functionality not available'}), 500

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
    return render_template('youtube_playlist.html', 
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