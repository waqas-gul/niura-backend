"""
FFT-based EEG processing endpoints
Fast alternative to BrainFlow-based processing
"""

import logging
from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import List
from app.services.fft_eeg_service import FFTEEGService
from app.schemas.eeg import EEGBatchIn
from app.events.kafka_producer import send_processed_eeg_event

router = APIRouter()
logger = logging.getLogger(__name__)


def process_and_publish_fft_bg(records, user_id, duration):
    """Background task to process EEG data with FFT and publish to Kafka."""
    try:
        service = FFTEEGService()
        processed_records = service.process_eeg_records(records, duration)
        
        # Publish to Kafka
        if processed_records:
            send_processed_eeg_event(user_id, processed_records)
            logger.info(f"✅ Published {len(processed_records)} FFT-processed records to Kafka for user {user_id}")
        
    except Exception as e:
        logger.exception(f"❌ Error in FFT processing for user {user_id}: {e}")
        raise


@router.post("/bulk-fft")
def create_eeg_records_fft(
    batch: EEGBatchIn,
    background_tasks: BackgroundTasks,
    current_user: dict = None
):
    """
    Process EEG records using fast FFT-based pipeline.
    
    Alternative to /bulk endpoint - uses lightweight FFT processing
    instead of BrainFlow ML models for faster real-time performance.
    """
    user_id = (
        int(current_user.get("sub"))
        if current_user
        else (batch.user_id or 0)
    )
    
    try:
        if not batch.records:
            raise HTTPException(status_code=400, detail="No EEG records provided")
        
        duration = batch.duration or 2
        
        # Add background task
        background_tasks.add_task(
            process_and_publish_fft_bg, 
            batch.records, 
            user_id, 
            duration
        )
        
        return {
            "message": f"EEG records received and are being processed with FFT pipeline. {len(batch.records)} records will be processed with {duration}s window.",
            "records_count": len(batch.records),
            "duration": duration,
            "processing_method": "FFT"
        }
        
    except Exception as e:
        logger.exception(f"Failed to process EEG records with FFT: {str(e)}")
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to process EEG records: {str(e)}"
        )


@router.post("/bulk-fft-sync")
def create_eeg_records_fft_sync(
    batch: EEGBatchIn,
    current_user: dict = None
):
    """
    Process EEG records synchronously using FFT pipeline.
    Returns full results immediately (for testing/debugging).
    """
    user_id = (
        int(current_user.get("sub"))
        if current_user
        else (batch.user_id or 0)
    )
    
    try:
        if not batch.records:
            raise HTTPException(status_code=400, detail="No EEG records provided")
        
        duration = batch.duration or 2
        
        # Process synchronously
        service = FFTEEGService()
        processed_records = service.process_eeg_records(batch.records, duration)
        
        return {
            "user_id": user_id,
            "records_count": len(batch.records),
            "processed_count": len(processed_records),
            "duration": duration,
            "processing_method": "FFT",
            "records": processed_records
        }
        
    except Exception as e:
        logger.exception(f"Failed to process EEG records with FFT (sync): {str(e)}")
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to process EEG records: {str(e)}"
        )
