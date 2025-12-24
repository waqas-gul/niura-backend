from sqlalchemy import Column, Integer, Float, Date,  Index
from app.database import Base

class DailyEEGRecord(Base):
    __tablename__ = "daily_eeg_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    date = Column(Date, nullable=False)
    focus = Column(Float, nullable=False)
    stress = Column(Float, nullable=False)
    wellness = Column(Float, nullable=False)
    

    __table_args__ = (
        Index('idx_daily_user_date', 'user_id', 'date'),
    )

class MonthlyEEGRecord(Base):
    __tablename__ = "monthly_eeg_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    focus = Column(Float, nullable=False)
    stress = Column(Float, nullable=False)
    wellness = Column(Float, nullable=False)
    
    
    __table_args__ = (
        Index('idx_monthly_user_year_month', 'user_id', 'year', 'month'),
    )

class YearlyEEGRecord(Base):
    __tablename__ = "yearly_eeg_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    year = Column(Integer, nullable=False)
    focus = Column(Float, nullable=False)
    stress = Column(Float, nullable=False)
    wellness = Column(Float, nullable=False)
    

    
    __table_args__ = (
        Index('idx_yearly_user_year', 'user_id', 'year'),
    )

class EEGRecordsBackup(Base):
    __tablename__ = "eeg_records_backup"

    id = Column(Integer, primary_key=True, index=True)
    original_id = Column(Integer, nullable=False)
    user_id = Column(Integer, index=True)
    timestamp = Column(Date, nullable=False)
    focus_label = Column(Float)
    stress_label = Column(Float)
    wellness_label = Column(Float)
    backup_date = Column(Date, nullable=False)
    

    
    __table_args__ = (
        Index('idx_backup_user_date', 'user_id', 'backup_date'),
        Index('idx_backup_timestamp', 'timestamp'),
    )
