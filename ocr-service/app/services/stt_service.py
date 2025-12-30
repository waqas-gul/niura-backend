"""
Speech-to-Text Service - Business logic for audio transcription
Uses OpenAI Whisper for high-accuracy English transcription
"""
import whisper
import tempfile
import os
import time
from app.models.responses import STTResponse
from app.core.logging_config import logger

class STTService:
    """Service for Speech-to-Text transcription using OpenAI Whisper"""
    
    def __init__(self):
        """Initialize Whisper model (base model for good balance of speed/accuracy)"""
        try:
            # Load Whisper model
            # Options: tiny, base, small, medium, large
            # 'base' is good balance (faster, 99% accurate for clear English)
            # 'small' or 'medium' for better accuracy with accents/noise
            logger.info("Loading Whisper model (base)...")
            self.model = whisper.load_model("base")
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            self.model = None
    
    def transcribe_audio(self, audio_bytes: bytes, filename: str) -> STTResponse:
        """
        Transcribe audio bytes to text using OpenAI Whisper
        
        Args:
            audio_bytes: Raw audio bytes
            filename: Original filename for format detection
            
        Returns:
            STTResponse containing transcribed text
        """
        if not self.model:
            return STTResponse(
                success=False,
                transcribed_text="",
                error="Whisper model not initialized. Please restart the server."
            )
        
        temp_audio_path = None
        
        try:
            # Save audio to temporary file (Whisper works with file paths)
            temp_audio_path = self._save_temp_audio(audio_bytes, filename)
            
            logger.info(f"Transcribing audio with Whisper: {filename}")
            start_time = time.time()
            
            # Transcribe with Whisper
            # language='en' forces English (better accuracy)
            # fp16=False for CPU compatibility
            result = self.model.transcribe(
                temp_audio_path,
                language='en',  # Force English for best accuracy
                fp16=False,     # CPU compatibility
                task='transcribe'  # transcribe (not translate)
            )
            
            transcribed_text = result['text'].strip()
            duration = round(time.time() - start_time, 2)
            
            logger.info(f"Transcription completed in {duration}s")
            
            if not transcribed_text:
                return STTResponse(
                    success=False,
                    transcribed_text="",
                    error="No speech detected in audio"
                )
            
            return STTResponse(
                success=True,
                transcribed_text=transcribed_text,
                language="en",
                duration=duration
            )
            
        except Exception as e:
            logger.error(f"STT transcription failed: {str(e)}")
            return STTResponse(
                success=False,
                transcribed_text="",
                error=f"Transcription failed: {str(e)}"
            )
        
        finally:
            # Clean up temp file
            if temp_audio_path and os.path.exists(temp_audio_path):
                try:
                    os.remove(temp_audio_path)
                except:
                    pass
    
    def _save_temp_audio(self, audio_bytes: bytes, filename: str) -> str:
        """
        Save audio bytes to temporary file
        
        Returns:
            Path to temporary audio file
        """
        # Detect format from filename
        file_ext = os.path.splitext(filename)[1].lower()
        
        # Whisper supports: mp3, mp4, mpeg, mpga, m4a, wav, webm
        if not file_ext:
            file_ext = '.wav'  # Default
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
        temp_file.write(audio_bytes)
        temp_file.close()
        
        return temp_file.name
