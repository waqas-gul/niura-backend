"""
OCR Service - Business logic for text extraction from images
Supports both Tesseract (printed) and Google Vision (handwritten)
"""
import cv2
import numpy as np
import pytesseract
from PIL import Image
import io
import os
from app.models.responses import OCRResponse
from app.core.logging_config import logger

# Google Vision for handwriting recognition
try:
    from google.cloud import vision
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False
    logger.warning("Google Vision not installed. Only Tesseract OCR available.")

class OCRService:
    """Service for Optical Character Recognition"""
    
    def __init__(self):
        # Configure Tesseract path for Windows (common installation location)
        if os.name == 'nt':  # Windows
            tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            if os.path.exists(tesseract_path):
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
            else:
                logger.warning("Tesseract not found at default path. Install from: https://github.com/UB-Mannheim/tesseract/wiki")
        
        # Initialize Google Vision client (works without credentials for basic use)
        self.vision_client = None
        if VISION_AVAILABLE:
            try:
                self.vision_client = vision.ImageAnnotatorClient()
                logger.info("Google Vision API initialized - will use for all OCR (better handwriting recognition)")
            except Exception as e:
                logger.warning(f"Google Vision not configured: {e}. Using Tesseract only.")
    
    def extract_text(self, image_bytes: bytes) -> OCRResponse:
        """
        Extract text from image bytes
        Uses Google Vision API by default (better for handwriting)
        Falls back to Tesseract if Vision is unavailable
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            OCRResponse containing extracted text
        """
        try:
            # Try Google Vision first (best for handwriting)
            if self.vision_client:
                return self._extract_with_vision(image_bytes)
            
            # Fallback to Tesseract (for printed text only)
            logger.info("Using Tesseract OCR (note: poor with handwriting)")
            return self._extract_with_tesseract(image_bytes)
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}")
            return OCRResponse(
                success=False,
                extracted_text="",
                format_type="error",
                error=str(e)
            )
    
    def _extract_with_vision(self, image_bytes: bytes) -> OCRResponse:
        """
        Extract text using Google Vision API
        Best for: Handwritten text, printed text, photos
        """
        try:
            image = vision.Image(content=image_bytes)
            
            # Use document_text_detection for best results
            response = self.vision_client.document_text_detection(image=image)
            
            if response.error.message:
                raise Exception(response.error.message)
            
            # Get full text
            extracted_text = response.full_text_annotation.text if response.full_text_annotation else ""
            
            if not extracted_text or len(extracted_text.strip()) == 0:
                return OCRResponse(
                    success=False,
                    extracted_text="",
                    format_type="error",
                    error="No text detected in image"
                )
            
            has_bullets = self._has_bullet_points(extracted_text)
            
            return OCRResponse(
                success=True,
                extracted_text=extracted_text.strip(),
                format_type="bullets" if has_bullets else "paragraph",
                confidence=95.0
            )
            
        except Exception as e:
            logger.error(f"Google Vision failed: {e}")
            # Fall back to Tesseract
            logger.info("Falling back to Tesseract OCR")
            return self._extract_with_tesseract(image_bytes)
    
    def _extract_with_tesseract(self, image_bytes: bytes) -> OCRResponse:
        """
        Extract text using Tesseract OCR
        Best for: Printed text only (poor with handwriting)
        """
        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Preprocess image
        processed_image = self._preprocess_image(image)
        
        # Extract text with Tesseract
        extracted_text = pytesseract.image_to_string(processed_image)
        
        # Format text (preserve structure)
        formatted_text = self._format_text(extracted_text)
        
        if not formatted_text or len(formatted_text.strip()) < 2:
            return OCRResponse(
                success=False,
                extracted_text="",
                format_type="error",
                error="No text detected (Tesseract is poor with handwriting - install Google Vision for better results)"
            )
        
        # Detect if text has bullet points or paragraphs
        has_bullets = self._has_bullet_points(extracted_text)
        
        return OCRResponse(
            success=True,
            extracted_text=formatted_text,
            format_type="bullets" if has_bullets else "paragraph",
            confidence=self._calculate_confidence(extracted_text)
        )
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Enhanced preprocessing for better OCR accuracy (especially for photos)
        """
        # Convert PIL to OpenCV format
        img_array = np.array(image)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Resize if image is too small (improve quality for low-res photos)
        height, width = gray.shape
        if height < 1000:
            scale_factor = 1000 / height
            gray = cv2.resize(gray, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)
        
        # Apply adaptive thresholding (better for photos with varying lighting)
        # This helps with photos taken with phone cameras
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(binary, h=10)
        
        # Morphological operations to clean up text
        kernel = np.ones((1, 1), np.uint8)
        morph = cv2.morphologyEx(denoised, cv2.MORPH_CLOSE, kernel)
        
        # Convert back to PIL
        return Image.fromarray(morph)
    
    def _format_text(self, text: str) -> str:
        """
        Format extracted text preserving structure
        """
        # Remove excessive whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Join lines maintaining structure
        formatted = '\n'.join(lines)
        
        return formatted
    
    def _has_bullet_points(self, text: str) -> bool:
        """
        Detect if text contains bullet points
        """
        bullet_chars = ['•', '·', '-', '*', '○', '□', '■']
        lines = text.split('\n')
        
        bullet_count = sum(1 for line in lines if any(line.strip().startswith(char) for char in bullet_chars))
        
        return bullet_count > 0
    
    def _calculate_confidence(self, text: str) -> float:
        """
        Estimate OCR confidence based on text characteristics
        """
        if not text or len(text.strip()) < 5:
            return 0.0
        
        # Simple heuristic: ratio of alphanumeric to total characters
        alphanumeric = sum(c.isalnum() for c in text)
        total = len(text.replace(' ', '').replace('\n', ''))
        
        if total == 0:
            return 0.0
        
        return round((alphanumeric / total) * 100, 2)
