from sqlalchemy import Column, Integer, Float, DateTime
from app.database import Base

class EEGRecord(Base):
    __tablename__ = "eeg_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    timestamp = Column(DateTime, nullable=False)
    focus_label = Column(Float)
    stress_label = Column(Float)
    wellness_label = Column(Float)
    created_at = Column(DateTime)
    created_by = Column(Integer)
    updated_at = Column(DateTime)
    updated_by = Column(Integer)