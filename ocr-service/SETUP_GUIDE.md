# Setup Guide for Junior Developers

This guide will help you set up the OCR & Speech-to-Text API from scratch.

## Step 1: Install System Requirements

### 1.1 Install Python 3.10 or higher
Download from: https://www.python.org/downloads/

Verify installation:
```powershell
python --version
```

### 1.2 Install FFmpeg (Required for Audio Processing)
```powershell
# Using winget (easiest method)
winget install --id=Gyan.FFmpeg -e

# Restart PowerShell after installation
# Verify
ffmpeg -version
```

**If you get an error**, download manually from: https://ffmpeg.org/download.html and add to PATH

### 1.3 Install Tesseract OCR (Required for Image Processing)
1. Download installer: https://github.com/UB-Mannheim/tesseract/wiki
2. Run installer and install to: `C:\Program Files\Tesseract-OCR\`
3. Verify:
```powershell
tesseract --version
```

## Step 2: Clone and Setup Project

```powershell
# Navigate to project directory
cd I:\path\to\fastapi_ocr_stt

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate

# Install Python dependencies (takes 2-3 minutes)
pip install -r requirements.txt
```

## Step 3: Test Installation

Run this quick test to verify everything is installed:

```powershell
# Test FFmpeg
ffmpeg -version

# Test Tesseract
tesseract --version

# Test Python packages
python -c "import whisper; import pytesseract; print('✓ All packages installed')"
```

## Step 4: Start the Server

```powershell
# Make sure you're in project directory and venv is activated
cd I:\path\to\fastapi_ocr_stt
.\venv\Scripts\activate

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

## Step 5: Test the API

1. Open browser: http://localhost:8000/docs
2. You'll see interactive API documentation
3. Try the endpoints:
   - **POST /api/v1/ocr/extract** - Upload an image to extract text
   - **POST /api/v1/stt/transcribe** - Upload an audio file to transcribe

## Optional: Setup Google Vision API (Better Handwriting Recognition)

If you need better handwriting recognition, see [GOOGLE_VISION_SETUP.md](GOOGLE_VISION_SETUP.md)

**Without Google Vision**: Uses Tesseract (good for printed text)  
**With Google Vision**: 95%+ accuracy on handwritten text

## Common Issues & Solutions

### Issue: "FFmpeg not found"
**Solution**: 
```powershell
# Reload PATH in current PowerShell session
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# Verify
ffmpeg -version

# If still fails, restart computer
```

### Issue: "Tesseract not found"
**Solution**: 
- Reinstall Tesseract to: `C:\Program Files\Tesseract-OCR\`
- Or update path in `app/services/ocr_service.py` line 26

### Issue: "Port 8000 already in use"
**Solution**: Use a different port
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### Issue: Slow first transcription
**Solution**: This is normal - Whisper model loads on first use (~3-5 seconds). Subsequent transcriptions are fast.

## Project Structure Overview

```
fastapi_ocr_stt/
├── app/
│   ├── main.py                    # FastAPI app entry point
│   ├── controllers/               # API endpoints (routes)
│   │   ├── ocr_controller.py      # OCR endpoint logic
│   │   └── stt_controller.py      # STT endpoint logic
│   ├── services/                  # Business logic
│   │   ├── ocr_service.py         # OCR processing (Tesseract + Google Vision)
│   │   └── stt_service.py         # Audio transcription (Whisper)
│   ├── models/                    # Data models
│   │   └── responses.py           # Response schemas
│   └── core/                      # Utilities
│       └── logging_config.py      # Logging setup
├── requirements.txt               # Python dependencies
├── README.md                      # Main documentation
├── GOOGLE_VISION_SETUP.md        # Google Vision setup guide
└── SETUP_GUIDE.md                # This file
```

## Next Steps

1. Read [README.md](README.md) for full API documentation
2. Test both endpoints with sample files
3. Check [GOOGLE_VISION_SETUP.md](GOOGLE_VISION_SETUP.md) if you need better handwriting recognition
4. Experiment with the code in `app/` directory

## Need Help?

- API Documentation: http://localhost:8000/docs (when server is running)
- Check logs in the terminal where server is running
- Review error messages - they're usually very specific about what's wrong

## Security Reminder

**NEVER commit these files to Git:**
- `google-credentials.json` (contains sensitive credentials)
- `.env` files
- Any files with API keys or passwords

These are already in `.gitignore` but be careful!
