from pydantic import BaseModel
from typing import List, Optional, Union
from datetime import datetime

class SessionTimestamp(BaseModel):
    start: datetime
    end: Optional[datetime] = None

class SessionTrackingData(BaseModel):
    label: str
    duration: Optional[Union[str, int, float]] = None  # Accept duration in various formats
    timestamps: List[SessionTimestamp]

class SessionTrackingRequest(BaseModel):
    session_data: SessionTrackingData