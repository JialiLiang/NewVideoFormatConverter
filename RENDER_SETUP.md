# 🚀 Render.com Setup Guide - Fast Deployments

## ⚠️ IMPORTANT: Manual Dashboard Configuration Required

**The render.yaml file may be ignored by Render.com if your service was created before it existed.**

### 🔧 **Manual Setup in Render.com Dashboard:**

1. **Go to your Render.com dashboard**
2. **Click on your service** (video-format-converter)
3. **Go to "Settings" tab**
4. **Update these fields:**

#### **Build & Deploy Settings:**
```
Build Command: chmod +x build.sh && ./build.sh
Start Command: gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 300 app:app
```

#### **Environment Variables:**
```
AUTO_DETECT = true
ENABLE_AI = false    # ⚡ FAST MODE (1-2 min builds)
PORT = 10000
FLASK_ENV = production
PYTHONUNBUFFERED = 1
PIP_NO_CACHE_DIR = 1
```

5. **Click "Save Changes"**
6. **Trigger a manual deploy**

## 🎯 **Deployment Modes:**

### **⚡ Fast Mode (Recommended for most changes)**
- **Set:** `ENABLE_AI = false`
- **Build time:** 1-2 minutes
- **Includes:** Video processing, uploads, downloads
- **Excludes:** AI translation, vocal removal

### **🧠 Full Mode (Only when AI features needed)**
- **Set:** `ENABLE_AI = true` 
- **Build time:** 3-5 minutes
- **Includes:** Everything

## 🔍 **Troubleshooting:**

### **If builds are still slow:**
1. Check Render.com dashboard build command
2. Verify environment variables are set
3. Look for "Smart Render.com Build System" in build logs
4. If you see "pip install -r requirements.txt", the dashboard settings aren't applied

### **Build Log Indicators:**
**✅ Working (Fast Mode):**
```
🤖 Smart Render.com Build System
⚡ FAST MODE SELECTED
🚀 Expected build time: 1-2 minutes
📦 Installing core dependencies...
```

**❌ Not Working (Old System):**
```
Running build command 'pip install -r requirements.txt'
Collecting torch>=2.0.0...
```

## 🎉 **Expected Results:**
- **Fast Mode:** 1-2 minute deployments
- **Full Mode:** 3-5 minute deployments  
- **Old System:** 8-10 minute deployments

Your deployments should be **5x faster** once properly configured!
