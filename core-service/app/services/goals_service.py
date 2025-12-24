from sqlalchemy.orm import Session
from sqlalchemy import and_, func, extract
from datetime import datetime, timedelta, date
from typing import List, Optional
from app.models.goals import Goal, GoalType, TrackingMethod
from app.models.eeg_record import EEGRecord
from app.models.eeg_aggregates import DailyEEGRecord, MonthlyEEGRecord, YearlyEEGRecord
from app.models.sessions import Session as SessionModel
from app.schemas.goals import GoalCreate, GoalUpdate, GoalResponse
import logging

# Configure logging for goals service
goals_logger = logging.getLogger("goals_service")

class GoalsService:
    def __init__(self, db: Session):
        self.db = db

    def create_goal(self, user_id: int, goal_data: GoalCreate) -> Goal:
        """Create a new goal for the user"""
        db_goal = Goal(
            user_id=user_id,
            title=goal_data.title,
            goal_type=GoalType(goal_data.goal_type),
            tracking_method=TrackingMethod(goal_data.tracking_method),
            target=goal_data.target,
            current=0,  # Always start at 0
            start_date=goal_data.start_date,
            end_date=goal_data.end_date
        )
        
        self.db.add(db_goal)
        self.db.commit()
        self.db.refresh(db_goal)
        
        # Calculate initial progress with proper session management
        self._update_goal_progress_safe(db_goal)
        
        return db_goal

    def get_user_goals(self, user_id: int) -> List[Goal]:
        """Get all goals for a user"""
        goals = self.db.query(Goal).filter(Goal.user_id == user_id).all()
        
        # Update progress for all goals with proper session management
        for goal in goals:
            self._update_goal_progress_safe(goal)
        
        return goals

    def get_goal(self, user_id: int, goal_id: int) -> Optional[Goal]:
        """Get a specific goal for a user"""
        goal = self.db.query(Goal).filter(
            and_(Goal.id == goal_id, Goal.user_id == user_id)
        ).first()
        
        if goal:
            self._update_goal_progress_safe(goal)
        
        return goal

    def update_goal(self, user_id: int, goal_id: int, goal_data: GoalUpdate) -> Optional[Goal]:
        """Update a goal"""
        goal = self.db.query(Goal).filter(
            and_(Goal.id == goal_id, Goal.user_id == user_id)
        ).first()
        
        if not goal:
            return None
        
        # Update fields if provided
        if goal_data.title is not None:
            goal.title = goal_data.title
        if goal_data.goal_type is not None:
            goal.goal_type = GoalType(goal_data.goal_type)
        if goal_data.tracking_method is not None:
            goal.tracking_method = TrackingMethod(goal_data.tracking_method)
        if goal_data.target is not None:
            goal.target = goal_data.target
        if goal_data.current is not None:
            goal.current = goal_data.current
        if goal_data.start_date is not None:
            goal.start_date = goal_data.start_date
        if goal_data.end_date is not None:
            goal.end_date = goal_data.end_date
        
        goal.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(goal)
        
        # Recalculate progress after update with proper session management
        self._update_goal_progress_safe(goal)
        
        return goal

    def delete_goal(self, user_id: int, goal_id: int) -> bool:
        """Delete a goal"""
        goal = self.db.query(Goal).filter(
            and_(Goal.id == goal_id, Goal.user_id == user_id)
        ).first()
        
        if not goal:
            return False
        
        self.db.delete(goal)
        self.db.commit()
        return True

    def _update_goal_progress_safe(self, goal: Goal) -> None:
        """
        Safely update goal progress using the existing database session
        This prevents connection leaks by reusing the current session
        """
        try:
            if goal.tracking_method == TrackingMethod.SESSIONS:
                progress = self._calculate_sessions_progress(goal)
            elif goal.tracking_method == TrackingMethod.MINUTES:
                progress = self._calculate_minutes_progress(goal)
            elif goal.tracking_method == TrackingMethod.HIGH_FOCUS:
                progress = self._calculate_high_focus_progress(goal)
            elif goal.tracking_method == TrackingMethod.LOW_STRESS_EPISODES:
                progress = self._calculate_low_stress_episodes_progress(goal)
            else:
                progress = goal.current  # Keep manual progress
            
            if progress != goal.current:
                goal.current = progress
                # Use existing session instead of committing here
                # The commit will happen in the calling method
                self.db.flush()  # Flush changes without committing
                
        except Exception as e:
            goals_logger.error(f"Error updating goal progress for goal {goal.id}: {e}")
            # Don't raise - just log and continue with existing progress

    def _update_goal_progress(self, goal: Goal) -> None:
        """Update goal progress based on tracking method"""
        if goal.tracking_method == TrackingMethod.SESSIONS:
            progress = self._calculate_sessions_progress(goal)
        elif goal.tracking_method == TrackingMethod.MINUTES:
            progress = self._calculate_minutes_progress(goal)
        elif goal.tracking_method == TrackingMethod.HIGH_FOCUS:
            progress = self._calculate_high_focus_progress(goal)
        elif goal.tracking_method == TrackingMethod.LOW_STRESS_EPISODES:
            progress = self._calculate_low_stress_episodes_progress(goal)
        else:
            progress = goal.current  # Keep manual progress
        
        if progress != goal.current:
            goal.current = progress
            self.db.commit()

    def _calculate_sessions_progress(self, goal: Goal) -> int:
        """
        Scenario 1: Calculate progress based on completed sessions in sessions table
        Goal Type: Focus/Meditation + Tracking Method: Sessions
        Only counts sessions created AFTER the goal was created
        """
        try:
            # Count sessions in the date range for the user using existing session
            # Only count sessions that were created after the goal was created
            sessions_count = self.db.query(SessionModel).filter(
                and_(
                    SessionModel.user_id == goal.user_id,
                    SessionModel.date >= goal.start_date.date(),
                    SessionModel.date <= goal.end_date.date(),
                    SessionModel.created_at >= goal.created_at  # Only count sessions after goal creation
                )
            ).count()
            
            return min(sessions_count, goal.target)
        except Exception as e:
            goals_logger.error(f"Error calculating sessions progress: {e}")
            return goal.current  # Return existing progress on error

    def _calculate_minutes_progress(self, goal: Goal) -> int:
        """
        Scenario 2: Calculate progress based on focus/meditation minutes from EEG records
        Goal Type: Focus/Meditation + Tracking Method: Minutes
        Only counts EEG records created AFTER the goal was created
        """
        try:
            # Get all EEG records in the date range AND after goal creation using existing session
            eeg_records = self.db.query(EEGRecord).filter(
                and_(
                    EEGRecord.user_id == goal.user_id,
                    EEGRecord.timestamp >= goal.start_date,
                    EEGRecord.timestamp <= goal.end_date,
                    EEGRecord.timestamp >= goal.created_at  # Only count records after goal creation
                )
            ).all()
            
            # Count minutes based on goal type
            total_minutes = 0
            for record in eeg_records:
                if goal.goal_type == GoalType.FOCUS:
                    # Count any focus activity (focus_label > 0)
                    if record.focus_label and record.focus_label > 0:
                        total_minutes += 1  # Each record represents 1 minute
                elif goal.goal_type == GoalType.MEDITATION:
                    # For meditation, we'll count low stress + moderate focus as meditation minutes
                    if (record.stress_label and record.stress_label < 2.0 and 
                        record.focus_label and record.focus_label > 1.0):
                        total_minutes += 1
                else:  # CUSTOM
                    # For custom goals, count any activity
                    if (record.focus_label and record.focus_label > 0) or (record.stress_label and record.stress_label > 0):
                        total_minutes += 1
            
            return min(total_minutes, goal.target)
        except Exception as e:
            goals_logger.error(f"Error calculating minutes progress: {e}")
            return goal.current  # Return existing progress on error

    def _calculate_high_focus_progress(self, goal: Goal) -> int:
        """
        Scenario 3: Calculate progress based on high focus minutes (focus > 2.0)
        Goal Type: Focus/Meditation + Tracking Method: High Focus
        Uses live EEG data for current day and aggregated data for previous days
        Only counts data created AFTER the goal was created
        """
        try:
            # Convert goal dates to date objects for comparison
            start_date = goal.start_date.date() if isinstance(goal.start_date, datetime) else goal.start_date
            end_date = goal.end_date.date() if isinstance(goal.end_date, datetime) else goal.end_date
            today = datetime.utcnow().date()
            goal_created_date = goal.created_at.date() if isinstance(goal.created_at, datetime) else goal.created_at
            
            high_focus_count = 0
            
            # For previous days, use daily aggregated data (only days after goal creation)
            if start_date < today:
                previous_end = min(end_date, today - timedelta(days=1))
                # Only consider days on or after the goal creation date
                effective_start = max(start_date, goal_created_date)
                
                if effective_start <= previous_end:
                    high_focus_days = self.db.query(DailyEEGRecord).filter(
                        and_(
                            DailyEEGRecord.user_id == goal.user_id,
                            DailyEEGRecord.date >= effective_start,
                            DailyEEGRecord.date <= previous_end,
                            DailyEEGRecord.focus > 2.0
                        )
                    ).count()
                    high_focus_count += high_focus_days
            
            # For current day, use live EEG records (only after goal creation timestamp)
            if start_date <= today <= end_date:
                today_start = max(
                    datetime.combine(today, datetime.min.time()),
                    goal.created_at  # Only count records after goal creation
                )
                today_end = datetime.combine(today, datetime.max.time())
                
                today_high_focus = self.db.query(EEGRecord).filter(
                    and_(
                        EEGRecord.user_id == goal.user_id,
                        EEGRecord.timestamp >= today_start,
                        EEGRecord.timestamp <= today_end,
                        EEGRecord.focus_label > 2.0
                    )
                ).count()
                
                # Convert records to meaningful units (e.g., minutes)
                high_focus_minutes = today_high_focus // 60  # Assuming 1 record per second
                if high_focus_minutes > 0:
                    high_focus_count += 1
            
            return min(high_focus_count, goal.target)
        except Exception as e:
            goals_logger.error(f"Error calculating high focus progress: {e}")
            return goal.current  # Return existing progress on error

    def _calculate_low_stress_episodes_progress(self, goal: Goal) -> int:
        """
        Scenario 4: Calculate progress based on low stress minutes (stress < 1.0)
        Goal Type: Focus/Meditation + Tracking Method: Low Stress Episodes
        Uses live EEG data for current day and aggregated data for previous days
        Only counts data created AFTER the goal was created
        """
        try:
            # Convert goal dates to date objects for comparison
            start_date = goal.start_date.date() if isinstance(goal.start_date, datetime) else goal.start_date
            end_date = goal.end_date.date() if isinstance(goal.end_date, datetime) else goal.end_date
            today = datetime.utcnow().date()
            goal_created_date = goal.created_at.date() if isinstance(goal.created_at, datetime) else goal.created_at
            
            low_stress_count = 0
            
            # For previous days, use daily aggregated data (only days after goal creation)
            if start_date < today:
                previous_end = min(end_date, today - timedelta(days=1))
                # Only consider days on or after the goal creation date
                effective_start = max(start_date, goal_created_date)
                
                if effective_start <= previous_end:
                    low_stress_days = self.db.query(DailyEEGRecord).filter(
                        and_(
                            DailyEEGRecord.user_id == goal.user_id,
                            DailyEEGRecord.date >= effective_start,
                            DailyEEGRecord.date <= previous_end,
                            DailyEEGRecord.stress < 1.0
                        )
                    ).count()
                    low_stress_count += low_stress_days
            
            # For current day, use live EEG records (only after goal creation timestamp)
            if start_date <= today <= end_date:
                today_start = max(
                    datetime.combine(today, datetime.min.time()),
                    goal.created_at  # Only count records after goal creation
                )
                today_end = datetime.combine(today, datetime.max.time())
                
                today_low_stress = self.db.query(EEGRecord).filter(
                    and_(
                        EEGRecord.user_id == goal.user_id,
                        EEGRecord.timestamp >= today_start,
                        EEGRecord.timestamp <= today_end,
                        EEGRecord.stress_label < 1.0
                    )
                ).count()
                
                # Convert records to meaningful units (e.g., minutes)
                low_stress_minutes = today_low_stress // 60  # Assuming 1 record per second
                if low_stress_minutes > 0:
                    low_stress_count += 1
            
            return min(low_stress_count, goal.target)
        except Exception as e:
            goals_logger.error(f"Error calculating low stress episodes progress: {e}")
            return goal.current  # Return existing progress on error

    def get_current_goals_for_display(self, user_id: int) -> List[dict]:
        """Get goals formatted for the current HomeScreen display"""
        try:
            goals = self.get_user_goals(user_id)
            
            # Convert to the format expected by the HomeScreen
            formatted_goals = []
            for goal in goals[:3]:  # Only return top 3 goals
                unit_map = {
                    TrackingMethod.SESSIONS: "sessions",
                    TrackingMethod.MINUTES: "mins",
                    TrackingMethod.HIGH_FOCUS: "mins",
                    TrackingMethod.LOW_STRESS_EPISODES: "mins"
                }
                
                formatted_goals.append({
                    "name": goal.title,
                    "current": goal.current,
                    "target": goal.target,
                    "unit": unit_map.get(goal.tracking_method, "units")
                })
            
            return formatted_goals
        except Exception as e:
            goals_logger.error(f"Error getting current goals for display: {e}")
            # Return empty list on error to prevent crashes
            return []