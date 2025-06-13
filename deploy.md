# DigitalOcean App Platform Deployment Guide

## Prerequisites
1. DigitalOcean account
2. GitHub repository with your code
3. Git repository connected to DigitalOcean

## Deployment Steps

### 1. Push your code to GitHub
```bash
git add .
git commit -m "Setup for DigitalOcean deployment"
git push origin main
```

### 2. Create App on DigitalOcean
1. Go to DigitalOcean App Platform: https://cloud.digitalocean.com/apps
2. Click "Create App"
3. Choose "GitHub" as source
4. Select your repository: `NewVideoFormatConverter`
5. Choose branch: `main`
6. DigitalOcean will auto-detect the app.yaml file

### 3. Configure App Settings
- **App Name**: video-format-converter
- **Region**: Choose closest to your users
- **Plan**: Professional ($12/month recommended for video processing)
- **Instance Size**: Professional-XS (2 GB RAM, 1 vCPU)

### 4. Environment Variables (Auto-configured via app.yaml)
- `PORT`: 8080
- `FLASK_ENV`: production
- `FFMPEG_BINARY`: /usr/bin/ffmpeg
- `FFPROBE_BINARY`: /usr/bin/ffprobe

### 5. Deploy
Click "Create Resources" and wait for deployment to complete.

## Features Enabled
- ✅ FFmpeg/FFprobe installed automatically
- ✅ Auto-scaling based on traffic
- ✅ HTTPS enabled by default
- ✅ Global CDN
- ✅ Automatic deployments on git push
- ✅ Health checks configured
- ✅ Professional-grade infrastructure

## App URL
Your app will be available at: `https://video-format-converter-xxxxx.ondigitalocean.app`

## Monitoring
- View logs in DigitalOcean dashboard
- Monitor performance metrics
- Set up alerts for downtime

## Cost Estimate
- Professional-XS plan: ~$12/month
- Bandwidth: $0.01/GB
- Estimated total: $15-25/month for moderate usage 