#!/bin/bash
set -e

echo "🤖 Smart Render.com Build System"
echo "================================"

# Check environment variables
ENABLE_AI=${ENABLE_AI:-false}  # Default to FAST mode
AUTO_DETECT=${AUTO_DETECT:-true}

echo "🔧 Configuration:"
echo "   AUTO_DETECT: $AUTO_DETECT"
echo "   ENABLE_AI: $ENABLE_AI"

# Auto-detection logic (simplified and more reliable)
if [ "$AUTO_DETECT" = "true" ]; then
    echo "🔍 Auto-detecting deployment mode..."
    
    # Simple detection: if AI files exist, we might need them
    if [ "$ENABLE_AI" = "false" ] && [ -f "adlocalizer_app.py" ] && [ -s "adlocalizer_app.py" ]; then
        echo "   📄 AdLocalizer found, but ENABLE_AI=false - using FAST MODE anyway"
        echo "   💡 Set ENABLE_AI=true in Render dashboard for full features"
    fi
fi

# Show selected mode
if [ "$ENABLE_AI" = "true" ]; then
    echo "🧠 FULL MODE SELECTED"
    echo "   ⏱️  Expected build time: 3-5 minutes"
    echo "   🎯 Includes: Video processing + AI features"
else
    echo "⚡ FAST MODE SELECTED"
    echo "   🚀 Expected build time: 1-2 minutes"
    echo "   🎯 Includes: Video processing only"
fi

echo ""
echo "📦 Installing core dependencies (always fast)..."
pip install --no-cache-dir --upgrade pip
pip install --no-cache-dir -r requirements-base.txt

# Conditionally install AI dependencies
if [ "$ENABLE_AI" = "true" ]; then
    echo "🤖 Installing AI dependencies..."
    echo "   - OpenAI, ElevenLabs APIs"
    echo "   - PyTorch, Demucs models"
    echo "   - Audio processing libraries"
    pip install --no-cache-dir -r requirements-ai.txt
else
    echo "⚡ Skipping AI dependencies (fast mode)"
    echo "   - AdLocalizer disabled"
    echo "   - Vocal removal disabled"
    echo "   - Core video processing enabled"
fi

# Install any remaining dependencies
echo "🔄 Installing additional dependencies..."
pip install --no-cache-dir -r requirements.txt || true

# Create necessary directories
mkdir -p uploads temp_files

echo ""
echo "✅ Build complete!"
echo "🎯 Mode: $([ "$ENABLE_AI" = "true" ] && echo "FULL" || echo "FAST")"
echo "🚀 Ready to start application!"
