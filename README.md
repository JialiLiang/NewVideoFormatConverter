# 🎥 Photoroom Video Format Converter

A comprehensive video processing toolkit with multiple tools for video conversion, localization, and more.

## 🚀 Features

### Video Converter
- Convert videos to different formats (square, landscape, vertical)
- Smart dynamic adjustment for any input aspect ratio
- High-quality output with optimized settings
- Progressive results display
- Background processing with real-time progress

### AdLocalizer (AI-Powered Video Localization)
- **Fixed**: Drag and drop video upload functionality
- AI-powered transcription using OpenAI Whisper
- Multi-language translation with OpenAI GPT-4
- Voice generation with ElevenLabs
- Audio mixing with video
- Support for 17+ languages

### Additional Tools (Work in Progress)
- Static Generator
- Hook Remixer
- Montage Maker

## 📁 New File Structure

The application has been restructured for better organization:

```
NewVideoFormatConverter/
├── app.py                    # Main application entry point
├── video_converter_app.py    # Video converter functionality
├── adlocalizer_app.py        # AdLocalizer functionality
├── video_converter.py        # Video processing functions
├── tools_config.py           # Tool configuration
├── templates/
│   ├── index.html           # Video converter interface
│   ├── adlocalizer.html     # AdLocalizer interface
│   └── wip_tool.html        # Work-in-progress tool template
├── requirements.txt          # Python dependencies
└── README.md                # This file
```

## 🔧 Recent Fixes

### 1. Fixed Drag and Drop in AdLocalizer
- **Issue**: Drag and drop wasn't working properly in AdLocalizer
- **Fix**: Enhanced JavaScript event handling with proper event propagation control
- **Changes**: Added `dragenter` events, improved `dragleave` logic, and manual event triggering

### 2. Proper File Naming and Structure
- **Issue**: Monolithic `app.py` was confusing and hard to maintain
- **Fix**: Split into separate modules:
  - `app.py` - Main entry point and routing
  - `video_converter_app.py` - Video conversion functionality
  - `adlocalizer_app.py` - AdLocalizer functionality
  - `video_converter.py` - Core video processing functions

### 3. Fixed 500 Internal Server Error
- **Issue**: Various import and routing issues causing server errors
- **Fix**: Proper module separation, error handling, and route registration
- **Changes**: Clean imports, better error handling, and modular structure

## 🛠️ Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd NewVideoFormatConverter
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables (create `.env` file):
```env
OPENAI_API_KEY=your_openai_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
SECRET_KEY=your_secret_key
```

4. Run the application:
```bash
python3 app.py --port 8000
```

## 🌐 Usage

### Video Converter
1. Visit `http://localhost:8000/video-converter`
2. Drag and drop or select video files
3. Choose output formats (square, landscape, vertical)
4. Click "Convert Videos" and wait for processing
5. Download individual files or all as ZIP

### AdLocalizer
1. Visit `http://localhost:8000/adlocalizer`
2. **Drag and drop** videos for transcription (now working!)
3. Enter text to translate or use transcribed text
4. Select target languages
5. Choose translation mode (faithful or creative)
6. Generate voiceovers
7. Upload video for mixing
8. Download localized videos

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

### Video Converter
- `POST /upload` - Upload videos for conversion
- `GET /status/<job_id>` - Get conversion status
- `GET /download/<job_id>/<filename>` - Download converted file
- `GET /download_zip/<job_id>` - Download all files as ZIP

### AdLocalizer
- `POST /api/transcribe` - Transcribe video audio
- `POST /api/translate` - Translate text
- `POST /api/generate-voice` - Generate voiceovers
- `POST /api/upload-video` - Upload video for mixing
- `POST /api/mix-audio` - Mix audio with video
- `GET /audio/<filepath>` - Serve audio files
- `GET /video/<filepath>` - Serve video files

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

Made with ❤️ by Jiali

## 🆕 Recent Updates

- ✅ Fixed drag and drop functionality in AdLocalizer
- ✅ Restructured codebase for better maintainability
- ✅ Fixed 500 Internal Server Error issues
- ✅ Improved error handling and logging
- ✅ Enhanced user experience with better feedback