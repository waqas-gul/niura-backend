from pydantic import BaseModel, EmailStr
from typing import Any, Dict, Optional
from datetime import date, datetime

class UserBase(BaseModel):
    full_name: str
    email: EmailStr
    gender: str
    role:Optional[str]="user"
    dob: Optional[date] = None
    nationality: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    occupation: Optional[str] = None
    marital_status: Optional[str] = None
    sleep_hours: Optional[int] = None
    exercise_frequency: Optional[str] = None
    smoking_status: Optional[bool] = None
    alcohol_consumption: Optional[bool] = None
    focus_threshold: Optional[int]=2
    stress_threshold: Optional[int]=2

class UserCreate(UserBase):
    password: str
    role: str = "user" 
   

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = None  # still allow password updates
    email: Optional[EmailStr] = None
    gender: Optional[str] = None
    dob: Optional[date] = None
    nationality: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    occupation: Optional[str] = None
    marital_status: Optional[str] = None
    sleep_hours: Optional[int] = None
    exercise_frequency: Optional[str] = None
    smoking_status: Optional[bool] = None
    alcohol_consumption: Optional[bool] = None

class UserOut(BaseModel):
    id: int
    full_name: str
    email: str
    gender: Optional[str] = None
    focus_threshold: int
    stress_threshold: int
    created_at: datetime
    class Config:
        from_attributes = True

class ResponseModel(BaseModel):
    code: str
    message: str
    data: Optional[Dict[str, Any]] = None        

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class EmailRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str