"""
FFT-based EEG processing endpoints
Fast alternative to BrainFlow-based processing

PERFORMANCE OPTIMIZATIONS:
1. Async endpoint handlers (no thread pool blocking)
2. Celery task queue for CPU-intensive work (not BackgroundTasks)
3. Minimal logging in hot path
4. Fast enqueue + immediate return pattern
"""

import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.schemas.eeg import EEGBatchIn
from app.tasks.eeg_processing import process_eeg_fft

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================================================
# OPTIMIZED ASYNC ENDPOINT - Main production endpoint
# ============================================================================

@router.post("/bulk-fft")
async def create_eeg_records_fft(
    batch: Dict[str, Any],  # Accept raw dict to skip Pydantic overhead
    current_user: dict = None
) -> Dict[str, Any]:
    """
    Fast async endpoint: Enqueue EEG processing and return immediately.
    
    PERFORMANCE CHARACTERISTICS:
    - Async handler (no thread pool overhead)
    - Minimal validation (delegate to worker)
    - Fire-and-forget task submission
    - Target: <300ms p50 latency under 200+ concurrent requests
    - Pydantic validation optimized for large payloads
    - Celery task queue (separate worker process for CPU work)
    - Target: <300ms p50 latency under 200+ concurrent requests
    
    ARCHITECTURE:
    - Web layer: Validate input + enqueue task + return
    - Worker layer: FFT processing + Kafka publishing (separate process)
    
    Alternative to /bulk endpoint - uses lightweight FFT processing
    instead of BrainFlow ML models for faster real-time performance.
    """
    # Extract user_id (minimal overhead)
    user_id = (
        int(current_user.get("sub"))
        if current_user
        else (batch.get("user_id") or 0)
    )
    
    # Minimal validation - delegate detailed validation to worker
    records = batch.get("records", [])
    if not records:
        raise HTTPException(status_code=400, detail="No EEG records provided")
    
    duration = batch.get("duration") or 2
    records_count = len(records)
    
    # PERFORMANCE: Pass raw dict directly - no Pydantic conversion
    # Worker will handle validation if needed
    process_eeg_fft.apply_async(
        args=[records, user_id, duration],
        queue='eeg_processing',
        ignore_result=True
    )
    
    # Return immediately - no task_id needed for fire-and-forget
    return {
        "message": f"EEG records received and queued for FFT processing",
        "records_count": records_count,
        "duration": duration,
        "processing_method": "FFT",
        "status": "queued"  # Task submitted successfully
    }


# ============================================================================
# SYNC ENDPOINT - For testing/debugging only
# ============================================================================

# ============================================================================
# SYNC ENDPOINT - For testing/debugging only
# ============================================================================

@router.post("/bulk-fft-sync")
async def create_eeg_records_fft_sync(
    batch: EEGBatchIn,
    current_user: dict = None
) -> Dict[str, Any]:
    """
    Process EEG records synchronously using FFT pipeline.
    Returns full results immediately (for testing/debugging).
    
    WARNING: This endpoint blocks the event loop during processing.
    Use /bulk-fft for production traffic.
    """
    from app.services.fft_eeg_service import FFTEEGService
    
    user_id = (
        int(current_user.get("sub"))
        if current_user
        else (batch.user_id or 0)
    )
    
    if not batch.records:
        raise HTTPException(status_code=400, detail="No EEG records provided")
    
    duration = batch.duration or 2
    
    # Process synchronously (blocks event loop - testing only)
    service = FFTEEGService()
    records_data = [rec.model_dump() for rec in batch.records]
    processed_records = service.process_eeg_records(records_data, duration)
    
    return {
        "user_id": user_id,
        "records_count": len(batch.records),
        "processed_count": len(processed_records),
        "duration": duration,
        "processing_method": "FFT_SYNC",
        "records": processed_records
    }
