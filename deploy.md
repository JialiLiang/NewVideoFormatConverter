# Render.com Deployment Guide

## Why Render.com is Perfect for This App
- ✅ **Native FFmpeg Support**: FFmpeg and FFprobe are pre-installed
- ✅ **Simple Pricing**: $7/month for Starter plan (512MB RAM)
- ✅ **Easy Signup**: No complex payment setup
- ✅ **Reliable**: Used by thousands of developers
- ✅ **Free Tier**: 750 hours/month for testing

## Prerequisites
1. GitHub account
2. Render.com account (free signup)

## Deployment Steps

### 1. Push your code to GitHub
```bash
git add .
git commit -m "Setup for Render.com deployment"
git push origin main
```

### 2. Create Web Service on Render
1. Go to: https://render.com/
2. Click "Get Started for Free"
3. Sign up with GitHub
4. Click "New +" → "Web Service"
5. Connect your GitHub repository: `NewVideoFormatConverter`
6. Choose branch: `main`

### 3. Configure Service Settings
- **Name**: video-format-converter
- **Environment**: Python 3
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python app.py`
- **Plan**: Starter ($7/month) or Free (750 hours/month)

### 4. Environment Variables (Optional)
- `FLASK_ENV`: production
- `PORT`: 10000 (auto-configured)

### 5. Deploy
Click "Create Web Service" and wait for deployment.

## Key Advantages
- ✅ **FFmpeg Works Out of the Box**: No configuration needed
- ✅ **Automatic HTTPS**: SSL certificates included
- ✅ **Auto-deploys**: Updates on every git push
- ✅ **Health Checks**: Built-in monitoring
- ✅ **Simple Pricing**: No hidden costs
- ✅ **Great Support**: Active community and docs

## App URL
Your app will be available at: `https://video-format-converter-xxxx.onrender.com`

## Pricing
- **Free Plan**: 750 hours/month (sleeps after 15 min of inactivity)
- **Starter Plan**: $7/month (always on, 512MB RAM)
- **Standard Plan**: $25/month (1GB RAM, better performance)

## Perfect for Video Processing
Render's native FFmpeg support means no path issues, no binary detection problems, and reliable video processing. This is exactly what you need! 