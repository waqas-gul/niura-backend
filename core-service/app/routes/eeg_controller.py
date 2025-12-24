from datetime import datetime, timedelta
import logging
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from typing import List, Dict, Any
from app.models.sessions import (
    Event,
    Session,
)  # or the correct path to your Session model
from sqlalchemy.orm import Session as DBSession  # for the DB session dependency
from app.database import get_db
from app.core.security import get_current_user_payload
from app.schemas.goals import (
    GoalsResponse,
    GoalCreate,
    GoalUpdate,
    GoalResponse,
    GoalsListResponse,
)
from app.schemas.sessions import (
    EventCreate,
    EventOut,
    SessionCreate,
    SessionHistoryOut,
    EventUpdate,
)
from app.services.eeg_service import EEGService
from app.services.goals_service import GoalsService
from app.schemas.eeg import EEGBatchIn
from app.models.eeg_record import EEGRecord
from app.schemas.eeg import EEGRecordOut
from app.schemas.recommendation import RecommendationsResponse
from app.services.session_service import SessionService
from app.models.sessions import Task
from app.schemas.sessions import TaskCreate, TaskResponse, TaskUpdate
from app.schemas.session_tracking import SessionTrackingRequest
from pydantic import BaseModel
from sqlalchemy import and_, func  # Add func import here
from datetime import timezone

router = APIRouter()


class ThresholdUpdateRequest(BaseModel):
    focus_threshold: float
    stress_threshold: float


@router.get("/eeg/records")
def get_eeg_records(
    limit: int = Query(100, description="Number of records to retrieve"),
    db: DBSession = Depends(get_db),
    current_user=Depends(get_current_user_payload),
):
    """Get EEG records for the current user"""
    user_id = int(current_user.get("sub"))

    records = (
        db.query(EEGRecord)
        .filter(EEGRecord.user_id == user_id)
        .order_by(EEGRecord.timestamp.desc())
        .limit(limit)
        .all()
    )

    return {
        "records": [EEGRecordOut.from_orm(record) for record in records],
        "count": len(records),
    }


@router.get("/eeg/latest", response_model=EEGRecordOut)
def get_latest_eeg_label(
    db: Session = Depends(get_db), current_user=Depends(get_current_user_payload)
):
    user_id = int(current_user.get("sub"))

    # Get start and end of today
    now = datetime.now()
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_today = start_of_today + timedelta(days=1)

    record = (
        db.query(EEGRecord)
        .filter(
            EEGRecord.user_id == user_id,
            EEGRecord.timestamp >= start_of_today,
            EEGRecord.timestamp < end_of_today,
        )
        .order_by(EEGRecord.timestamp.desc())
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="No EEG record found for today")
    return record


@router.get("/eeg/recommendations")
def get_recommendations(
    db: Session = Depends(get_db), current_user=Depends(get_current_user_payload)
):
    user_id = int(current_user.get("sub"))

    service = EEGService(db)
    recommendations = service.get_recommendations(user_id)

    # Always return an array, even if empty
    return {"recommendations": recommendations if recommendations else []}


@router.get("/eeg/aggregate", response_model=Dict[str, Any])
def get_eeg_aggregated(
    range: str = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_payload),
):
    user_id = int(current_user.get("sub"))

    service = EEGService(db)
    result = service.get_aggregated_data(user_id, range)
    return result


@router.get("/eeg/best-focus-time")
def get_best_focus_time(
    db: Session = Depends(get_db), current_user=Depends(get_current_user_payload)
):
    user_id = int(current_user.get("sub"))

    service = EEGService(db)
    return service.get_best_focus_time(user_id)


@router.get("/music-suggestion")
def get_music_suggestion(
    db: Session = Depends(get_db), current_user=Depends(get_current_user_payload)
):
    user_id = int(current_user.get("sub"))

    service = EEGService(db)
    return service.suggest_music(user_id)


@router.get("/current-goals", response_model=GoalsResponse)
def get_current_goals(
    db: Session = Depends(get_db), current_user=Depends(get_current_user_payload)
):
    user_id = int(current_user.get("sub"))

    # Use the new goals service instead of the old EEG service method
    goals_service = GoalsService(db)
    goals = goals_service.get_current_goals_for_display(user_id)
    return {"goals": goals}


# New Goals CRUD endpoints
@router.post("/goals", response_model=GoalResponse)
def create_goal(
    goal_data: GoalCreate,
    db: DBSession = Depends(get_db),
    current_user=Depends(get_current_user_payload),
):
    """Create a new goal"""
    user_id = int(current_user.get("sub"))

    goals_service = GoalsService(db)
    try:
        new_goal = goals_service.create_goal(user_id, goal_data)
        return new_goal
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/goals", response_model=GoalsListResponse)
def get_goals(
    db: DBSession = Depends(get_db), current_user=Depends(get_current_user_payload)
):
    """Get all goals for the current user"""
    user_id = int(current_user.get("sub"))

    goals_service = GoalsService(db)
    goals = goals_service.get_user_goals(user_id)
    return {"goals": goals}


@router.get("/goals/{goal_id}", response_model=GoalResponse)
def get_goal(
    goal_id: int,
    db: DBSession = Depends(get_db),
    current_user=Depends(get_current_user_payload),
):
    """Get a specific goal"""
    user_id = int(current_user.get("sub"))

    goals_service = GoalsService(db)
    goal = goals_service.get_goal(user_id, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@router.put("/goals/{goal_id}", response_model=GoalResponse)
def update_goal(
    goal_id: int,
    goal_data: GoalUpdate,
    db: DBSession = Depends(get_db),
    current_user=Depends(get_current_user_payload),
):
    """Update a goal"""
    user_id = int(current_user.get("sub"))

    goals_service = GoalsService(db)
    updated_goal = goals_service.update_goal(user_id, goal_id, goal_data)
    if not updated_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return updated_goal


@router.delete("/goals/{goal_id}")
def delete_goal(
    goal_id: int,
    db: DBSession = Depends(get_db),
    current_user=Depends(get_current_user_payload),
):
    """Delete a goal"""
    user_id = int(current_user.get("sub"))

    goals_service = GoalsService(db)
    success = goals_service.delete_goal(user_id, goal_id)
    if not success:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"message": "Goal deleted successfully"}


@router.post("/sessions/create")
def create_session(
    session: SessionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_payload),
):
    user_id = int(current_user.get("sub"))
    now = datetime.now()
    new_session = Session(
        user_id=user_id,
        date=session.date,
        duration=session.duration,
        label=session.label,
        created_at=now,
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return {"message": "Session created", "session_id": new_session.id}


@router.post("/eeg/session-labels")
def process_eeg_session(
    batch: EEGBatchIn,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_payload),
):
    user_id = int(current_user.get("sub"))
    service = EEGService(db)
    labels = service.process_and_label_records(batch.records, user_id)
    return {"labels": labels, "duration": batch.duration}


@router.get("/sessions/history", response_model=List[SessionHistoryOut])
def get_session_history(
    db: Session = Depends(get_db), current_user=Depends(get_current_user_payload)
):
    user_id = int(current_user.get("sub"))
    service = SessionService(db)
    return service.get_session_history(user_id)


@router.post("/events")
def add_event(
    event: EventCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_payload),
):
    user_id = int(current_user.get("sub"))

    new_event = Event(
        user_id=user_id,
        title=event.title,  # Add title field
        date=event.date,
        type=event.type,
        turnaround_time=event.turnaround_time,
        reminder_enabled=event.reminder_enabled,  # Add reminder field
        created_at=datetime.now(),
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return {"message": "Event added", "event": new_event.id}


@router.put("/events/{event_id}")
def update_event(
    event_id: int,
    event_update: EventUpdate,  # Changed from EventCreate to EventUpdate
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_payload),
):
    user_id = int(current_user.get("sub"))

    event = (
        db.query(Event).filter(Event.id == event_id, Event.user_id == user_id).first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Only update fields that are provided (not None)
    if event_update.title is not None:
        event.title = event_update.title
    if event_update.date is not None:
        event.date = event_update.date
    if event_update.type is not None:
        event.type = event_update.type
    if event_update.turnaround_time is not None:
        event.turnaround_time = event_update.turnaround_time
    if event_update.reminder_enabled is not None:
        event.reminder_enabled = event_update.reminder_enabled

    event.updated_at = datetime.now()
    db.commit()
    db.refresh(event)
    return {"message": "Event updated", "event": event.id}


@router.delete("/events/{event_id}")
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_payload),
):
    user_id = int(current_user.get("sub"))

    event = (
        db.query(Event).filter(Event.id == event_id, Event.user_id == user_id).first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    db.delete(event)
    db.commit()
    return {"message": "Event deleted"}


@router.get("/events", response_model=List[EventOut])
def get_events(
    db: Session = Depends(get_db), current_user=Depends(get_current_user_payload)
):
    user_id = int(current_user.get("sub"))
    events = (
        db.query(Event)
        .filter(Event.user_id == user_id)
        .order_by(Event.date.desc())
        .all()
    )
    return events


# Add Tasks
@router.post("/tasks")
def add_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_payload),
):
    user_id = int(current_user.get("sub"))
    new_task = Task(
        user_id=user_id,
        text=task.text,
        priority=task.priority.value,
        category=task.category.value,
        estimated_minutes=task.estimatedMinutes,
        completed=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return {
        "id": new_task.id,
        "text": new_task.text,
        "completed": new_task.completed,
        "priority": new_task.priority,
        "category": new_task.category,
        "estimatedMinutes": new_task.estimated_minutes,
        "created_at": new_task.created_at.isoformat(),
        "updated_at": new_task.updated_at.isoformat(),
    }


# Get All Tasks
@router.get(
    "/tasks", response_model=List[TaskResponse]
)  # Changed from TaskCreate to TaskResponse
def get_tasks(
    db: Session = Depends(get_db), current_user=Depends(get_current_user_payload)
):
    user_id = int(current_user.get("sub"))
    tasks = (
        db.query(Task)
        .filter(Task.user_id == user_id)
        .order_by(Task.created_at.desc())
        .all()
    )
    return tasks


# Update Task
@router.patch("/tasks/{task_id}")
def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_payload),
):
    user_id = int(current_user.get("sub"))

    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task_update.text is not None:
        task.text = task_update.text

    if task_update.completed is not None:
        task.completed = task_update.completed

    if task_update.priority is not None:
        task.priority = task_update.priority.value

    task.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(task)

    return {
        "id": task.id,
        "text": task.text,
        "completed": task.completed,
        "priority": task.priority,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    }


# Delete all tasks for specfic user
@router.delete("/tasks/clear")
def delete_all_tasks(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_payload),
):
    user_id = int(current_user.get("sub"))

    deleted_count = (
        db.query(Task).filter(Task.user_id == user_id).delete(synchronize_session=False)
    )

    db.commit()

    return {"message": "All tasks deleted successfully", "deleted_count": deleted_count}


# Delete Task
@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_payload),
):
    user_id = int(current_user.get("sub"))

    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"message": "Task deleted"}


# Update Session - PUT /api/sessions/{session_id}
@router.put("/sessions/{session_id}")
def update_session(
    session_id: int,
    session_update: dict,  # Allow flexible updates
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_payload),
):
    user_id = int(current_user.get("sub"))

    session = (
        db.query(Session)
        .filter(Session.id == session_id, Session.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Update allowed fields
    if "duration" in session_update:
        session.duration = session_update["duration"]
    if "label" in session_update:
        session.label = session_update["label"]
    if "date" in session_update:
        session.date = session_update["date"]

    session.updated_at = datetime.now()
    db.commit()
    db.refresh(session)
    return {"message": "Session updated", "session_id": session.id}


@router.get("/aggregate-by-time-of-day")
def get_eeg_aggregate_by_time_of_day(
    db: DBSession = Depends(get_db), current_user=Depends(get_current_user_payload)
):
    user_id = int(current_user.get("sub"))
    service = EEGService(db)
    result = service.get_time_of_day_aggregate(user_id)
    return result

from datetime import datetime, timezone


@router.post("/sessions/track")
def track_session(
    request: SessionTrackingRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_payload),
):
    """
    Process session tracking data with timestamps and calculate focus, stress, wellness metrics.
    Prioritizes user-provided duration over calculated timestamp duration.
    """

    # Authenticate user
    user_id = int(current_user.get("sub"))

    # ---- helper: normalize incoming datetimes to UTC-naive to match DB 'timestamp without time zone'
    def to_utc_naive(dt: datetime | None) -> datetime | None:
        if not dt:
            return None
        if dt.tzinfo is not None:  # tz-aware -> UTC then drop tzinfo
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt  # already naive

    try:
        session_data = request.session_data

        # ---- helper: parse duration input into seconds
        def parse_duration_to_seconds(duration_input):
            if duration_input is None:
                return None
            duration_str = str(duration_input).strip().lower()
            if duration_str.replace(".", "").isdigit():
                return int(float(duration_str))
            import re

            m = re.match(
                r"^(\d+(?:\.\d+)?)\s*(s|sec|second|seconds|m|min|minute|minutes|h|hr|hour|hours)?$",
                duration_str,
            )
            if m:
                value = float(m.group(1))
                unit = m.group(2) or "s"
                if unit in ["s", "sec", "second", "seconds"]:
                    return int(value)
                if unit in ["m", "min", "minute", "minutes"]:
                    return int(value * 60)
                if unit in ["h", "hr", "hour", "hours"]:
                    return int(value * 3600)
            try:
                return int(float(duration_str))
            except Exception:
                return None

        # 1) Determine duration in seconds - prioritize user input
        user_duration_seconds = parse_duration_to_seconds(session_data.duration)

        if user_duration_seconds is not None:
            total_duration_seconds = user_duration_seconds
            print(f"Using user-provided duration: {total_duration_seconds} seconds")
        else:
            # Fall back to calculated duration from timestamps (normalize datetimes!)
            total_duration_seconds = 0
            for interval in session_data.timestamps:
                start = to_utc_naive(interval.start)
                end = to_utc_naive(interval.end)
                if end is not None:
                    total_duration_seconds += (end - start).total_seconds()
            total_duration_seconds = int(total_duration_seconds)
            print(
                f"Using calculated duration from timestamps: {total_duration_seconds} seconds"
            )

        # 2) Collect EEG records from timestamps (normalize datetimes!)
        all_eeg_records = []
        for interval in session_data.timestamps:
            start = to_utc_naive(interval.start)
            end = to_utc_naive(interval.end)
            if end is None:
                continue

            # Optional: quick log to verify the window used
            print("Querying EEG between:", start.isoformat(), "and", end.isoformat())

            records = (
                db.query(EEGRecord)
                .filter(
                    and_(
                        EEGRecord.user_id == user_id,
                        EEGRecord.timestamp >= start,
                        EEGRecord.timestamp <= end,
                    )
                )
                .order_by(EEGRecord.timestamp.asc())
                .all()
            )
            all_eeg_records.extend(records)

        # 3) Aggregate EEG data by second and average labels
        seconds_data: dict[datetime, dict] = {}
        for rec in all_eeg_records:
            key = rec.timestamp.replace(microsecond=0)
            bucket = seconds_data.setdefault(
                key,
                {
                    "focus_values": [],
                    "stress_values": [],
                    "wellness_values": [],
                    "timestamp": key,
                },
            )
            if rec.focus_label is not None:
                bucket["focus_values"].append(rec.focus_label)
            if rec.stress_label is not None:
                bucket["stress_values"].append(rec.stress_label)
            if rec.wellness_label is not None:
                bucket["wellness_values"].append(rec.wellness_label)

        # Helper function to aggregate data for frontend graphs
        # If duration <= 10 seconds, return actual timestamps
        # If duration > 10 seconds, aggregate into exactly 10 points
        def aggregate_for_frontend_graph(seconds_data_dict):
            if not seconds_data_dict:
                return [], [], [], []

            sorted_keys = sorted(seconds_data_dict.keys())
            total_points = len(sorted_keys)

            # If we have 10 or fewer points (e.g., 3, 5, 8, 10 seconds), return all actual timestamps
            if total_points <= 10:
                focus_data, stress_data, wellness_data, timestamps = [], [], [], []
                for key in sorted_keys:
                    info = seconds_data_dict[key]
                    avg_f = (
                        sum(info["focus_values"]) / len(info["focus_values"])
                        if info["focus_values"]
                        else 0
                    )
                    avg_s = (
                        sum(info["stress_values"]) / len(info["stress_values"])
                        if info["stress_values"]
                        else 0
                    )
                    avg_w = (
                        sum(info["wellness_values"]) / len(info["wellness_values"])
                        if info["wellness_values"]
                        else 0
                    )
                    focus_data.append(avg_f)
                    stress_data.append(avg_s)
                    wellness_data.append(avg_w)
                    timestamps.append(key.strftime("%Y-%m-%dT%H:%M:%S"))
                return focus_data, stress_data, wellness_data, timestamps

            # For longer durations (e.g., 110 seconds, 1 hour), aggregate into exactly 10 buckets
            focus_data, stress_data, wellness_data, timestamps = [], [], [], []
            bucket_size = total_points / 10

            for i in range(10):
                start_idx = int(i * bucket_size)
                end_idx = int((i + 1) * bucket_size) if i < 9 else total_points

                bucket_focus_values = []
                bucket_stress_values = []
                bucket_wellness_values = []
                bucket_timestamps = []

                # Collect all values in this bucket
                for idx in range(start_idx, end_idx):
                    key = sorted_keys[idx]
                    info = seconds_data_dict[key]

                    if info["focus_values"]:
                        bucket_focus_values.extend(info["focus_values"])
                    if info["stress_values"]:
                        bucket_stress_values.extend(info["stress_values"])
                    if info["wellness_values"]:
                        bucket_wellness_values.extend(info["wellness_values"])
                    bucket_timestamps.append(key)

                # Calculate averages for this bucket
                avg_focus = (
                    sum(bucket_focus_values) / len(bucket_focus_values)
                    if bucket_focus_values
                    else 0
                )
                avg_stress = (
                    sum(bucket_stress_values) / len(bucket_stress_values)
                    if bucket_stress_values
                    else 0
                )
                avg_wellness = (
                    sum(bucket_wellness_values) / len(bucket_wellness_values)
                    if bucket_wellness_values
                    else 0
                )

                # Use the middle timestamp of the bucket as representative timestamp
                middle_timestamp = (
                    bucket_timestamps[len(bucket_timestamps) // 2]
                    if bucket_timestamps
                    else sorted_keys[start_idx]
                )

                focus_data.append(avg_focus)
                stress_data.append(avg_stress)
                wellness_data.append(avg_wellness)
                timestamps.append(middle_timestamp.strftime("%Y-%m-%dT%H:%M:%S"))

            return focus_data, stress_data, wellness_data, timestamps

        # Get aggregated data for frontend graphing
        all_focus, all_stress, all_wellness, all_timestamps = (
            aggregate_for_frontend_graph(seconds_data)
        )

        # Determine if data was aggregated or returned as-is
        was_aggregated = len(seconds_data) > 10

        # Calculate overall averages from all raw data (not just the 10 points)
        all_focus_raw, all_stress_raw, all_wellness_raw = [], [], []
        for key in sorted(seconds_data.keys()):
            info = seconds_data[key]
            if info["focus_values"]:
                all_focus_raw.extend(info["focus_values"])
            if info["stress_values"]:
                all_stress_raw.extend(info["stress_values"])
            if info["wellness_values"]:
                all_wellness_raw.extend(info["wellness_values"])

        overall_avg_focus = (
            sum(all_focus_raw) / len(all_focus_raw) if all_focus_raw else 0
        )
        overall_avg_stress = (
            sum(all_stress_raw) / len(all_stress_raw) if all_stress_raw else 0
        )
        overall_avg_wellness = (
            sum(all_wellness_raw) / len(all_wellness_raw) if all_wellness_raw else 0
        )

        # 4) Compute hours, minutes, seconds from total duration
        duration_seconds = int(total_duration_seconds)
        hours = duration_seconds // 3600
        minutes = (duration_seconds % 3600) // 60
        seconds = duration_seconds % 60

        # 5) Persist session (store UTC now)
        now = datetime.now(timezone.utc)
        new_session = Session(  # rename if your SQLAlchemy model is named 'Session'
            user_id=user_id,
            date=now,
            duration=duration_seconds,  # stored in seconds
            label=session_data.label,
            focus=overall_avg_focus,
            stress=overall_avg_stress,
            wellness=overall_avg_wellness,
            created_at=now,
            updated_at=now,
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)

        # 6) Return aggregated breakdown (intelligent aggregation based on duration)
        return {
            "message": "Session tracked successfully",
            "session_id": new_session.id,
            "duration_seconds": duration_seconds,
            "duration_minutes": duration_seconds // 60,
            "duration_hours": hours,
            "duration_readable": f"{hours}h {minutes}m {seconds}s",
            "duration_source": "user_provided"
            if user_duration_seconds is not None
            else "calculated_from_timestamps",
            "avg_focus": overall_avg_focus,
            "avg_stress": overall_avg_stress,
            "avg_wellness": overall_avg_wellness,
            "eeg_records_count": len(all_eeg_records),  # raw rows matched
            "aggregated_data_points": len(all_focus),  # number of points returned
            "was_aggregated": was_aggregated,  # true if data was averaged, false if actual timestamps returned
            "focus_data": all_focus,
            "stress_data": all_stress,
            "wellness_data": all_wellness,
            "timestamps": all_timestamps,
        }

    except Exception as e:
        logging.exception(f"Error tracking session: {e}")
        raise HTTPException(status_code=500, detail=f"Error tracking session: {e}")


@router.get("/sessions/{session_id}/details")
def get_session_details(
    session_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_payload),
):
    """
    Get detailed session metrics with EEG data for plotting focus/stress trends
    """
    user_id = int(current_user.get("sub"))

    # Get session record
    session = (
        db.query(Session)
        .filter(Session.id == session_id, Session.user_id == user_id)
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get EEG records for the session time period
    # We'll get records from session start time to end time
    session_start = session.date
    session_end = datetime.combine(
        session.date.date(), session.date.time()
    ) + timedelta(minutes=session.duration)

    eeg_records = (
        db.query(EEGRecord)
        .filter(
            and_(
                EEGRecord.user_id == user_id,
                EEGRecord.timestamp >= session_start,
                EEGRecord.timestamp <= session_end,
            )
        )
        .order_by(EEGRecord.timestamp.asc())
        .all()
    )

    # Helper function to aggregate EEG data for frontend graphs
    # If records <= 10, return actual timestamps
    # If records > 10, aggregate into exactly 10 points
    def aggregate_eeg_for_frontend_graph(eeg_records_list):
        if not eeg_records_list:
            return [], [], [], []

        total_records = len(eeg_records_list)

        # If we have 10 or fewer records (short duration), return all actual timestamps
        if total_records <= 10:
            focus_data, stress_data, wellness_data, timestamps = [], [], [], []
            for record in eeg_records_list:
                if record.focus_label is not None:
                    focus_data.append(record.focus_label)
                if record.stress_label is not None:
                    stress_data.append(record.stress_label)
                if record.wellness_label is not None:
                    wellness_data.append(record.wellness_label)
                timestamps.append(record.timestamp.isoformat())
            return focus_data, stress_data, wellness_data, timestamps

        # For longer sessions, aggregate into exactly 10 buckets
        focus_data, stress_data, wellness_data, timestamps = [], [], [], []
        bucket_size = total_records / 10

        for i in range(10):
            start_idx = int(i * bucket_size)
            end_idx = int((i + 1) * bucket_size) if i < 9 else total_records

            bucket_focus_values = []
            bucket_stress_values = []
            bucket_wellness_values = []
            bucket_timestamps = []

            # Collect all values in this bucket
            for idx in range(start_idx, end_idx):
                record = eeg_records_list[idx]
                if record.focus_label is not None:
                    bucket_focus_values.append(record.focus_label)
                if record.stress_label is not None:
                    bucket_stress_values.append(record.stress_label)
                if record.wellness_label is not None:
                    bucket_wellness_values.append(record.wellness_label)
                bucket_timestamps.append(record.timestamp)

            # Calculate averages for this bucket
            avg_focus = (
                sum(bucket_focus_values) / len(bucket_focus_values)
                if bucket_focus_values
                else 0
            )
            avg_stress = (
                sum(bucket_stress_values) / len(bucket_stress_values)
                if bucket_stress_values
                else 0
            )
            avg_wellness = (
                sum(bucket_wellness_values) / len(bucket_wellness_values)
                if bucket_wellness_values
                else 0
            )

            # Use the middle timestamp of the bucket as representative timestamp
            middle_timestamp = (
                bucket_timestamps[len(bucket_timestamps) // 2]
                if bucket_timestamps
                else eeg_records_list[start_idx].timestamp
            )

            focus_data.append(avg_focus)
            stress_data.append(avg_stress)
            wellness_data.append(avg_wellness)
            timestamps.append(middle_timestamp.isoformat())

        return focus_data, stress_data, wellness_data, timestamps

    # Get aggregated EEG data for frontend plotting
    focus_data, stress_data, wellness_data, timestamps = (
        aggregate_eeg_for_frontend_graph(eeg_records)
    )

    # Determine if data was aggregated or returned as-is
    was_aggregated = len(eeg_records) > 10

    return {
        "session_id": session.id,
        "label": session.label,
        "duration": session.duration,
        "avg_focus": session.focus,
        "avg_stress": session.stress,
        "avg_wellness": session.wellness,
        "focus_data": focus_data,
        "stress_data": stress_data,
        "wellness_data": wellness_data,
        "timestamps": timestamps,
        "eeg_records_count": len(eeg_records),
        "aggregated_data_points": len(focus_data),  # number of points returned
        "was_aggregated": was_aggregated,  # true if data was averaged, false if actual timestamps returned
    }


@router.get("/eeg/summary")
def get_user_summary(
    db: DBSession = Depends(get_db), current_user=Depends(get_current_user_payload)
):
    """
    Returns the total number of sessions, total focus time in minutes, and average focus score for the current user.
    """
    user_id = int(current_user.get("sub"))

    # Get total sessions
    total_sessions = db.query(Session).filter(Session.user_id == user_id).count()

    # Get average focus score from sessions table (not EEG records)
    avg_focus_result = (
        db.query(func.avg(Session.focus))
        .filter(
            and_(
                Session.user_id == user_id,
                Session.focus.isnot(None),  # Only include sessions with focus data
            )
        )
        .scalar()
    )

    # Get focused records with timestamps for calculating focus time
    focused_records = (
        db.query(EEGRecord.timestamp)
        .filter(and_(EEGRecord.user_id == user_id, EEGRecord.focus_label > 0))
        .all()
    )

    # Calculate unique minutes where focus was active
    focused_minutes = set()
    for record in focused_records:
        # Extract minute from timestamp (ignoring seconds)
        minute_timestamp = record.timestamp.replace(second=0, microsecond=0)
        focused_minutes.add(minute_timestamp)

    total_focus_minutes = len(focused_minutes)
    avg_focus = round(avg_focus_result or 0, 1)  # Round to 1 decimal place

    return {
        "sessions": total_sessions,
        "Focus Time": f"{total_focus_minutes}m",
        "Avg Score": f"{avg_focus}",  # Remove the % since focus is typically 0-3 scale
    }
