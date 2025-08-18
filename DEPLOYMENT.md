# Deployment Guide

## Quick Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Download AI models** (required for vocal removal):
   ```bash
   python3 setup_models.py
   ```
   This downloads ~300MB of AI models for vocal removal.

3. **Start the application**:
   ```bash
   python3 app.py
   ```

## ⚠️ Vocal Removal Feature Disabled

**AI vocal removal has been temporarily disabled to reduce deployment size.**

### What was removed:
- **PyTorch dependencies**: ~2-3GB saved
- **DEMUCS models**: ~240MB saved  
- **Replicate API**: Cloud processing dependencies
- **Total savings**: ~3-4GB deployment size reduction

### Available Options:
- **Option A**: Upload SFX-only video (recommended)
- **Option B**: Upload video + replace with custom music
- **Option C**: ~~AI vocal removal~~ (disabled)

## Production Deployment

### Render.com Setup
1. Add to `render.yaml`:
   ```yaml
   services:
     - type: web
       name: video-converter
       env: python
       buildCommand: "pip install -r requirements.txt && python3 setup_models.py"
       startCommand: "python3 app.py"
   ```

### Heroku Setup
Add to `Procfile`:
```
release: python3 setup_models.py
web: python3 app.py
```

## Environment Variables

- `SECRET_KEY`: Flask secret key for sessions
- `PORT`: Port to run on (default: 5000)
- `REPLICATE_API_TOKEN`: Replicate API token for cloud vocal removal (optional)

## Storage Requirements

- **Disk space**: Minimal (AI models removed)
- **Memory**: 1GB+ recommended for video processing
- **Temp storage**: Videos processed in `/tmp` directories

## Performance Notes

- **Faster deployment**: No heavy AI model downloads
- **Reduced memory usage**: No PyTorch/DEMUCS inference
- **Lower costs**: No GPU requirements for vocal processing
- **Simpler setup**: Fewer dependencies to manage

## Troubleshooting

### Models not downloading
```bash
# Check if models exist
python3 -c "from vocal_models_config import get_available_models, check_replicate_available; print('Replicate available:', check_replicate_available()); print('Available models:', list(get_available_models().keys()))"

# Re-run setup
python3 setup_models.py
```

### Replicate API not working
```bash
# Check API token
echo $REPLICATE_API_TOKEN

# Set API token (get from https://replicate.com/account/api-tokens)
export REPLICATE_API_TOKEN=your_token_here
```

### Memory issues
- Ensure at least 2GB RAM available
- Use DEMUCS v4 instead of UVR MDX-Net for lower memory usage