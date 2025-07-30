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
VOCAL_REMOVAL_MODELS = {
    "htdemucs_ft": {
        "name": "DEMUCS v4 (High Quality)",
        "description": "Latest DEMUCS with transformers - excellent quality",
        "quality": "Excellent",
        "speed": "Medium",
        "engine": "demucs",
        "model_name": "htdemucs_ft",
        "recommended": True,
        "params": {
            "--two-stems": "vocals",
            "--mp3": True,
            "--mp3-bitrate": "320"
        }
    },
    "replicate_all_in_one": {
        "name": "Replicate All-in-One Audio (Best)",
        "description": "AI Music Structure Analyzer + Stem Splitter using Demucs & Mdx-Net",
        "quality": "Outstanding",
        "speed": "Fast",
        "engine": "replicate",
        "model_name": "erickluis00/all-in-one-audio",
        "recommended": True,
        "params": {
            "model": "harmonix-all",
            "audioSeparatorModel": "Kim_Vocal_2.onnx"
        }
    }
}

def get_model_config(model_id):
    """Get configuration for a specific model"""
    return VOCAL_REMOVAL_MODELS.get(model_id)

# get_available_models() is now defined below with dependency checking

def get_recommended_models():
    """Get list of recommended models"""
    return {k: v for k, v in VOCAL_REMOVAL_MODELS.items() if v.get("recommended", False)}

def get_default_model():
    """Get the default model (recommended and fast)"""
    # Return htdemucs_ft as it's better quality and still reliable
    return "htdemucs_ft"

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
    """Check if replicate is available and API token is set"""
    try:
        import replicate
        api_token = os.environ.get('REPLICATE_API_TOKEN')
        return api_token is not None
    except ImportError:
        return False

def get_available_models():
    """Get list of all available models (only those that can actually run)"""
    replicate_available = check_replicate_available()
    
    # Filter models based on what's actually available
    available_models = {}
    for model_id, model_config in VOCAL_REMOVAL_MODELS.items():
        if model_config["engine"] == "demucs":
            # DEMUCS should always be available
            available_models[model_id] = model_config
        elif model_config["engine"] == "replicate" and replicate_available:
            # Only include replicate models if the library and API token are available
            available_models[model_id] = model_config
    
    return available_models