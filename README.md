# Video Format Converter

A modern Flask web application for converting videos to different formats with smart processing and real-time downloads.

## ✨ Features

* **Square Format (1080x1080)** - Pure crop to square
* **Square with Blur (1080x1080)** - Original video centered with blurred background
* **Landscape with Blur (1920x1080)** - Original video centered with blurred sides
* **Vertical with Blur (1080x1920)** - Original video centered with blurred top/bottom
* **Smart Processing** - Automatically handles any input video orientation
* **Progressive Downloads** - Download videos as soon as they're ready
* **Batch Processing** - Convert multiple videos at once

## 🚀 Live Demo

Visit the live app: [Railway Deployment](https://newvideoformatconverter.up.railway.app)

## 💻 Installation

1. Clone this repository:
```bash
git clone https://github.com/JialiLiang/NewVideoFormatConverter.git
cd NewVideoFormatConverter
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Install ffmpeg:
* **Linux**: `sudo apt-get install ffmpeg`
* **macOS**: `brew install ffmpeg`
* **Windows**: Download from ffmpeg.org and add to PATH

## 🏃‍♂️ Running Locally

```bash
python app.py
```
Then open http://localhost:8000 in your browser.

## 🌟 Key Features

* **Smart Video Processing**
  - Maintains aspect ratio for all formats
  - Adds beautiful blur effects where needed
  - Works with any input video orientation

* **Modern UI**
  - Real-time progress updates
  - Progressive downloads
  - Drag-and-drop upload
  - Mobile-friendly design

* **Robust Processing**
  - Processes one video at a time to prevent resource overload
  - Automatic cleanup of temporary files
  - Error handling and recovery

## 🛠️ Dependencies

* Flask==2.3.3 - Web framework
* moviepy==1.0.3 - Video processing
* Pillow==10.2.0 - Image processing
* numpy==1.26.4 - Numerical computing
* ffmpeg-python==0.2.0 - FFmpeg integration
* imageio-ffmpeg==0.4.8 - FFmpeg support

## 📝 License

MIT 