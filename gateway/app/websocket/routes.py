from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import jwt, JWTError
from app.websocket.manager import manager
from app.websocket.metrics_manager import metrics_manager
from app.events.kafka_producer import send_eeg_event
from app.core.config import JWT_AUDIENCE, JWT_ISSUER, JWT_SECRET_KEY, ALGORITHM
import json
import logging

logger = logging.getLogger("websocket")

router = APIRouter(prefix="/ws", tags=["WebSocket"])


@router.websocket("/eeg")
async def eeg_endpoint(websocket: WebSocket):
    """Handles EEG bulk data streaming via WebSocket with user authentication."""

    # 1️⃣ Extract token from query params
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="Missing authentication token")
        logger.warning("WebSocket connection rejected: No token provided")
        return

    # 2️⃣ Decode the JWT (same as get_current_user)
    try:
        # Use same validation options as REST API to handle clock skew and be more lenient
        payload = jwt.decode(
            token, JWT_SECRET_KEY, algorithms=[ALGORITHM], 
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
            options={"verify_aud": True, "verify_nbf": False}  # Disable nbf check for clock skew
        )
        
        user_id = payload.get("sub")
        if user_id is None:
            logger.error("❌ EEG WebSocket: Token missing 'sub' claim")
            await websocket.close(code=1008, reason="Invalid token: missing user_id")
            logger.warning("WebSocket token missing user_id (sub)")
            return
    except JWTError as e:
        logger.error(f"❌ EEG WebSocket JWT validation failed: {type(e).__name__} - {str(e)}")
        await websocket.close(code=1008, reason="Invalid or expired token")
        logger.warning(f"WebSocket token validation failed: {e}")
        return

    # ✅ If authenticated successfully:
    logger.info(f"WebSocket connection established for user_id={user_id}")
    await manager.connect(websocket)

    try:
        while True:
            raw_message = await websocket.receive_text()

            try:
                data = json.loads(raw_message)
                send_eeg_event(user_id=user_id, eeg_payload=data)
                logger.debug(f"Received {len(data.get('records', []))} samples for user {user_id}")

                await manager.broadcast_json({
                    "type": "EEG_FRAME",
                    "user_id": user_id,
                    "count": len(data.get("records", [])),
                    "data": data
                })

            except json.JSONDecodeError:
                logger.warning("Invalid JSON received, skipping...")
            except Exception as e:
                logger.error(f"Kafka send failed: {e}")

    except WebSocketDisconnect:
        await manager.disconnect(websocket)
        logger.info(f"User {user_id} disconnected")


@router.websocket("/metrics")
async def metrics_endpoint(websocket: WebSocket):
    """Handles real-time processed metrics streaming via WebSocket."""

    # 1️⃣ Extract token from query params
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="Missing authentication token")
        logger.warning("Metrics WebSocket connection rejected: No token provided")
        return

    # 2️⃣ Decode the JWT
    try:
        # Use same validation options as REST API to handle clock skew and be more lenient
        payload = jwt.decode(
            token, JWT_SECRET_KEY, algorithms=[ALGORITHM], 
            audience=JWT_AUDIENCE, issuer=JWT_ISSUER,
            options={"verify_aud": True, "verify_nbf": False}  # Disable nbf check for clock skew
        )
        
        user_id = payload.get("sub")
        if user_id is None:
            logger.error("❌ Metrics WebSocket: Token missing 'sub' claim")
            await websocket.close(code=1008, reason="Invalid token: missing user_id")
            logger.warning("Metrics WebSocket token missing user_id (sub)")
            return
        user_id = str(user_id)  # Convert to string for consistency
    except JWTError as e:
        logger.error(f"❌ Metrics WebSocket JWT validation failed: {type(e).__name__} - {str(e)}")
        await websocket.close(code=1008, reason="Invalid or expired token")
        logger.warning(f"Metrics WebSocket token validation failed: {e}")
        return

    # ✅ If authenticated successfully:
    logger.info(f"📊 Metrics WebSocket connected for user_id={user_id}")
    await metrics_manager.connect(user_id, websocket)

    try:
        # Keep connection alive - metrics are pushed from Kafka consumer
        while True:
            # Wait for client disconnect or keep-alive pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        await metrics_manager.disconnect(user_id, websocket)
        logger.info(f"📊 User {user_id} metrics WebSocket disconnected")

