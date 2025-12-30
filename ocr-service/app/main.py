"""
Main FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.controllers.ocr_controller import router as ocr_router
from app.controllers.stt_controller import router as stt_router

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

# Register routers
app.include_router(ocr_router, prefix="/api/image", tags=["OCR"])
app.include_router(stt_router, prefix="/api/audio", tags=["Speech-to-Text"])


@app.get("/")
async def root():
    return {
        "message": "OCR & Speech-to-Text API",
        "endpoints": {"ocr": "/api/image/extract", "stt": "/api/audio/transcribe"},
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
