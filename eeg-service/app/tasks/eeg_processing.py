"""
Celery tasks for CPU-intensive EEG processing.
Offloads FFT computation and ML inference from web workers.
"""

import logging
from typing import List, Dict, Any
from app.core.celery_app import celery_app
from app.services.fft_eeg_service import FFTEEGService
from app.events.kafka_producer import send_processed_eeg_event

logger = logging.getLogger(__name__)


@celery_app.task(name="process_eeg_fft", bind=True, max_retries=3)
def process_eeg_fft(self, records: List[Dict[str, Any]], user_id: int, duration: int):
    """
    Background task: Process EEG records using FFT pipeline.
    
    This runs in a separate Celery worker process, not in the FastAPI thread pool.
    CPU-intensive FFT computations happen here without blocking HTTP responses.
    
    Args:
        records: List of raw EEG record dictionaries
        user_id: User identifier
        duration: Processing window duration in seconds
    
    Returns:
        dict: Processing result summary
    """
    try:
        logger.info(f"🔄 Starting FFT processing for user {user_id}, {len(records)} records")
        
        # Initialize service (happens in worker process)
        service = FFTEEGService()
        
        # CPU-intensive processing happens here
        processed_records = service.process_eeg_records(records, duration)
        
        # Publish results to Kafka
        if processed_records:
            send_processed_eeg_event(user_id, processed_records)
            logger.info(f"✅ Published {len(processed_records)} FFT-processed records to Kafka for user {user_id}")
        
        return {
            "status": "success",
            "user_id": user_id,
            "records_processed": len(processed_records),
            "records_received": len(records)
        }
        
    except Exception as e:
        logger.exception(f"❌ Error in FFT processing for user {user_id}: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries)
