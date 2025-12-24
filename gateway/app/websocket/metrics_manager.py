from fastapi import WebSocket
from typing import Dict, Set
import asyncio
import logging

logger = logging.getLogger("metrics_websocket")

class MetricsConnectionManager:
    """Manages WebSocket connections for real-time processed metrics."""
    
    def __init__(self):
        # user_id -> set of websockets
        self.connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: str, websocket: WebSocket):
        """Connect a WebSocket for a specific user."""
        await websocket.accept()
        async with self._lock:
            if user_id not in self.connections:
                self.connections[user_id] = set()
            self.connections[user_id].add(websocket)
        logger.info(f"🔌 Metrics WebSocket connected for user {user_id}: {len(self.connections[user_id])} connections")

    async def disconnect(self, user_id: str, websocket: WebSocket):
        """Disconnect a WebSocket for a specific user."""
        async with self._lock:
            if user_id in self.connections:
                self.connections[user_id].discard(websocket)
                if not self.connections[user_id]:
                    del self.connections[user_id]
        logger.info(f"❌ Metrics WebSocket disconnected for user {user_id}")

    async def send_to_user(self, user_id: str, message: dict):
        """Send metrics data to all connections for a specific user."""
        if user_id not in self.connections:
            return
        
        to_remove = []
        for ws in list(self.connections[user_id]):
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send to user {user_id}: {e}")
                to_remove.append(ws)
        
        # Clean up failed connections
        for ws in to_remove:
            await self.disconnect(user_id, ws)

metrics_manager = MetricsConnectionManager()
