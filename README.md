# 🎥 Photoroom Creative Tools Platform

A comprehensive video processing and content creation platform with multiple professional tools. Built with a **hybrid architecture** combining Flask backend with React frontend for modern user experience.

## 🏗️ Architecture Overview

**Hybrid Stack:**
- **Backend**: Flask (Python) - REST APIs + Legacy Jinja templates
- **Frontend**: React + Vite + TypeScript + Chakra UI
- **Authentication**: Google OAuth 2.0 with session-based auth
- **Deployment**: Render.com ready with automated builds

**Migration Strategy:** Legacy Jinja pages coexist with new React pages, allowing gradual feature migration without disruption.

## 🚀 Features

### Video Converter
- Convert videos to different formats (square, landscape, vertical)
- Smart dynamic adjustment for any input aspect ratio
- High-quality output with optimized FFmpeg settings
- Progressive results display with per-file status tracking
- Background processing with real-time progress updates
- Streamed uploads keep memory usage flat even for large batches
- Resilient task queue with parallel conversions, retries, and error recovery
- Batch ZIP download for completed conversions

### AdLocalizer (AI-Powered Video Localization)
- AI-powered transcription using OpenAI Whisper
- Multi-language translation with OpenAI GPT-4
- Voice generation with ElevenLabs (17+ languages)
- Advanced audio processing with vocal removal options
- Automatic subtitle generation and formatting
- Custom music overlay support
- Audio mixing with original video
- ISO 639-1 compliant language codes

### YouTube Tools
- **Playlist Creator**: Batch creation of YouTube playlists with standardized naming
- **Bulk Uploader**: Upload multiple videos with automatic playlist assignment
- **Drag & Drop Interface**: Modern web UI for video uploads
- **Smart Filename Parsing**: Automatic language and tag detection
- **OAuth Integration**: One-time Google account authentication

### Name Generator
- Creative filename generation with validation
- ISO 639-1 language code support
- OpenAI-powered filename correction
- Built-in validation and formatting rules
- Copy-to-clipboard functionality

### Language Mapping Tool
- ISO 639-1 compliant language code reference
- Complete mapping table for all supported languages
- Inline help and documentation

## 📁 Project Structure

```
NewVideoFormatConverter/
├── app.py                      # Main Flask application entry point
├── oauth_routes.py             # Google OAuth authentication
├── video_converter_app.py      # Video converter module
├── adlocalizer_app.py          # AdLocalizer module  
├── youtube_playlist_app.py     # YouTube playlist creator
├── youtube_uploader.py         # YouTube bulk uploader
├── video_converter.py          # Core video processing functions
├── subtitle_processing.py      # Subtitle generation & formatting
├── subtitle_utils.py           # Subtitle utilities
├── tools_config.py             # Tool configuration
├── language_config.py          # ISO 639-1 language mappings
├── ffmpeg_config.py            # FFmpeg processing config
├── vocal_models_config.py      # Audio processing models
├── setup_fonts.py              # Font installation script
├── setup_models.py             # AI model setup script
├── requirements.txt            # Python dependencies
├── render.yaml                 # Render.com deployment config
├── templates/                  # Jinja templates (legacy UI)
│   ├── base.html
│   ├── index.html             # Dashboard
│   ├── video_converter.html
│   ├── adlocalizer.html
│   ├── name_generator.html
│   ├── youtube_playlist.html
│   ├── youtube_uploader.html
│   └── partials/
│       └── navbar.html
├── static/                     # Static assets for legacy UI
│   ├── fonts/                 # Multi-language fonts (CJK, RTL)
│   ├── music/                 # Default background music tracks
│   └── styles/
├── storage/
│   └── r2_storage.py          # Cloudflare R2 storage integration
├── youtube_upload/            # YouTube upload package
│   ├── downloader.py
│   ├── uploader.py
│   ├── planner.py
│   ├── runner.py
│   └── models.py
├── web/                        # React frontend (new UI)
│   ├── src/
│   │   ├── pages/             # React page components
│   │   │   ├── LoginPage.tsx
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── ProfilePage.tsx
│   │   │   ├── VideoConverterPage.tsx
│   │   │   ├── AdLocalizerPage.tsx
│   │   │   ├── NameGeneratorPage.tsx
│   │   │   └── YoutubePlaylistPage.tsx
│   │   ├── api/               # API client modules
│   │   ├── components/        # Reusable components
│   │   ├── layouts/           # Layout components
│   │   ├── routes/            # Route configuration
│   │   ├── providers/         # Context providers
│   │   └── utils/
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
└── uploads/                    # Temporary upload directory
```

## ✨ Recent Improvements

### Google OAuth Integration
- Secure authentication with Google accounts
- Session-based auth with httpOnly cookies
- Protected routes for sensitive operations
- React-based login flow with protected route guards

### ISO 639-1 Language Standardization
- Migrated from legacy codes (JP, KR, BR) to standard ISO codes (ja, ko, pt)
- Centralized language configuration in `language_config.py`
- Full backward compatibility during transition
- Dedicated language mapping reference page

### Modular Architecture
- Split monolithic app into focused modules
- Separate concerns: video processing, localization, YouTube tools
- Better error handling and logging
- Easier testing and maintenance

### Enhanced Video Processing
- Streamed uploads for large files
- Parallel conversion queue with retry logic
- Per-file status tracking and error reporting
- Batch download as ZIP

## 🛠️ Installation

### Prerequisites
- Python 3.9 or higher
- Node.js 18+ (for React frontend)
- FFmpeg (pre-installed on most systems, required for video processing)
- Google Cloud Console project with OAuth 2.0 credentials (for authentication)
- OpenAI API key (for AdLocalizer transcription and translation)
- ElevenLabs API key (for voice generation)

### Backend Setup

1. **Clone the repository:**
```bash
git clone <repository-url>
cd NewVideoFormatConverter
```

2. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

3. **Download AI models (for vocal removal):**
```bash
python3 setup_models.py
```

4. **Install subtitle fonts (for CJK/RTL language support):**
```bash
python3 setup_fonts.py
```

5. **Set up environment variables (create `.env` file):**
```env
# Required
SECRET_KEY=your_secret_key_here

# Google OAuth (required for authentication)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:5000/api/auth/google/callback

# Frontend URLs
FRONTEND_URL=http://localhost:5173
FRONTEND_APP_PATH=/app
FRONTEND_LOGIN_PATH=/login

# Session Configuration
SESSION_COOKIE_SECURE=false          # Set to true in production with HTTPS
SESSION_LIFETIME_DAYS=7

# AdLocalizer APIs (optional, required for AdLocalizer features)
OPENAI_API_KEY=your_openai_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key

# YouTube Tools (optional, required for YouTube features)
YOUTUBE_UPLOAD_PASSWORD=your_shared_password  # Shared password for upload endpoints

# Video Converter Tuning (optional)
VIDEO_UPLOAD_MAX_MB=0                # 0 disables Flask's request cap, default 2048
VIDEO_UPLOAD_CHUNK_MB=8              # Chunk size for streaming uploads
VIDEO_PROCESS_MAX_WORKERS=0          # 0 uses min(4, CPU cores)
VIDEO_PROCESS_MAX_RETRIES=1          # Retry attempts per failed task

# Cloudflare R2 Storage (optional)
R2_ACCOUNT_ID=your_r2_account_id
R2_ACCESS_KEY_ID=your_r2_access_key
R2_SECRET_ACCESS_KEY=your_r2_secret
R2_BUCKET_NAME=your_bucket_name
R2_PUBLIC_URL=https://your-bucket-url.com
```

6. **Run the Flask backend:**
```bash
python3 app.py --port 5000
```

### Frontend Setup (React)

1. **Navigate to the web directory:**
```bash
cd web
```

2. **Install Node dependencies:**
```bash
npm install
```

3. **Create `.env` file in web/ directory:**
```env
VITE_API_BASE_URL=http://localhost:5000
```

4. **Start the React development server:**
```bash
npm run dev
```

The React app will be available at `http://localhost:5173`

### Quick Start (Both Servers)

You can run both servers in separate terminals:

**Terminal 1 (Backend):**
```bash
python3 app.py --port 5000
```

**Terminal 2 (Frontend):**
```bash
cd web && npm run dev
```

Then access:
- **React UI (New)**: `http://localhost:5173`
- **Legacy UI**: `http://localhost:5000`

## 🌐 Usage

### Two UI Options
- **React UI (Recommended)**: Modern interface at `http://localhost:5173` (requires login)
- **Legacy UI**: Direct access at `http://localhost:5000` (no login required)

### Video Converter

**React UI:**
1. Sign in at `http://localhost:5173/login`
2. Navigate to Video Converter (`/app/video-converter`)
3. Drag and drop MP4/MOV files (up to 100MB each)
4. Select output formats (square, vertical, landscape)
5. Click "Convert Videos" and monitor real-time progress
6. Download individual files or batch ZIP

**Legacy UI:**
1. Visit `http://localhost:5000/video-converter`
2. Upload videos and select formats
3. Monitor per-file status (queued → running → success/fail)
4. Download completed files

### AdLocalizer

**React UI:**
1. Navigate to `http://localhost:5173/app/adlocalizer`
2. **Transcribe**: Upload media or paste text manually
3. **Translate**: Select target languages (ISO 639-1 codes: en, es, fr, ja, ko, etc.)
4. **Generate Voice**: Choose translation tone (faithful/creative)
5. **Mix**: Upload base video, add music, generate localized versions
6. Download individual renders or voiceover bundle

**Legacy UI:**
1. Visit `http://localhost:5000/adlocalizer`
2. Follow the step-by-step workflow:
   - Transcribe video audio
   - Translate to multiple languages
   - Generate voiceovers
   - Mix with video
3. Download localized videos

### Name Generator

**React UI:**
1. Navigate to `http://localhost:5173/app/name-generator`
2. Fill in creative metadata fields:
   - Creator name
   - Asset name
   - Feature tag (AIBG, ANIM, LOGO, etc.)
   - Language code (ISO 639-1)
   - Dimensions (PO, SQ, LS)
3. Copy generated filename or iteration helper
4. Use validator to check existing filenames
5. AI correction available for non-compliant names

### YouTube Tools

**Playlist Creator (Legacy UI):**
1. Visit `http://localhost:5000/youtube-playlist-batch`
2. Enter base tag (e.g., AIBG, ANIM)
3. Select languages or use default list
4. Preview and confirm playlist names
5. Authenticate with Google and create playlists

**Bulk Uploader (Legacy UI):**
1. Visit `http://localhost:5000/youtube-uploader`
2. Drag and drop video files
3. Filenames must contain `[TAG]` and `[lang]` for automatic parsing
4. Enter shared password
5. Preview playlist assignments
6. Upload videos and download results CSV

**CLI Tools:**
```bash
# Create playlists from command line
python make_playlists.py

# Upload videos from CSV
python youtube_uploader.py --csv youtube_uploads_sample.csv --run
```

## 🔧 Configuration

### Tools Configuration
Edit `tools_config.py` to:
- Add new tools
- Modify tool URLs
- Change tool icons and descriptions
- Enable/disable tools

### Video Processing
Edit `video_converter.py` to:
- Modify output formats
- Adjust quality settings
- Change processing parameters

#### Backend job tuning
The converter now exposes additional environment overrides:

- `VIDEO_UPLOAD_MAX_MB` – Total request cap; set to `0` to accept chunked uploads of any size (default 2048 MB).
- `VIDEO_UPLOAD_CHUNK_MB` – Chunk size used when streaming uploads to disk (minimum 0.25 MB).
- `VIDEO_PROCESS_MAX_WORKERS` – Hard limit on concurrent ffmpeg jobs; defaults to `min(4, CPU cores)`.
- `VIDEO_PROCESS_MAX_RETRIES` – Automatic retry attempts per failed conversion task.

These controls let you balance throughput and resource usage per deployment tier.

## 🎼 YouTube Playlist Batch Creator

The legacy playlist utility batch-creates unlisted YouTube playlists using the YouTube Data API v3. It is handy when you need standardized naming across multiple locales, for example:

```
[AIBG]_[fr]_01102025
[AIBG]_[ja]_01102025
[AIBG]_[de]_01102025
...
```

### ✨ Features
- Batch creation of unlisted playlists in one run
- Customizable naming pattern `[BASE_TAG]_[LANGUAGE]_[DATE]`
- Supports multiple base tags in a single batch
- Supports any number of languages (defaults to 18 common locales)
- One-time OAuth 2.0 login (opens a browser the first time)
- Token caching via `token.json` so you authenticate only once
- Graceful retry logic for API rate limits
- Preview and confirmation step before playlist creation in the web UI

### 🚀 Quick Start

1. **Prerequisites**
   - Python 3.9 or newer
   - Install dependencies:

```bash
pip install google-auth-oauthlib google-api-python-client
```

   - Enable the YouTube Data API v3 in Google Cloud Console
   - Create an OAuth client ID (Desktop App) and copy the downloaded JSON as `client_secret.json` into the project folder

2. **Run the batch creator**

   ```bash
   python make_playlists.py
   ```

   - The first run opens a browser where you choose the YouTube account to manage
   - When prompted for base tags, enter a comma-separated list to generate multiple tags in one run (e.g. `AIBG,ANIM`)
   - When prompted for languages, press Enter to use the default list or type a custom comma-separated list (e.g. `fr` for a single test playlist)
   - After authentication the playlists are created automatically
   - Prefer the legacy web tools? Use `/youtube-playlist` for ID extraction and `/youtube-playlist-batch` for the batch creator UI once the Flask app is running

### 📂 Example Output

With the base tag `AIBG`, date `01102025`, and the default language list (`fr`, `ja`, `en`, ...), the tool generates:

```
[AIBG]_[fr]_01102025
[AIBG]_[ja]_01102025
[AIBG]_[en]_01102025
...
```

All playlists default to the unlisted privacy setting.

### 🛠️ Roadmap

- **v1 — MVP (current)**
  - Batch creation from a predefined language list
  - Simple `[TAG]_[LANG]_[DATE]` format
  - Unlisted privacy by default
  - Retry on rate limits
- **v2 — Configurable Inputs**
  - CLI arguments such as `--tag AIBG --date 01102025 --langs fr,ja,en`
  - Config file (`config.json` or `.env`) to define language sets and base naming
- **v3 — Enhanced Usability**
  - Read playlist names from a CSV file
  - Export playlist ID plus name to CSV for tracking
  - Optional per-playlist descriptions
- **v4 — Web App Integration**
  - Convert into a lightweight Flask or FastAPI app
  - OAuth client ID for the web application flow
  - Dashboard: input tag/date, pick languages, click "Create Playlists"
- **v5 — Scaling and Team Use**
  - Multi-user support (each user authorizes their own YouTube account)
  - Persist refresh tokens in a data store
  - Error logging and monitoring for quota limits

### ⚠️ Notes
- Authenticate with the Google account that owns the target YouTube channel
- If you manage multiple channels or brand accounts, pick the correct one during OAuth consent
- Delete `token.json` if you need to sign in with a different account

### 📦 Upload Preview (WIP)

`youtube_uploader.py` provides a preview-only workflow for upcoming bulk video uploads:

```bash
python youtube_uploader.py --csv youtube_uploads_sample.csv
```

- CSV columns: `file_path` (local path to the video) and `playlist_hint` (existing legacy filename containing `[TAG]` and `[lang]`).
- The script resolves the target playlist name, flags URLs vs. local files, and prints a summary.
- Use `--date DDMMYYYY` to override the fallback date when the hint omits one.
- Reminder: actual video uploads will require re-authorizing with the `youtube.upload` scope; this script is a staging step for that flow.
- Add `--run` to perform uploads immediately. The CLI will:
  - Download remote sources into a temp folder before upload.
  - Set each video to `unlisted`, keep the filename as the YouTube title, and mark it as not made for kids.
  - Ensure the destination playlist exists (creating it when missing) and append the uploaded video.
  - Emit a timestamped results CSV summarizing successes, skips, and failures.

### 🖥️ Web Drag & Drop Uploader

- Visit `/youtube-uploader` (legacy UI) to drag and drop local video files.
- Filenames should still contain `[TAG]` and `[lang]`; the UI previews the inferred playlist before upload.
- The backend reuses the same pipeline as the CLI, including resumable uploads, playlist creation, and results CSV downloads.
- Reports are stored under `uploads/youtube_reports/` and can be retrieved directly from the interface.

## 🐛 Troubleshooting

### Common Issues

1. **Drag and drop not working in AdLocalizer**
   - ✅ **Fixed**: Enhanced JavaScript event handling
   - Make sure you're using a modern browser

2. **500 Internal Server Error**
   - ✅ **Fixed**: Proper module separation and error handling
   - Check that all dependencies are installed
   - Verify environment variables are set

3. **Video processing fails**
   - Ensure ffmpeg is installed
   - Check video file format (MP4, MOV supported)
   - Verify sufficient disk space

4. **API errors in AdLocalizer**
   - Check OpenAI and ElevenLabs API keys
   - Verify API quotas and limits
   - Check network connectivity

## 📝 API Endpoints

### Authentication
- `GET /api/auth/google/login` - Initiate Google OAuth flow
- `GET /api/auth/google/callback` - Handle OAuth callback
- `POST /api/auth/logout` - Logout and clear session
- `GET /api/me` - Get current user info (returns 401 if not authenticated)

### Video Converter
- `POST /api/upload` - Upload videos for conversion (streamed writes, returns `job_id`)
- `GET /api/status/<job_id>` - Get conversion status with per-task metrics
- `GET /api/download/<job_id>/<filename>` - Download converted file
- `GET /api/download_zip/<job_id>` - Download all successful files as ZIP

### AdLocalizer
- `POST /api/transcribe` - Transcribe video audio with Whisper
- `POST /api/translate` - Translate text with GPT-4
- `POST /api/generate-voice` - Generate voiceovers with ElevenLabs
- `POST /api/upload-video` - Upload video for mixing
- `POST /api/mix-audio` - Mix audio with video using FFmpeg
- `GET /api/audio/<filepath>` - Serve generated audio files
- `GET /api/video/<filepath>` - Serve processed video files

### YouTube Tools
- `POST /api/youtube/playlists/create` - Create YouTube playlists
- `POST /api/youtube/upload` - Upload videos to YouTube with playlist assignment
- `GET /api/youtube/reports/<filename>` - Download upload results CSV

### Name Generator
- `POST /api/name/generate` - Generate creative filename
- `POST /api/name/validate` - Validate filename format
- `POST /api/name/correct` - AI-powered filename correction

### Utility
- `GET /health` - Health check endpoint
- `GET /language-mapping` - View ISO 639-1 language code reference

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following the existing code style
4. Test thoroughly (both React and Flask components)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 🗺️ Development Roadmap

See [roadmap.md](roadmap.md) for detailed implementation plans and milestones.

**Current Focus:**
- ✅ Google OAuth authentication
- ✅ React app shell with protected routes
- ✅ ISO 639-1 language standardization
- 🔄 Progressive feature migration from Jinja to React
- 📋 Enhanced error handling and observability
- 📋 Rate limiting and CSRF protection

## 📄 Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide for Render.com and other platforms
- [roadmap.md](roadmap.md) - Development roadmap and architecture plans
- [web/README.md](web/README.md) - React frontend documentation

## 🆕 Recent Updates

**v1.1 (October 2025)**
- ✅ Implemented Google OAuth 2.0 authentication
- ✅ Built React app shell with protected routes
- ✅ Migrated Name Generator to React
- ✅ ISO 639-1 language code standardization across all tools
- ✅ Enhanced video converter with streaming uploads
- ✅ YouTube bulk uploader with playlist automation

**Previous Updates**
- ✅ Fixed drag and drop functionality in AdLocalizer
- ✅ Restructured codebase for better maintainability
- ✅ Improved error handling and logging
- ✅ Modular architecture with separation of concerns

## 📧 Support

For issues, questions, or feature requests, please open an issue on GitHub.

---

**Made with ❤️ by Jiali**  
*Photoroom Creative Tools Platform*
