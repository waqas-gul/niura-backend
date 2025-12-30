"""
OCR Controller - Handles image text extraction requests
"""

from fastapi import APIRouter, File, UploadFile, HTTPException
import os
from datetime import datetime
from pathlib import Path
from app.services.ocr_service import OCRService
from app.models.responses import OCRResponse
from app.core.logging_config import logger

router = APIRouter()
ocr_service = OCRService()


@router.post("/extract", response_model=OCRResponse)
async def extract_text_from_image(file: UploadFile = File(...)):
    """
    Extract text from uploaded image

    Args:
        file: Image file (PNG, JPG, JPEG)

    Returns:
        OCRResponse with extracted text
    """
    try:
        # Validate file type
        if not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400, detail="File must be an image (PNG, JPG, JPEG)"
            )

        logger.info(f"Processing OCR request for file: {file.filename}")

        # Read file content
        image_bytes = await file.read()

        # Optional: save incoming images for debugging when enabled
        try:
            if os.getenv("OCR_DEBUG_SAVE", "false").lower() == "true":
                save_dir = Path("/app/logs/debug_uploads")
                save_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
                safe_name = (
                    file.filename.replace(" ", "_") if file.filename else "upload"
                )
                out_path = save_dir / f"{timestamp}_{safe_name}"
                with open(out_path, "wb") as f:
                    f.write(image_bytes)
                logger.info(f"Saved debug upload to: {out_path}")
        except Exception as save_exc:
            logger.warning(f"Failed to save debug upload: {save_exc}")

        # Process through service
        result = ocr_service.extract_text(image_bytes)

        logger.info(f"OCR completed successfully for: {file.filename}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR processing failed: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to process image: {str(e)}"
        )
