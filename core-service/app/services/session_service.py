import logging
from fastapi import HTTPException
from app.models.sessions import Session
from app.schemas.sessions import SessionHistoryOut

logger = logging.getLogger(__name__)

class SessionService:
    def __init__(self, db):
        self.db = db

    def get_session_history(self, user_id: int):
        try:
            sessions = (
                self.db.query(Session)
                .filter(Session.user_id == user_id)
                .order_by(Session.date.desc())
                .limit(10)
                .all()
            )
            return [
                SessionHistoryOut(
                    date=s.date,
                    duration=s.duration,
                    label=s.label
                ) for s in sessions
            ]
        except Exception as e:
            logger.exception("Failed to fetch session history for user %s", user_id)
            raise HTTPException(status_code=500, detail="Failed to fetch session history")