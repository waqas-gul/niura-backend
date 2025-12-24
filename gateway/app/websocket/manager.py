
from fastapi import WebSocket
from typing import Set
import asyncio
import json
import logging

logger = logging.getLogger("websocket")

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info(f"🔌 WebSocket connected: {len(self.active_connections)} active")

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self.active_connections.discard(websocket)
        logger.info(f"❌ WebSocket disconnected: {len(self.active_connections)} active")

    async def broadcast_json(self, message: dict):
        """Send message to all active clients."""
        to_remove = []
        for ws in list(self.active_connections):
            try:
                await ws.send_json(message)
            except Exception:
                to_remove.append(ws)
        for ws in to_remove:
            await self.disconnect(ws)

manager = ConnectionManager()
