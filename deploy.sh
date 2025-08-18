#!/bin/bash
set -e

echo "🚀 Smart Deployment Script"
echo "=========================="

# Check if there are changes to commit
if [[ -n $(git status --porcelain) ]]; then
    echo "📝 Changes detected, preparing commit..."
    
    # Get commit message from user or use default
    if [ -z "$1" ]; then
        read -p "💬 Enter commit message (or press Enter for auto-message): " COMMIT_MSG
        if [ -z "$COMMIT_MSG" ]; then
            COMMIT_MSG="Auto-deploy: $(date '+%Y-%m-%d %H:%M')"
        fi
    else
        COMMIT_MSG="$1"
    fi
    
    # Add and commit changes
    git add .
    git commit -m "$COMMIT_MSG"
    
    echo "✅ Changes committed: $COMMIT_MSG"
else
    echo "ℹ️  No changes to commit"
fi

# Auto-detect deployment mode
echo ""
echo "🤖 Auto-detecting optimal deployment mode..."

# Get list of changed files in the last commit
CHANGED_FILES=$(git diff --name-only HEAD~1 HEAD 2>/dev/null || echo "")

if [ -z "$CHANGED_FILES" ]; then
    echo "   📁 Using all files for detection"
    CHANGED_FILES=$(git ls-files)
fi

# Files that require AI features
AI_NEEDED=false

for file in $CHANGED_FILES; do
    case $file in
        *adlocalizer* | *vocal* | *setup_models* | *requirements-ai*)
            echo "   🧠 AI feature detected: $file"
            AI_NEEDED=true
            break
            ;;
    esac
done

# Show prediction
if [ "$AI_NEEDED" = "true" ]; then
    echo "   📊 Prediction: FULL MODE (3-5 minutes)"
    echo "   🎯 Includes: Video processing + AI features"
else
    echo "   📊 Prediction: FAST MODE (1-2 minutes)"  
    echo "   🎯 Includes: Video processing only"
fi

echo ""
echo "🌐 Pushing to GitHub..."
git push origin main

echo ""
echo "✅ Deployment initiated!"
echo "🔗 Check your Render.com dashboard for build progress"
echo "📊 The build system will automatically choose the optimal mode"
echo ""
echo "💡 Pro tip: The build logs will show which mode was selected"
