#!/bin/bash
# Fast build script for Render.com

echo "🚀 Starting optimized build..."

# Install core dependencies first (fast)
echo "📦 Installing core dependencies..."
pip install --upgrade pip
pip install -r requirements-core.txt

# Only install AI dependencies if needed (optional)
if [ "$INSTALL_AI_FEATURES" = "true" ]; then
    echo "🤖 Installing AI dependencies (this will take longer)..."
    pip install -r requirements-ai.txt
    
    # Download models if needed
    if [ -f "setup_models.py" ]; then
        echo "📥 Downloading AI models..."
        python setup_models.py
    fi
else
    echo "⏩ Skipping AI dependencies (set INSTALL_AI_FEATURES=true to enable)"
fi

echo "✅ Build complete!"
