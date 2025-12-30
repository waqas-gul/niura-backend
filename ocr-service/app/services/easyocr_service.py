"""
Alternative OCR Service using EasyOCR (better handwriting, no credentials needed)
"""
import easyocr
import numpy as np
from PIL import Image
import io
from app.models.responses import OCRResponse
from app.core.logging_config import logger

class EasyOCRService:
    """Service using EasyOCR - works offline, good with handwriting"""
    
    def __init__(self):
        # Initialize EasyOCR reader (downloads models first time)
        # Supports multiple languages, good with handwriting
        logger.info("Initializing EasyOCR (first time will download models)...")
        self.reader = easyocr.Reader(['en'], gpu=False)
        logger.info("EasyOCR ready - supports handwritten text!")
    
    def extract_text(self, image_bytes: bytes) -> OCRResponse:
        """
        Extract text from image using EasyOCR
        Works well with both printed and handwritten text
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            OCRResponse containing extracted text
        """
        try:
            # Convert bytes to numpy array
            image = Image.open(io.BytesIO(image_bytes))
            image_array = np.array(image)
            
            # Perform OCR
            results = self.reader.readtext(image_array)
            
            if not results:
                return OCRResponse(
                    success=False,
                    extracted_text="",
                    format_type="error",
                    error="No text detected in image"
                )
            
            # Extract text and confidence
            extracted_lines = []
            confidences = []
            
            for (bbox, text, confidence) in results:
                extracted_lines.append(text)
                confidences.append(confidence)
            
            # Join all detected text
            extracted_text = '\n'.join(extracted_lines)
            avg_confidence = (sum(confidences) / len(confidences)) * 100 if confidences else 0
            
            has_bullets = self._has_bullet_points(extracted_text)
            
            return OCRResponse(
                success=True,
                extracted_text=extracted_text,
                format_type="bullets" if has_bullets else "paragraph",
                confidence=round(avg_confidence, 2)
            )
            
        except Exception as e:
            logger.error(f"EasyOCR extraction failed: {str(e)}")
            return OCRResponse(
                success=False,
                extracted_text="",
                format_type="error",
                error=str(e)
            )
    
    def _has_bullet_points(self, text: str) -> bool:
        """Detect if text contains bullet points"""
        bullet_chars = ['•', '·', '-', '*', '○', '□', '■']
        lines = text.split('\n')
        
        bullet_count = sum(1 for line in lines if any(line.strip().startswith(char) for char in bullet_chars))
        
        return bullet_count > 0
