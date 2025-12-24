from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.database import get_db
from app.services.eeg_aggregation_service import EEGAggregationService
from datetime import datetime, date
from typing import Optional

router = APIRouter(prefix="/admin/aggregation", tags=["admin-aggregation"])

# Request models for body data
class DailyAggregationRequest(BaseModel):
    date: str = Field(..., description="Date in YYYY-MM-DD format")

class MonthlyAggregationRequest(BaseModel):
    year: int = Field(..., description="Year (e.g., 2025)")
    month: int = Field(..., ge=1, le=12, description="Month (1-12)")

class YearlyAggregationRequest(BaseModel):
    year: int = Field(..., description="Year (e.g., 2025)")

@router.post("/daily")
async def trigger_daily_aggregation(
    request: DailyAggregationRequest,
    db: Session = Depends(get_db)
):
    """
    Manually trigger daily aggregation for a specific date
    Send date in request body: {"date": "YYYY-MM-DD"}
    """
    try:
        service = EEGAggregationService(db)
        
        # Parse the date from request body
        parsed_date = datetime.strptime(request.date, "%Y-%m-%d").date()
        
        # Pass the EXACT date to the service with fallback disabled
        await service.process_daily_aggregation(parsed_date, use_fallback=False)
        
        return {
            "message": f"Daily aggregation completed for {request.date}",
            "date": request.date,
            "status": "success"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid date format. Use YYYY-MM-DD. Error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/monthly")
async def trigger_monthly_aggregation(
    request: MonthlyAggregationRequest,
    db: Session = Depends(get_db)
):
    """
    Manually trigger monthly aggregation for a specific year/month
    Send data in request body: {"year": 2025, "month": 8}
    """
    try:
        service = EEGAggregationService(db)
        
        # Pass the EXACT year and month from request body
        await service.process_monthly_aggregation(request.year, request.month)
        
        return {
            "message": f"Monthly aggregation completed for {request.year}-{request.month:02d}",
            "year": request.year,
            "month": request.month,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/yearly")
async def trigger_yearly_aggregation(
    request: YearlyAggregationRequest,
    db: Session = Depends(get_db)
):
    """
    Manually trigger yearly aggregation for a specific year
    Send data in request body: {"year": 2025}
    """
    try:
        service = EEGAggregationService(db)
        
        # Pass the EXACT year from request body
        await service.process_yearly_aggregation(request.year)
        
        return {
            "message": f"Yearly aggregation completed for {request.year}",
            "year": request.year,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_aggregation_status(db: Session = Depends(get_db)):
    """Get status of aggregation tables"""
    try:
        from app.models.eeg_aggregates import DailyEEGRecord, MonthlyEEGRecord, YearlyEEGRecord, EEGRecordsBackup
        
        daily_count = db.query(DailyEEGRecord).count()
        monthly_count = db.query(MonthlyEEGRecord).count()
        yearly_count = db.query(YearlyEEGRecord).count()
        backup_count = db.query(EEGRecordsBackup).count()
        
        return {
            "daily_records": daily_count,
            "monthly_records": monthly_count,
            "yearly_records": yearly_count,
            "backup_records": backup_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
