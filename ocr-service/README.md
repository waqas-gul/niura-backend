# OCR & Speech-to-Text FastAPI Application

Professional REST API for image text extraction (OCR) and audio transcription (STT) with clean architecture.

## 🚀 Quick Start (For Junior Developers)

```powershell
# 1. Install system dependencies
winget install --id=Gyan.FFmpeg -e
# Download Tesseract: https://github.com/UB-Mannheim/tesseract/wiki

# 2. Clone and setup
cd fastapi_ocr_stt
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# 3. Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 4. Test at http://localhost:8000/docs
```

## Features

- **OCR Endpoint**: Extract text from images (PNG, JPG, JPEG)
  - 🔥 **Powered by Google Vision API** - Excellent handwritten text recognition
  - ✅ **Best for**: Handwritten notes, printed text, documents, photos
  - 📷 Handles poor lighting, angles, and low-quality images
- **STT Endpoint**: Transcribe audio files to text (WAV, MP3, M4A, FLAC, etc.)
  - 🔥 **Powered by OpenAI Whisper** - State-of-the-art accuracy
  - ✅ **99%+ accuracy** for clear English speech
  - 🎯 Works offline, handles accents and background noise
- Clean architecture with controllers and services
- Comprehensive error handling
- Logging and monitoring

## Important Notes

### OCR - Google Vision API
**Google Vision API** is the primary OCR engine:
- ✅ **Excellent for handwritten text** (95%+ accuracy)
- ✅ Works well: Handwritten notes, printed text, photos, documents
- ✅ Handles poor lighting, angles, and image quality
- 🔐 **Requires setup** - see [GOOGLE_VISION_SETUP.md](GOOGLE_VISION_SETUP.md)
- 💰 Free tier: 1,000 requests/month

### STT - OpenAI Whisper
**OpenAI Whisper** for speech transcription:
- ✅ **State-of-the-art accuracy** (better than Google Speech API)
- ✅ Works offline (no API costs or rate limits)
- ✅ Handles accents, background noise, and various audio qualities
- ⚡ First run downloads model (~150MB for 'base' model)

### Improving OCR for Photos
When taking photos of documents:
1. Use good lighting (avoid shadows)
2. Hold camera directly above (avoid angles)
3. Ensure text is in focus
4. Use high resolution (at least 1000px height)
5. Avoid reflections on glossy paper

## Architecture

```
app/
├── main.py                 # FastAPI application entry
├── controllers/            # Request handlers
│   ├── ocr_controller.py
│   └── stt_controller.py
├── services/              # Business logic
│   ├── ocr_service.py
│   └── stt_service.py
├── models/                # Pydantic models
│   └── responses.py
└── core/                  # Core utilities
    └── logging_config.py
```

## Prerequisites

### Required:
1. **Python 3.10+**

2. **FFmpeg** - Required by Whisper for audio processing
   ```powershell
   # Install using winget (easiest method)
   winget install --id=Gyan.FFmpeg -e
   
   # Verify installation
   ffmpeg -version
   ```
   Alternative: Download from https://ffmpeg.org/download.html and add to PATH

3. **Tesseract OCR** - Required for OCR fallback
   - Download: https://github.com/UB-Mannheim/tesseract/wiki
   - Install to: `C:\Program Files\Tesseract-OCR\`
   - Verify: `tesseract --version`

### Optional (Recommended for Production):
1. **Google Cloud Vision API** - For better handwritten text recognition
   - See [GOOGLE_VISION_SETUP.md](GOOGLE_VISION_SETUP.md) for setup instructions
   - Without credentials: Falls back to Tesseract
   - With credentials: 95%+ accuracy on handwritten text
   - Free tier: 1,000 requests/month

## Installation

```powershell
# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies (may take 2-3 minutes for PyTorch/Whisper)
pip install -r requirements.txt
```

**Note:** First run will download Whisper model (~150MB). Subsequent runs are instant.

## Running the Application

### Basic Run (No Google Vision)
```powershell
# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### With Google Vision API (Better Handwriting Recognition)
```powershell
# Set credentials path (one-time per session)
$env:GOOGLE_APPLICATION_CREDENTIALS="I:\path\to\google-credentials.json"

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at: `http://localhost:8000`

## API Documentation

Interactive docs: `http://localhost:8000/docs`

### Endpoints

#### 1. OCR - Extract Text from Image

**POST** `/api/v1/ocr/extract`

- **Request**: Form-data with `file` (image)
- **Response**:
```json
{
  "success": true,
  "extracted_text": "Your extracted text here...",
  "format_type": "paragraph",
  "confidence": 95.5
}
```

#### 2. STT - Transcribe Audio

**POST** `/api/v1/stt/transcribe`

- **Request**: Form-data with `file` (audio)
- **Response**:
```json
{
  "success": true,
  "transcribed_text": "Your transcribed text here...",
  "language": "en",
  "duration": 2.5
}
```

**Note:** Duration is processing time, not audio length.

## Testing with Postman

### OCR Endpoint:
1. Set method to `POST`
2. URL: `http://localhost:8000/api/v1/ocr/extract`
3. Body → form-data
4. Key: `file`, Type: `File`, Value: Select your image
5. Send

### STT Endpoint:
1. Set method to `POST`
2. URL: `http://localhost:8000/api/v1/stt/transcribe`
3. Body → form-data
4. Key: `file`, Type: `File`, Value: Select your audio
5. Send

## Project Structure Details

- **Controllers**: Handle HTTP requests, validation, and responses
- **Services**: Contain business logic for OCR and STT processing
- **Models**: Pydantic models for request/response validation
- **Core**: Shared utilities like logging

## Error Handling

All endpoints return structured error responses:
```json
{
  "success": false,
  "error": "Detailed error message"
}
```

## Troubleshooting

### STT: "WinError 2: The system cannot find the file specified"
**Problem**: FFmpeg not installed or not in PATH  
**Solution**:
```powershell
# Install FFmpeg
winget install --id=Gyan.FFmpeg -e

# Restart PowerShell, then verify
ffmpeg -version

# If still fails, reload PATH in current session
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
```

### OCR: "Tesseract not found"
**Problem**: Tesseract OCR not installed  
**Solution**: Download from https://github.com/UB-Mannheim/tesseract/wiki and install to `C:\Program Files\Tesseract-OCR\`

### Google Vision: "403 SERVICE_DISABLED"
**Problem**: Vision API not enabled for your project  
**Solution**: See [GOOGLE_VISION_SETUP.md](GOOGLE_VISION_SETUP.md) for detailed setup

### Server won't start: "Port already in use"
**Problem**: Port 8000 is already occupied  
**Solution**: 
```powershell
# Use a different port
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

## Important Notes for Deployment

⚠️ **Security**:
- Never commit `google-credentials.json` to Git
- Use environment variables for credentials in production
- Enable CORS only for trusted domains in production

⚠️ **Performance**:
- Whisper model loads on startup (~3-5 seconds)
- First transcription may be slower (model initialization)
- Consider using smaller Whisper models (tiny/base) for faster processing
- For production, use larger models (small/medium) for better accuracy

## License

MIT
