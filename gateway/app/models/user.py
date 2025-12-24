from sqlalchemy import Column, Integer, String, Text, Boolean, Date, TIMESTAMP, Float, func
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    gender = Column(String(10), nullable=False)  # <-- make gender required
    
    role = Column(String(50), nullable=False, default="user")
    
    dob = Column(Date, nullable=True)
    nationality = Column(String(100), nullable=True)
    phone = Column(String(20), unique=True, nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    occupation = Column(String(255), nullable=True)
    marital_status = Column(String(20), nullable=True)
    sleep_hours = Column(Integer, nullable=True)
    exercise_frequency = Column(String(50), nullable=True)
    smoking_status = Column(Boolean, nullable=True)
    alcohol_consumption = Column(Boolean, nullable=True)
    focus_threshold = Column(Float, default=2.0)
    stress_threshold = Column(Float, default=2.0)

    # # Soft delete fields
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(TIMESTAMP, nullable=True)
    
    # Forgot password field - stores timestamp-based code
    forgot_password_code = Column(String(50), nullable=True)  # Length increased to accommodate base64-encoded codes
    
    created_at = Column(TIMESTAMP, server_default=func.now())
    created_by = Column(Integer, nullable=True)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    updated_by = Column(Integer, nullable=True)

