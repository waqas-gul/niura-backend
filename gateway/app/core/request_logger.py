import logging
import time
import uuid
from contextvars import ContextVar
from fastapi import Request
from jose import jwt, JWTError
from starlette.types import ASGIApp, Receive, Scope, Send
from app.core.config import JWT_SECRET_KEY, ALGORITHM

logger = logging.getLogger("gateway.request")

# Context variables
request_id_ctx = ContextVar("request_id", default=None)
user_id_ctx = ContextVar("user_id", default=None)


class ContextLoggingMiddleware:
    """Assigns a unique request ID and extracts user_id from JWT."""
    
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Assign new request ID
        request_id = str(uuid.uuid4())
        request_id_ctx.set(request_id)

        # Try extracting user ID from Bearer token (if exists)
        user_id = None
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode("utf-8")
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split("Bearer ")[1]
            try:
                payload = jwt.decode(
                    token, 
                    JWT_SECRET_KEY, 
                    algorithms=[ALGORITHM],
                    options={"verify_aud": False}  # Don't verify audience in middleware
                )
                # Try 'sub' field for user_id
                user_id = payload.get("sub")
                
                # Debug: log what we found (remove after testing)
                logger.debug(f"JWT payload keys: {list(payload.keys())}")
                logger.debug(f"Extracted user_id: {user_id}")
            except JWTError as e:
                logger.debug(f"JWT decode error: {str(e)}")
                user_id = None
        else:
            logger.debug(f"No auth header found or invalid format. Headers: {list(headers.keys())}")
        
        user_id_ctx.set(user_id)

        # Wrapper to add headers to response
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                if user_id:
                    headers.append((b"x-user-id", str(user_id).encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)


class RequestLoggingMiddleware:
    """Logs every request with timing, request_id, and user_id."""
    
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()
        
        # Capture status code from response
        status_code = None
        
        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        await self.app(scope, receive, send_wrapper)
        
        # Log after request completes
        process_time = (time.time() - start_time) * 1000
        
        logger.info("", extra={
            "event": "HTTP Request",
            "method": scope["method"],
            "path": scope["path"],
            "status_code": status_code,
            "duration_ms": round(process_time, 2),
            "request_id": request_id_ctx.get(),
            "user_id": user_id_ctx.get(),
        })



def get_request_id() -> str:
    """Helper: fetch current request ID."""
    return request_id_ctx.get()


def get_user_id() -> str:
    """Helper: fetch current authenticated user ID."""
    return user_id_ctx.get()