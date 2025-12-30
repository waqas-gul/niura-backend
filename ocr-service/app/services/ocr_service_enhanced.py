"""
Enhanced OCR Service with Google Vision API support for handwriting
"""
import cv2
import numpy as np
import pytesseract
from PIL import Image
import io
import os
from app.models.responses import OCRResponse
from app.core.logging_config import logger

# Optional: Google Vision for better handwriting recognition
try:
    from google.cloud import vision
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False

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
        
        # Initialize Google Vision client if available
        self.vision_client = None
        if VISION_AVAILABLE and os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
            try:
                self.vision_client = vision.ImageAnnotatorClient()
                logger.info("Google Vision API initialized for handwriting recognition")
            except Exception as e:
                logger.warning(f"Could not initialize Google Vision: {e}")
    
    def extract_text(self, image_bytes: bytes, use_vision: bool = False) -> OCRResponse:
        """
        Extract text from image bytes
        
        Args:
            image_bytes: Raw image bytes
            use_vision: Use Google Vision API for better handwriting recognition
            
        Returns:
            OCRResponse containing extracted text
        """
        try:
            # Try Google Vision first if enabled and available
            if use_vision and self.vision_client:
                return self._extract_with_vision(image_bytes)
            
            # Fallback to Tesseract
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
        """Extract text using Google Vision API (better for handwriting)"""
        try:
            image = vision.Image(content=image_bytes)
            response = self.vision_client.document_text_detection(image=image)
            
            if response.error.message:
                raise Exception(response.error.message)
            
            extracted_text = response.full_text_annotation.text
            
            has_bullets = self._has_bullet_points(extracted_text)
            
            return OCRResponse(
                success=True,
                extracted_text=extracted_text.strip(),
                format_type="bullets" if has_bullets else "paragraph",
                confidence=95.0  # Vision API doesn't return confidence
            )
            
        except Exception as e:
            logger.warning(f"Google Vision failed, falling back to Tesseract: {e}")
            return self._extract_with_tesseract(image_bytes)
    
    def _extract_with_tesseract(self, image_bytes: bytes) -> OCRResponse:
        """Extract text using Tesseract OCR (best for printed text)"""
        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Enhanced preprocessing for better accuracy
        processed_image = self._preprocess_image_enhanced(image)
        
        # Extract text with Tesseract
        extracted_text = pytesseract.image_to_string(processed_image)
        
        # Format text (preserve structure)
        formatted_text = self._format_text(extracted_text)
        
        # Detect if text has bullet points or paragraphs
        has_bullets = self._has_bullet_points(extracted_text)
        
        return OCRResponse(
            success=True,
            extracted_text=formatted_text,
            format_type="bullets" if has_bullets else "paragraph",
            confidence=self._calculate_confidence(extracted_text)
        )
    
    def _preprocess_image_enhanced(self, image: Image.Image) -> Image.Image:
        """
        Enhanced preprocessing for better OCR accuracy
        """
        # Convert PIL to OpenCV format
        img_array = np.array(image)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Resize if image is too small (improve quality)
        height, width = gray.shape
        if height < 1000:
            scale_factor = 1000 / height
            gray = cv2.resize(gray, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)
        
        # Apply adaptive thresholding (better for photos with varying lighting)
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(binary)
        
        # Deskew if needed (straighten tilted text)
        deskewed = self._deskew_image(denoised)
        
        # Convert back to PIL
        return Image.fromarray(deskewed)
    
    def _deskew_image(self, image: np.ndarray) -> np.ndarray:
        """Straighten tilted images"""
        coords = np.column_stack(np.where(image > 0))
        if len(coords) == 0:
            return image
        
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        
        # Only deskew if angle is significant
        if abs(angle) > 0.5:
            (h, w) = image.shape
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            return rotated
        
        return image
    
    def _format_text(self, text: str) -> str:
        """Format extracted text preserving structure"""
        # Remove excessive whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Join lines maintaining structure
        formatted = '\n'.join(lines)
        
        return formatted
    
    def _has_bullet_points(self, text: str) -> bool:
        """Detect if text contains bullet points"""
        bullet_chars = ['•', '·', '-', '*', '○', '□', '■']
        lines = text.split('\n')
        
        bullet_count = sum(1 for line in lines if any(line.strip().startswith(char) for char in bullet_chars))
        
        return bullet_count > 0
    
    def _calculate_confidence(self, text: str) -> float:
        """Estimate OCR confidence based on text characteristics"""
        if not text or len(text.strip()) < 5:
            return 0.0
        
        # Simple heuristic: ratio of alphanumeric to total characters
        alphanumeric = sum(c.isalnum() for c in text)
        total = len(text.replace(' ', '').replace('\n', ''))
        
        if total == 0:
            return 0.0
        
        return round((alphanumeric / total) * 100, 2)
