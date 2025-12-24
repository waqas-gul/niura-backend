from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class EEGRecordIn(BaseModel):
    sample_index: int
    timestamp: datetime
    eeg: List[float]

class EEGBatchIn(BaseModel):
    user_id: Optional[int] = None
    records: List[EEGRecordIn]
    duration: Optional[int] = 4

class EEGRecordOut(BaseModel):
    id: int
    user_id: int
    timestamp: datetime
    focus_label: float
    stress_label: float
    wellness_label: float
    
    class Config:
        from_attributes = True