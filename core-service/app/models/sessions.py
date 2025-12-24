from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Float,
    Boolean,
)  # Add Boolean here
from app.database import Base


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    text = Column(String(255), nullable=False)
    completed = Column(Boolean, default=False, nullable=False)  # Add completed field
    priority = Column(String(10), default="medium", nullable=False)  # Add priority field
    category = Column(String(20), default="action", nullable=False)  
    estimated_minutes = Column(Integer, nullable=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    title = Column(String(255), nullable=False)  # Add title column
    date = Column(DateTime, nullable=False)
    type = Column(String(50), nullable=False)
    turnaround_time = Column(Integer, nullable=False)
    reminder_enabled = Column(
        Boolean, default=False, nullable=False
    )  # Add reminder field
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class Session(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    date = Column(DateTime, nullable=False)
    duration = Column(Integer, nullable=False)
    label = Column(String, nullable=False)
    focus = Column(Float, nullable=True)
    stress = Column(Float, nullable=True)
    wellness = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, onupdate=datetime.now)
