from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional

# Performance optimization: Minimal validation for high-throughput ingress
# Reduce Pydantic overhead on large payloads (500+ records per request)
class EEGRecordIn(BaseModel):
    model_config = ConfigDict(
        # Disable assignment validation (not needed for ingress)
        validate_assignment=False,
        # Allow arbitrary types for performance
        arbitrary_types_allowed=True,
        # Disable extra field validation
        extra='ignore',
        # Use python directly without validation where possible
        use_enum_values=True
    )
    
    sample_index: int
    timestamp: datetime
    eeg: List[float]  # Simple list, no nested model overhead

class EEGBatchIn(BaseModel):
    model_config = ConfigDict(
        # Optimize for bulk ingress - minimal validation overhead
        validate_assignment=False,
        arbitrary_types_allowed=True,
        extra='ignore'
    )
    
    user_id: Optional[int] = None
    records: List[EEGRecordIn]
    duration: Optional[int] = 4

class EEGRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    timestamp: datetime
    focus_label: float
    stress_label: float
    wellness_label: float