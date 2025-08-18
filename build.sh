#!/bin/bash
set -e

echo "🚀 Starting optimized Render.com build..."

# Check if this is a full build or incremental
FULL_BUILD=${FULL_BUILD:-false}
ENABLE_AI=${ENABLE_AI:-true}

echo "📦 Installing core dependencies (fast)..."
pip install --no-cache-dir --upgrade pip
pip install --no-cache-dir -r requirements-base.txt

# Only install AI dependencies if needed (can be disabled for faster deploys)
if [ "$ENABLE_AI" = "true" ]; then
    echo "🤖 Installing AI dependencies (slow - can be disabled)..."
    pip install --no-cache-dir -r requirements-ai.txt
else
    echo "⚡ Skipping AI dependencies for faster deployment"
fi

# Install any remaining dependencies from main requirements.txt that aren't covered
echo "🔄 Installing any additional dependencies..."
pip install --no-cache-dir -r requirements.txt || true

echo "✅ Build complete!"
echo "💡 Tip: Set ENABLE_AI=false for 5x faster deployments when AI features aren't needed"
