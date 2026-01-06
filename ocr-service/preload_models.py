"""
Model Preloading Script
Runs during Docker build to cache Whisper model in the image
This reduces cold start time from ~120s to ~5s
"""
import whisper
import sys

def preload_whisper_model(model_size: str = "base"):
    """
    Download and cache Whisper model
    
    Args:
        model_size: Model size (tiny, base, small, medium, large)
    """
    print(f"🔄 Downloading Whisper '{model_size}' model...")
    print(f"   This will be cached in the Docker image to speed up container startup")
    
    try:
        # Download model (will be cached)
        model = whisper.load_model(model_size)
        print(f"✅ Whisper '{model_size}' model downloaded successfully")
        print(f"   Model size: ~140MB")
        print(f"   Container startup will now be ~5 seconds instead of ~120 seconds")
        return True
    except Exception as e:
        print(f"❌ Failed to download model: {e}")
        return False

if __name__ == "__main__":
    model_size = sys.argv[1] if len(sys.argv) > 1 else "base"
    success = preload_whisper_model(model_size)
    sys.exit(0 if success else 1)
