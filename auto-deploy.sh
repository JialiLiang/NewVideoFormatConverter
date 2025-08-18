#!/bin/bash
set -e

echo "🤖 Auto-detecting optimal deployment mode..."

# Get list of changed files in the last commit
CHANGED_FILES=$(git diff --name-only HEAD~1 HEAD 2>/dev/null || git ls-files)

# Files that require AI features
AI_REQUIRED_FILES=(
    "adlocalizer_app.py"
    "setup_models.py"
    "vocal_models_config.py"
    "requirements-ai.txt"
)

# Files that are AI-related in templates
AI_TEMPLATE_FILES=(
    "templates/adlocalizer.html"
    "templates/vocal_removal_test.html"
)

# Check if any AI-related files were changed
NEEDS_AI=false

echo "📁 Analyzing changed files:"
for file in $CHANGED_FILES; do
    echo "  - $file"
    
    # Check if it's an AI-required file
    for ai_file in "${AI_REQUIRED_FILES[@]}"; do
        if [[ "$file" == *"$ai_file"* ]]; then
            echo "    ⚡ AI feature detected!"
            NEEDS_AI=true
            break
        fi
    done
    
    # Check if it's an AI template file
    for ai_template in "${AI_TEMPLATE_FILES[@]}"; do
        if [[ "$file" == *"$ai_template"* ]]; then
            echo "    🎨 AI template detected!"
            NEEDS_AI=true
            break
        fi
    done
done

# Decide deployment mode
if [ "$NEEDS_AI" = true ]; then
    echo ""
    echo "🧠 AI features detected - using FULL MODE"
    echo "⏱️  Expected deploy time: 3-5 minutes"
    export ENABLE_AI=true
    DEPLOY_MODE="full"
else
    echo ""
    echo "⚡ Core changes only - using FAST MODE"
    echo "🚀 Expected deploy time: 1-2 minutes"
    export ENABLE_AI=false
    DEPLOY_MODE="fast"
fi

# Update render.yaml with the appropriate mode
if [ "$DEPLOY_MODE" = "fast" ]; then
    echo "📝 Configuring for fast deployment..."
    # Use the optimized render.yaml but with ENABLE_AI=false
    sed -i.bak 's/value: true  # Set to '\''false'\'' for 5x faster deployments/value: false  # Auto-set for fast deployment/' render.yaml
else
    echo "📝 Configuring for full deployment..."
    # Use the optimized render.yaml with ENABLE_AI=true
    sed -i.bak 's/value: false  # Auto-set for fast deployment/value: true  # Auto-set for full deployment/' render.yaml
fi

echo ""
echo "✅ Auto-configuration complete!"
echo "🎯 Mode: $DEPLOY_MODE"
echo "🔧 ENABLE_AI: $ENABLE_AI"
echo ""
echo "Ready to deploy! Run: git add . && git commit -m 'Auto-optimized deploy' && git push"
