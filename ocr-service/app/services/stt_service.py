"""
Speech-to-Text Service - Business logic for audio transcription
Uses OpenAI Whisper for high-accuracy English transcription
"""
import whisper
import tempfile
import os
import time
import threading
from app.models.responses import STTResponse
from app.core.logging_config import logger

class STTService:
    """Service for Speech-to-Text transcription using OpenAI Whisper"""
    
    def __init__(self):
        """
        Initialize STT Service with lazy model loading.
        Model loads in background to avoid blocking application startup.
        """
        self.model = None
        self._model_loading = False
        self._model_ready = False
        self._load_lock = threading.Lock()
        
        # Start loading model in background thread (non-blocking)
        logger.info("Starting background Whisper model loading (base)...")
        self._load_thread = threading.Thread(target=self._load_model_background, daemon=True)
        self._load_thread.start()
    
    def _load_model_background(self):
        """Load Whisper model in background thread"""
        try:
            with self._load_lock:
                if self._model_loading or self._model_ready:
                    return
                self._model_loading = True
            
            # Load Whisper model
            # Options: tiny, base, small, medium, large
            # 'base' is good balance (faster, 99% accurate for clear English)
            logger.info("Loading Whisper model (base)... This may take 1-2 minutes on first run.")
            self.model = whisper.load_model("base")
            
            with self._load_lock:
                self._model_ready = True
                self._model_loading = False
            
            logger.info("✅ Whisper model loaded successfully and ready for transcription")
        except Exception as e:
            logger.error(f"❌ Failed to load Whisper model: {e}")
            with self._load_lock:
                self._model_loading = False
                self._model_ready = False
    
    def is_ready(self) -> bool:
        """Check if the model is loaded and ready"""
        with self._load_lock:
            return self._model_ready
    
    def transcribe_audio(self, audio_bytes: bytes, filename: str) -> STTResponse:
        """
        Transcribe audio bytes to text using OpenAI Whisper
        
        Args:
            audio_bytes: Raw audio bytes
            filename: Original filename for format detection
            
        Returns:
            STTResponse containing transcribed text
        """
        # Check if model is ready
        if not self.is_ready():
            if self._model_loading:
                return STTResponse(
                    success=False,
                    transcribed_text="",
                    error="Whisper model is still loading. Please try again in 30-60 seconds."
                )
            else:
                return STTResponse(
                    success=False,
                    transcribed_text="",
                    error="Whisper model failed to load. Please check server logs."
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
