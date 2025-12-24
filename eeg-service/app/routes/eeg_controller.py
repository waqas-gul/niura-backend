
import logging
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query

from app.services.eeg_service import EEGService

# from app.models.eeg_record import EEGRecord
# from sqlalchemy.orm import Session as DBSession  # for the DB session dependency

from pydantic import BaseModel
# from sqlalchemy import and_, func  # Add func import here
from app.schemas.eeg import EEGBatchIn, EEGRecordOut
# from sqlalchemy.orm import Session 

router = APIRouter()

class ThresholdUpdateRequest(BaseModel):
    focus_threshold: float
    stress_threshold: float

def process_and_publish_bg(records, user_id, duration):
    """Background task to process EEG data and publish to Kafka."""
    try:
        service = EEGService()  # ✅ no DB session required now
        published_count = service.save_eeg_records(records, user_id, duration)
        logging.info(f"✅ Published {published_count} processed EEG records to Kafka for user {user_id}")
    except Exception as e:
        logging.exception(f"❌ Error publishing EEG data for user {user_id}: {e}")
        raise e


@router.post("/bulk")
def create_eeg_records(
    batch: EEGBatchIn,
    background_tasks: BackgroundTasks,
    # db: DBSession = Depends(get_db),   # removed
    current_user:dict=None
):
    user_id = (
        int(current_user.get("sub"))
        if current_user
        else (batch.user_id or 0)
    )
    
    try:
        if not batch.records:
            raise HTTPException(status_code=400, detail="No EEG records provided")
        
        duration = batch.duration or 4
        
        background_tasks.add_task(
            process_and_publish_bg, batch.records, user_id, duration
        )
        
        return {
            "message": f"EEG records received and are being processed. {len(batch.records)} records will be processed with {duration}s window.",
            "records_count": len(batch.records),
            "duration": duration
        }
    except Exception as e:
        logging.exception(f"Failed to process EEG records: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to process EEG records: {str(e)}")


