#!/bin/bash
set -e

echo "🤖 Starting intelligent auto-optimized build..."

# Auto-detect if AI features are needed based on changed files
AUTO_DETECT=${AUTO_DETECT:-true}
ENABLE_AI=${ENABLE_AI:-true}

if [ "$AUTO_DETECT" = "true" ]; then
    echo "🔍 Auto-detecting required features..."
    
    # Get list of files that exist (since we can't reliably get git diff in Render)
    AI_NEEDED=false
    
    # Check if AI-related files exist and seem to be recently modified
    if [ -f "adlocalizer_app.py" ] && [ -s "adlocalizer_app.py" ]; then
        echo "   📄 AdLocalizer app found"
        AI_NEEDED=true
    fi
    
    if [ -f "vocal_models_config.py" ] && [ -s "vocal_models_config.py" ]; then
        echo "   🎵 Vocal models config found"
        AI_NEEDED=true
    fi
    
    if [ -f "setup_models.py" ] && [ -s "setup_models.py" ]; then
        echo "   🔧 Model setup script found"
        AI_NEEDED=true
    fi
    
    # Check if AI templates exist
    if [ -f "templates/adlocalizer.html" ]; then
        echo "   🎨 AI templates found"
        AI_NEEDED=true
    fi
    
    # Override ENABLE_AI based on detection
    if [ "$AI_NEEDED" = "true" ]; then
        ENABLE_AI=true
        echo "   🧠 AI features detected - FULL MODE"
        echo "   ⏱️  Build time: ~3-5 minutes"
    else
        ENABLE_AI=false
        echo "   ⚡ Core features only - FAST MODE"
        echo "   🚀 Build time: ~1-2 minutes"
    fi
else
    echo "🔧 Using manual ENABLE_AI setting: $ENABLE_AI"
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
