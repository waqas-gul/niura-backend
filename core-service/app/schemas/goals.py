from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class GoalCreate(BaseModel):
    title: str
    goal_type: str  # "focus", "meditation", "custom"
    tracking_method: str  # "sessions", "minutes", "high_focus", "low_stress_episodes"
    target: int
    start_date: datetime
    end_date: datetime

class GoalUpdate(BaseModel):
    title: Optional[str] = None
    goal_type: Optional[str] = None
    tracking_method: Optional[str] = None
    target: Optional[int] = None
    current: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class GoalResponse(BaseModel):
    id: int
    title: str
    goal_type: str
    tracking_method: str
    target: int
    current: int
    start_date: datetime
    end_date: datetime
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class GoalProgress(BaseModel):
    name: str
    current: float
    target: float
    unit: str

class GoalsResponse(BaseModel):
    goals: List[GoalProgress]

class GoalsListResponse(BaseModel):
    goals: List[GoalResponse]