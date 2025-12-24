from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.schemas.goals import GoalCreate, GoalUpdate, GoalResponse, GoalsListResponse
from app.services.goals_service import GoalsService
from app.models.goals import GoalType, TrackingMethod
from app.core.security import get_current_user_payload
from typing import List

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

@router.post("/goals", response_model=GoalResponse)
def create_goal(
    goal_data: GoalCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_payload)
):
    """Create a new goal for the current user"""
    try:
        print(f"🎯 Creating goal with data: {goal_data.dict()}")
        print(f"🔍 Goal type: '{goal_data.goal_type}' (type: {type(goal_data.goal_type)})")
        print(f"🔍 Tracking method: '{goal_data.tracking_method}' (type: {type(goal_data.tracking_method)})")
        
        # Validate enum values before creating goal
        try:
            goal_type_enum = GoalType(goal_data.goal_type)
            print(f"✅ Goal type enum created: {goal_type_enum}")
        except ValueError as e:
            print(f"❌ Invalid goal type: {goal_data.goal_type}")
            raise HTTPException(status_code=400, detail=f"Invalid goal type: {goal_data.goal_type}")
        
        try:
            tracking_method_enum = TrackingMethod(goal_data.tracking_method)
            print(f"✅ Tracking method enum created: {tracking_method_enum}")
        except ValueError as e:
            print(f"❌ Invalid tracking method: {goal_data.tracking_method}")
            raise HTTPException(status_code=400, detail=f"Invalid tracking method: {goal_data.tracking_method}")
        
        goals_service = GoalsService(db)
        goal = goals_service.create_goal(int(current_user), goal_data)
        print(f"✅ Goal created successfully: {goal.id}")
        return goal
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error creating goal: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/goals", response_model=GoalsListResponse)
def get_goals(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_payload)
):
    """Get all goals for the current user"""
    try:
        goals_service = GoalsService(db)
        goals = goals_service.get_user_goals(int(current_user))
        return GoalsListResponse(goals=goals)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/goals/{goal_id}", response_model=GoalResponse)
def get_goal(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_payload)
):
    """Get a specific goal for the current user"""
    try:
        goals_service = GoalsService(db)
        goal = goals_service.get_goal(int(current_user), goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        return goal
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/goals/{goal_id}", response_model=GoalResponse)
def update_goal(
    goal_id: int,
    goal_data: GoalUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_payload)
):
    """Update a specific goal for the current user"""
    try:
        goals_service = GoalsService(db)
        goal = goals_service.update_goal(int(current_user), goal_id, goal_data)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        return goal
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/goals/{goal_id}")
def delete_goal(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_payload)
):
    """Delete a specific goal for the current user"""
    try:
        goals_service = GoalsService(db)
        success = goals_service.delete_goal(int(current_user), goal_id)
        if not success:
            raise HTTPException(status_code=404, detail="Goal not found")
        return {"message": "Goal deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/goals/current/display")
def get_current_goals_display(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_payload)
):
    """Get formatted goals for HomeScreen display (top 3 goals)"""
    try:
        goals_service = GoalsService(db)
        goals = goals_service.get_current_goals_for_display(int(current_user))
        return {"goals": goals}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/goals/{goal_id}/refresh")
def refresh_goal_progress(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_payload)
):
    """Manually refresh progress for a specific goal"""
    try:
        goals_service = GoalsService(db)
        goal = goals_service.get_goal(int(current_user), goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        # Progress is automatically updated when getting the goal
        return {"message": "Goal progress refreshed", "current": goal.current, "target": goal.target}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))