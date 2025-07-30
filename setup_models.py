#!/usr/bin/env python3
"""
Setup script to pre-download AI models for vocal removal.
This should be run during deployment/installation.
"""

import sys
import os
from pathlib import Path

def download_demucs_models():
    """Download DEMUCS models"""
    print("🎵 Downloading DEMUCS models...")
    
    try:
        import torch
        from demucs.pretrained import get_model
        
        models_to_download = ['htdemucs_ft']  # Only the high quality DEMUCS model
        
        for model_name in models_to_download:
            print(f"  📥 Downloading {model_name}...")
            try:
                model = get_model(model_name)
                print(f"  ✅ {model_name} downloaded successfully")
            except Exception as e:
                print(f"  ❌ Failed to download {model_name}: {e}")
                return False
                
        print("✅ All DEMUCS models downloaded successfully")
        return True
        
    except ImportError:
        print("❌ DEMUCS not installed. Please install it first: pip install demucs")
        return False
    except Exception as e:
        print(f"❌ Error downloading DEMUCS models: {e}")
        return False

def check_replicate_setup():
    """Check Replicate API setup"""
    print("🔊 Checking Replicate API setup...")
    
    try:
        import replicate
        
        # Check if API token is set
        api_token = os.environ.get('REPLICATE_API_TOKEN')
        if not api_token:
            print("  ⚠️ REPLICATE_API_TOKEN not set")
            print("   Set it with: export REPLICATE_API_TOKEN=your_token_here")
            print("   Get your token from: https://replicate.com/account/api-tokens")
            return False
        
        print("  ✅ Replicate API token is configured")
        print("  📝 Model: erickluis00/all-in-one-audio")
        print("  💰 Cost: ~$0.13 per run (7 runs per $1)")
        print("  ⏱️ Speed: ~130 seconds on Nvidia L40S GPU")
        
        return True
        
    except ImportError:
        print("  ❌ replicate not installed")
        print("   Install with: pip install replicate")
        return False
    except Exception as e:
        print(f"  ❌ Error checking Replicate setup: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Setting up AI models for vocal removal...")
    print("This may take a few minutes and download ~300MB of models.")
    print()
    
    success = True
    
    # Download DEMUCS models (required)
    if not download_demucs_models():
        success = False
    
    print()
    
    # Check Replicate API setup (optional)
    if not check_replicate_setup():
        print("  ⚠️ Replicate API not configured - only DEMUCS will be available")
        print("  💡 To enable cloud-based vocal removal, set REPLICATE_API_TOKEN")
    
    print()
    
    if success:
        print("🎉 Model setup completed successfully!")
        print("The vocal removal feature is now ready to use.")
    else:
        print("❌ Model setup failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()