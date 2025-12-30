"""
Response Models - Pydantic models for API responses
"""
from pydantic import BaseModel, Field
from typing import Optional

class OCRResponse(BaseModel):
    """Response model for OCR endpoint"""
    success: bool = Field(..., description="Whether extraction was successful")
    extracted_text: str = Field(..., description="Extracted text from image")
    format_type: str = Field(..., description="Text format: bullets, paragraph, or error")
    confidence: Optional[float] = Field(None, description="OCR confidence score (0-100)")
    error: Optional[str] = Field(None, description="Error message if failed")

class STTResponse(BaseModel):
    """Response model for Speech-to-Text endpoint"""
    success: bool = Field(..., description="Whether transcription was successful")
    transcribed_text: str = Field(..., description="Transcribed text from audio")
    language: Optional[str] = Field("en-US", description="Detected/used language")
    duration: Optional[float] = Field(None, description="Audio duration in seconds")
    error: Optional[str] = Field(None, description="Error message if failed")
