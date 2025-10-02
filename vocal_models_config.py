# Vocal Removal Models Configuration
# This file defines the available AI models for vocal removal and their settings
#
# INSTALLATION NOTES:
# - DEMUCS models (htdemucs, htdemucs_ft) work out of the box
# - For UVR MDX-Net model, install: pip install audio-separator librosa omegaconf
# - The system automatically detects which models are available

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Available vocal removal models (simplified to best options)
VOCAL_REMOVAL_MODELS: dict[str, dict] = {}

def get_model_config(model_id):
    """Get configuration for a specific model"""
    return VOCAL_REMOVAL_MODELS.get(model_id)

# get_available_models() is now defined below with dependency checking

def get_recommended_models():
    """Get list of recommended models"""
    return {k: v for k, v in VOCAL_REMOVAL_MODELS.items() if v.get("recommended", False)}

def get_default_model():
    """Get the default model (recommended and fast)"""
    return None

def validate_model_id(model_id):
    """Validate if model ID exists"""
    return model_id in VOCAL_REMOVAL_MODELS

# Model download URLs and checksums (for future auto-download functionality)
MODEL_DOWNLOADS = {
    "bs_roformer": {
        "url": "https://github.com/TRvlvr/model_repo/releases/download/all_public_uvr_models/BS-Roformer-Viperx-1297.ckpt",
        "checksum": "sha256:..."  # Add actual checksum
    },
    "melband_roformer": {
        "url": "https://github.com/TRvlvr/model_repo/releases/download/all_public_uvr_models/mel_band_roformer_crowd_finetuned.ckpt", 
        "checksum": "sha256:..."  # Add actual checksum
    },
    "uvr_mdx": {
        "url": "https://github.com/TRvlvr/model_repo/releases/download/all_public_uvr_models/UVR-MDX-NET-Inst_HQ_3.ckpt",
        "checksum": "sha256:..."  # Add actual checksum
    }
}

def get_models_directory():
    """Get the directory where models are stored"""
    models_dir = Path("vocal_models")
    models_dir.mkdir(exist_ok=True)
    return models_dir

def check_replicate_available():
    """Check if replicate is available and API token is set - DISABLED"""
    # Replicate dependency has been removed to reduce deployment size
    return False

def get_available_models():
    """Return available vocal removal models (feature disabled)."""
    return {}
