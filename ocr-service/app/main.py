"""
Main FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.controllers.ocr_controller import router as ocr_router
from app.controllers.stt_controller import router as stt_router
from app.services.stt_service import STTService
from app.services.ocr_service import OCRService

app = FastAPI(
    title="OCR & Speech-to-Text API",
    description="REST API for image text extraction and audio transcription",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services (loaded lazily)
stt_service = STTService()
ocr_service = OCRService()

# Register routers
app.include_router(ocr_router, prefix="/api/image", tags=["OCR"])
app.include_router(stt_router, prefix="/api/audio", tags=["Speech-to-Text"])


@app.get("/")
async def root():
    return {
        "message": "OCR & Speech-to-Text API",
        "endpoints": {"ocr": "/api/image/extract", "stt": "/api/audio/transcribe"},
    }


@app.get("/api/health")
async def health():
    """
    Health check endpoint for ECS/Docker health monitoring.
    Returns service readiness status including ML model loading state.
    """
    # Check if STT service (Whisper model) is ready
    stt_ready = stt_service.is_ready()
    stt_loading = stt_service._model_loading
    
    # OCR service is always ready (no heavy model loading)
    ocr_ready = True
    
    # Service is healthy if at least basic API is running
    # But report model loading status
    status = {
        "status": "ok",
        "service": "ocr-stt-api",
        "services": {
            "ocr": {
                "status": "ready" if ocr_ready else "not_ready",
                "ready": ocr_ready
            },
            "stt": {
                "status": "ready" if stt_ready else ("loading" if stt_loading else "failed"),
                "ready": stt_ready,
                "loading": stt_loading
            }
        },
        "overall_ready": stt_ready and ocr_ready
    }
    
    return status
