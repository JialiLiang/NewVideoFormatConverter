# Video Format Converter

A Streamlit application for converting videos to different formats for various platforms.

## Features

- Convert videos to square format (1080x1080) for Google Ads
- Create square videos with blurred background (1080x1080) that maintain original aspect ratio
- Create landscape videos (1920x1080) with blurred background for YouTube

## Installation

1. Clone this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Ensure ffmpeg is installed on your system:

- **Linux**: `sudo apt-get install ffmpeg`
- **macOS**: `brew install ffmpeg`
- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH

## Deployment

### Local Development

```bash
streamlit run video_converter.py
```

### Streamlit Cloud Deployment

When deploying to Streamlit Cloud, the app will automatically install ffmpeg from the packages.txt file.

### Troubleshooting

If you encounter `FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'`, ensure that:

1. FFmpeg is properly installed on your system
2. FFmpeg is in your system PATH
3. For Streamlit Cloud deployment, make sure the packages.txt file contains `ffmpeg`

## Dependencies

- streamlit==1.32.0 - Web app framework
- moviepy==1.0.3 - Video editing library
- Pillow==10.2.0 - Image processing library
- numpy==1.26.4 - Numerical computing library
- ffmpeg-python==0.2.0 - Python bindings for FFmpeg
- imageio-ffmpeg==0.4.8 - FFmpeg bindings for imageio

## License

MIT 