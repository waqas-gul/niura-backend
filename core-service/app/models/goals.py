from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from app.database import Base
import enum

class GoalType(enum.Enum):
    FOCUS = "focus"
    MEDITATION = "meditation"
    CUSTOM = "custom"

class TrackingMethod(enum.Enum):
    SESSIONS = "sessions"
    MINUTES = "minutes"
    HIGH_FOCUS = "high_focus"
    LOW_STRESS_EPISODES = "low_stress_episodes"

class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    title = Column(String(255), nullable=False)
    goal_type = Column(Enum(GoalType), nullable=False)
    tracking_method = Column(Enum(TrackingMethod), nullable=False)
    target = Column(Integer, nullable=False)
    current = Column(Integer, default=0, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship
  