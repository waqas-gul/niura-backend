"""
Speech-to-Text Controller - Handles audio transcription requests
"""

from fastapi import APIRouter, File, UploadFile, HTTPException
from app.services.stt_service import STTService
from app.models.responses import STTResponse
from app.core.logging_config import logger

router = APIRouter()
stt_service = STTService()


@router.post("/transcribe", response_model=STTResponse)
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Transcribe audio file to text

    Args:
        file: Audio file (WAV, MP3, M4A, FLAC)

    Returns:
        STTResponse with transcribed text
    """
    try:
        # Validate file type - check both content_type and file extension
        allowed_types = [
            "audio/wav",
            "audio/mpeg",
            "audio/mp3",
            "audio/x-m4a",
            "audio/flac",
            "application/octet-stream",  # Allow when content-type is not properly set
        ]

        filename = file.filename.lower() if file.filename else ""
        allowed_extensions = [".wav", ".mp3", ".m4a", ".flac"]

        has_valid_content_type = file.content_type in allowed_types
        has_valid_extension = any(filename.endswith(ext) for ext in allowed_extensions)

        if not (has_valid_content_type or has_valid_extension):
            raise HTTPException(
                status_code=400,
                detail=f"File must be audio format (WAV, MP3, M4A, FLAC). Received: {file.content_type}",
            )

        logger.info(
            f"Processing STT request for file: {file.filename} (content_type: {file.content_type})"
        )

        # Read file content
        audio_bytes = await file.read()

        # Process through service
        result = stt_service.transcribe_audio(audio_bytes, file.filename)

        logger.info(f"STT completed successfully for: {file.filename}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"STT processing failed: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to transcribe audio: {str(e)}"
        )
