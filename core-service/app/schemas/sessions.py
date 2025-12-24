from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from enum import Enum


# Priority enum
class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Category(str, Enum):
    ACTION = "action"
    FEELING = "feeling"
    IDEA = "idea"


class TaskCreate(BaseModel):
    text: str
    priority: Priority = Priority.MEDIUM  # Default priority
    category: Category = Category.ACTION
    estimatedMinutes: Optional[int] = None


class TaskUpdate(BaseModel):
    text: Optional[str] = None
    completed: Optional[bool] = None
    priority: Optional[Priority] = None  # Optional priority field
    category: Optional[Category] = None
    estimatedMinutes: Optional[int] = None


class TaskResponse(BaseModel):
    id: int
    text: str
    completed: bool
    priority: str
    category: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    estimatedMinutes: Optional[int] = None

    class Config:
        from_attributes = True  # This allows Pydantic to work with SQLAlchemy models


class SessionHistoryOut(BaseModel):
    date: datetime
    duration: int  # in minutes
    label: str


class EventCreate(BaseModel):
    title: str  # Add title field
    date: datetime
    type: str  # e.g. "workout", "relax"
    turnaround_time: int  # in minutes
    reminder_enabled: bool = False  # Add reminder field with default False


class EventUpdate(BaseModel):
    title: Optional[str] = None
    date: Optional[datetime] = None
    type: Optional[str] = None
    turnaround_time: Optional[int] = None
    reminder_enabled: Optional[bool] = None


class SessionCreate(BaseModel):
    date: datetime
    duration: int
    label: str


class EventOut(BaseModel):
    id: int
    title: str  # Add title field
    date: datetime
    type: str
    turnaround_time: int
    reminder_enabled: bool  # Add reminder field
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
