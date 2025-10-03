# Deployment Guide

This guide covers deployment options for the **Photoroom Creative Tools Platform**, a hybrid Flask + React application.

## 🏗️ Architecture Overview

The platform consists of two components:
- **Flask Backend**: Python application serving REST APIs and legacy Jinja templates
- **React Frontend**: Modern SPA built with Vite, TypeScript, and Chakra UI

**Deployment Options:**
1. **Monolithic**: Flask serves both API and built React app (simplest)
2. **Separate Services**: Backend and frontend deployed independently (more scalable)

## 🚀 Quick Local Setup

### Backend Only (Legacy UI)

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Download AI models** (optional, for vocal removal):
   ```bash
   python3 setup_models.py
   ```
   Downloads ~300MB of AI models for vocal removal features.

3. **Install subtitle fonts** (ensures CJK/RTL captions render correctly):
   ```bash
   python3 setup_fonts.py
   ```

4. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

5. **Start the application**:
   ```bash
   python3 app.py
   ```
   Access at `http://localhost:5000`

### Full Stack (Backend + React)

1. **Complete backend setup** (steps above)

2. **Install frontend dependencies**:
   ```bash
   cd web
   npm install
   ```

3. **Configure frontend environment**:
   ```bash
   cd web
   echo "VITE_API_BASE_URL=http://localhost:5000" > .env
   ```

4. **Start both servers**:
   
   **Terminal 1 (Backend):**
   ```bash
   python3 app.py
   ```
   
   **Terminal 2 (Frontend):**
   ```bash
   cd web && npm run dev
   ```
   
   Access React UI at `http://localhost:5173`

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

## 🌐 Production Deployment

### Option 1: Monolithic Deployment (Recommended for Simplicity)

Flask serves both API endpoints and the built React app as static files.

#### Render.com Setup

1. **Build React app first**:
   ```yaml
   services:
     - type: web
       name: creative-tools-platform
       env: python
       buildCommand: |
         pip install -r requirements.txt
         python3 setup_fonts.py
         cd web && npm install && npm run build && cd ..
       startCommand: "python3 app.py"
       plan: starter
       healthCheckPath: /health
   ```

2. **Configure Flask to serve React**:
   Add to `app.py` (if not already present):
   ```python
   # Serve React app
   @app.route('/', defaults={'path': ''})
   @app.route('/<path:path>')
   def serve_react(path):
       if path and os.path.exists(f'web/dist/{path}'):
           return send_from_directory('web/dist', path)
       return send_from_directory('web/dist', 'index.html')
   ```

3. **Set environment variables** in Render dashboard:
   ```
   SECRET_KEY=<your-secret-key>
   GOOGLE_CLIENT_ID=<your-google-client-id>
   GOOGLE_CLIENT_SECRET=<your-google-client-secret>
   GOOGLE_REDIRECT_URI=https://your-app.onrender.com/api/auth/google/callback
   FRONTEND_URL=https://your-app.onrender.com
   SESSION_COOKIE_SECURE=true
   OPENAI_API_KEY=<your-openai-key>
   ELEVENLABS_API_KEY=<your-elevenlabs-key>
   ```

#### Heroku Setup

1. **Create Procfile**:
   ```
   release: python3 setup_fonts.py
   web: python3 app.py
   ```

2. **Add buildpacks**:
   ```bash
   heroku buildpacks:add --index 1 heroku/nodejs
   heroku buildpacks:add --index 2 heroku/python
   ```

3. **Add build script to package.json**:
   ```json
   {
     "scripts": {
       "heroku-prebuild": "cd web && npm install && npm run build"
     }
   }
   ```

### Option 2: Separate Services Deployment

Deploy backend and frontend independently for better scalability.

#### Backend Service (Render.com)

1. **Configure render.yaml** (backend only):
   ```yaml
   services:
     - type: web
       name: creative-tools-api
       env: python
       buildCommand: "pip install -r requirements.txt && python3 setup_fonts.py"
       startCommand: "python3 app.py"
       plan: starter
       healthCheckPath: /health
       envVars:
         - key: FRONTEND_URL
           value: https://your-frontend.onrender.com
         - key: SESSION_COOKIE_SECURE
           value: "true"
   ```

2. **Enable CORS** in Flask (if not already configured):
   ```python
   from flask_cors import CORS
   CORS(app, supports_credentials=True, origins=[os.environ.get('FRONTEND_URL')])
   ```

#### Frontend Service (Render Static Site or Vercel)

**Render Static Site:**
1. Create new Static Site in Render
2. **Build Command**: `cd web && npm install && npm run build`
3. **Publish Directory**: `web/dist`
4. **Environment Variables**:
   ```
   VITE_API_BASE_URL=https://your-backend.onrender.com
   ```

**Vercel:**
1. Import repository
2. **Root Directory**: `web`
3. **Build Command**: `npm run build`
4. **Output Directory**: `dist`
5. **Environment Variables**:
   ```
   VITE_API_BASE_URL=https://your-backend.onrender.com
   ```

### Option 3: Heroku (Monolithic)

Add to `Procfile`:
```
release: python3 setup_fonts.py && cd web && npm install && npm run build
web: python3 app.py
```

## 🔐 Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key for sessions | Random string (use `openssl rand -hex 32`) |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | `xxx.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | `GOCSPX-xxx` |
| `GOOGLE_REDIRECT_URI` | OAuth callback URL | `https://your-app.com/api/auth/google/callback` |

### Frontend Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `FRONTEND_URL` | React app URL | `https://your-app.com` or `http://localhost:5173` |
| `FRONTEND_APP_PATH` | Protected routes base path | `/app` |
| `FRONTEND_LOGIN_PATH` | Login page path | `/login` |

### Session & Security

| Variable | Description | Default |
|----------|-------------|---------|
| `SESSION_COOKIE_SECURE` | Use HTTPS-only cookies (true in production) | `false` |
| `SESSION_COOKIE_SAMESITE` | Cookie SameSite policy | `Lax` |
| `SESSION_LIFETIME_DAYS` | Session duration in days | `7` |

### API Keys (Optional, feature-specific)

| Variable | Description | Required For |
|----------|-------------|--------------|
| `OPENAI_API_KEY` | OpenAI API key | AdLocalizer transcription & translation |
| `ELEVENLABS_API_KEY` | ElevenLabs API key | AdLocalizer voice generation |
| `REPLICATE_API_TOKEN` | Replicate API token | Cloud vocal removal (optional) |
| `R2_ACCOUNT_ID` | Cloudflare R2 account ID | R2 storage integration |
| `R2_ACCESS_KEY_ID` | R2 access key | R2 storage integration |
| `R2_SECRET_ACCESS_KEY` | R2 secret key | R2 storage integration |
| `R2_BUCKET_NAME` | R2 bucket name | R2 storage integration |

### YouTube Tools

| Variable | Description | Default |
|----------|-------------|---------|
| `YOUTUBE_UPLOAD_PASSWORD` | Shared password for bulk uploads | `PhotoroomUA2025` |
| `YOUTUBE_UPLOAD_MAX_MB` | Max upload size (0 = unlimited) | `0` |

### Performance Tuning

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Server port | `5000` |
| `VIDEO_UPLOAD_MAX_MB` | Max video upload size | `2048` |
| `VIDEO_UPLOAD_CHUNK_MB` | Upload chunk size | `8` |
| `VIDEO_PROCESS_MAX_WORKERS` | Concurrent FFmpeg jobs | `min(4, CPU cores)` |
| `VIDEO_PROCESS_MAX_RETRIES` | Retry attempts per task | `1` |

## 📊 Resource Requirements

### Minimum Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **RAM** | 512 MB | 1-2 GB |
| **CPU** | 1 core | 2+ cores |
| **Disk** | 500 MB | 1 GB |
| **Bandwidth** | 1 GB/month | Depends on usage |

### Storage Breakdown

- **Python dependencies**: ~200 MB
- **Node modules** (build only): ~300 MB (not deployed)
- **AI models** (optional): ~300 MB
- **Fonts**: ~50 MB
- **Temp uploads**: Auto-cleaned after processing
- **Built React app**: ~2-5 MB

### Performance Notes

- **Video processing**: CPU-bound, benefits from multiple cores
- **Parallel conversions**: Configurable via `VIDEO_PROCESS_MAX_WORKERS`
- **Memory usage**: Scales with concurrent jobs and file sizes
- **FFmpeg**: Pre-installed on Render.com, no additional setup needed

## 🔧 Google OAuth Setup

1. **Go to Google Cloud Console**: https://console.cloud.google.com/

2. **Create a new project** (or select existing)

3. **Enable Google+ API**:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google+ API"
   - Click "Enable"

4. **Create OAuth 2.0 Credentials**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Application type: "Web application"
   - **Authorized JavaScript origins**:
     ```
     http://localhost:5173
     http://localhost:5000
     https://your-production-domain.com
     ```
   - **Authorized redirect URIs**:
     ```
     http://localhost:5000/api/auth/google/callback
     https://your-production-domain.com/api/auth/google/callback
     ```

5. **Copy credentials**:
   - Client ID → `GOOGLE_CLIENT_ID`
   - Client Secret → `GOOGLE_CLIENT_SECRET`

6. **Configure OAuth consent screen**:
   - Add your email as a test user (for development)
   - Fill in app information

## 🐛 Troubleshooting

### Google OAuth Issues

**Error: redirect_uri_mismatch**
```bash
# Verify redirect URI matches exactly in:
# 1. Google Console authorized redirect URIs
# 2. GOOGLE_REDIRECT_URI environment variable
# 3. Frontend VITE_API_BASE_URL + /api/auth/google/callback
```

**Error: Cookies not being set**
- Ensure `SESSION_COOKIE_SECURE=true` in production (HTTPS only)
- Check `SESSION_COOKIE_SAMESITE=Lax` or `None` (for cross-origin)
- Verify `FRONTEND_URL` matches the actual domain

**OAuth works locally but fails in production**
- Update Google Console with production URLs
- Set `SESSION_COOKIE_SECURE=true` for HTTPS
- Verify environment variables in deployment platform

### Build Issues

**React build fails**
```bash
# Clear cache and rebuild
cd web
rm -rf node_modules dist
npm install
npm run build
```

**Python dependencies fail**
```bash
# Ensure Python 3.9+
python3 --version

# Update pip
pip install --upgrade pip

# Install with verbose output
pip install -r requirements.txt -v
```

### Runtime Issues

**Fonts not rendering (CJK/RTL languages)**
```bash
# Verify fonts installed
ls static/fonts/

# Re-run font setup
python3 setup_fonts.py
```

**FFmpeg not found**
```bash
# Check FFmpeg availability
which ffmpeg
ffmpeg -version

# On Ubuntu/Debian
sudo apt-get install ffmpeg

# On macOS
brew install ffmpeg
```

**Video processing fails**
- Check available disk space (need 2-3x video size)
- Verify FFmpeg is installed and accessible
- Review logs for specific FFmpeg errors
- Reduce `VIDEO_PROCESS_MAX_WORKERS` if memory constrained

**API key errors**
```bash
# Verify API keys are set
python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print('OpenAI:', bool(os.getenv('OPENAI_API_KEY'))); print('ElevenLabs:', bool(os.getenv('ELEVENLABS_API_KEY')))"
```

### Performance Issues

**Slow video conversion**
- Increase `VIDEO_PROCESS_MAX_WORKERS` (up to CPU cores)
- Upgrade to a plan with more CPU cores
- Consider using cloud storage for large files

**High memory usage**
- Reduce `VIDEO_PROCESS_MAX_WORKERS`
- Lower `VIDEO_UPLOAD_MAX_MB` to limit file sizes
- Enable auto-cleanup of temp files

**React app loading slowly**
```bash
# Optimize build
cd web
npm run build

# Check bundle size
du -sh dist/
```

## 📈 Monitoring & Logs

### Health Checks

The app provides a health endpoint:
```bash
curl https://your-app.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-03T12:00:00Z"
}
```

### Logs

**Render.com**: View logs in dashboard under "Logs" tab

**Heroku**: 
```bash
heroku logs --tail
```

**Local**:
```bash
# Flask logs to stdout
python3 app.py

# React dev server logs
cd web && npm run dev
```

### Common Log Patterns

```
INFO: Video conversion started for job_id=abc123
WARNING: Retry attempt 1/3 for task xyz
ERROR: FFmpeg processing failed: [error details]
INFO: OAuth callback received, setting session
```

## 🚀 Post-Deployment Checklist

- [ ] Verify health endpoint returns 200 OK
- [ ] Test Google OAuth login flow end-to-end
- [ ] Upload and convert a test video
- [ ] Test AdLocalizer with sample audio/video
- [ ] Check that fonts render correctly for CJK languages
- [ ] Verify environment variables are set correctly
- [ ] Test both React UI and legacy UI routes
- [ ] Monitor logs for errors during first few hours
- [ ] Set up uptime monitoring (UptimeRobot, Pingdom, etc.)
- [ ] Document your production URLs and credentials

## 📚 Additional Resources

- [Flask Deployment Guide](https://flask.palletsprojects.com/en/stable/deploying/)
- [Vite Production Build](https://vitejs.dev/guide/build.html)
- [Render.com Documentation](https://render.com/docs)
- [Google OAuth Setup Guide](https://developers.google.com/identity/protocols/oauth2)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)

---

**Need help?** Check the main [README.md](README.md) or open an issue on GitHub.
