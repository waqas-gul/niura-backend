from fastapi import APIRouter, Depends, HTTPException
from app.core.security import get_current_user_payload
from app.events.kafka_producer import send_eeg_event
from pydantic import BaseModel

router = APIRouter()

class EEGDataIn(BaseModel):
    timestamp: float
    channels: list[float]
    attention: float | None = None
    meditation: float | None = None

@router.post("/eeg/data")
def receive_eeg_data(payload: EEGDataIn, current_user=Depends(get_current_user_payload)):
    try:
        user_id = current_user.get("sub")
        send_eeg_event(user_id, payload.dict())
        return {"status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Kafka publish failed: {e}")


