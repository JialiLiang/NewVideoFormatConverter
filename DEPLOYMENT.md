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

## Vocal Removal Models

The app supports high-quality vocal removal models:

- **DEMUCS v4**: Excellent quality, local processing (~15 seconds)
- **Replicate All-in-One Audio**: Outstanding quality, cloud processing (~130 seconds)

### Model Setup Details

The `setup_models.py` script downloads:
- **DEMUCS v4 (htdemucs_ft)**: ~240MB (required, local processing)
- **Replicate API**: Cloud-based processing (requires API token)

## Production Deployment

### Docker Setup
```dockerfile
FROM python:3.11

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Download AI models during build
RUN python3 setup_models.py

EXPOSE 5000
CMD ["python3", "app.py"]
```

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

- **Disk space**: ~300MB for AI models
- **Memory**: 2GB+ recommended for model inference
- **Temp storage**: Videos processed in `/tmp` directories

## Performance Notes

- **DEMUCS v4**: Local processing, ~15 seconds, no API costs
- **Replicate API**: Cloud processing, ~130 seconds, ~$0.13 per run
- Models are cached after first download (DEMUCS only)
- Replicate API requires internet connection and API token

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