import logging
import time
import uuid
from contextvars import ContextVar
from jose import jwt, JWTError
from starlette.types import ASGIApp, Receive, Scope, Send

# Context vars accessible anywhere
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_ctx: ContextVar[str | None]   = ContextVar("user_id", default=None)

logger = logging.getLogger("eeg.request")

def get_request_id() -> str | None:
    return request_id_ctx.get()

def get_user_id() -> str | None:
    return user_id_ctx.get()

class ContextLoggingMiddleware:
    """
    Core-service: reuse X-Request-ID/X-User-ID if provided by gateway.
    If missing, generate a new request_id.
    """
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        # Reuse propagated IDs if present
        req_id = headers.get(b"x-request-id", b"").decode() or str(uuid.uuid4())
        usr_id = headers.get(b"x-user-id", b"").decode() or None

        request_id_ctx.set(req_id)
        user_id_ctx.set(usr_id)

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                out = list(message.get("headers", []))
                out.append((b"x-request-id", req_id.encode()))
                if usr_id:
                    out.append((b"x-user-id", usr_id.encode()))
                message["headers"] = out
            await send(message)

        await self.app(scope, receive, send_wrapper)


class RequestLoggingMiddleware:
    """
    Access log: method, path, status, latency, request_id, user_id, handler.
    """
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.time()
        status_code = None
        endpoint_name = None

        # Best-effort: capture handler name if mounted by FastAPI
        endpoint_func = scope.get("endpoint")
        if callable(endpoint_func):
            endpoint_name = f"{endpoint_func.__module__}.{endpoint_func.__name__}"

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        await self.app(scope, receive, send_wrapper)

        dur_ms = round((time.time() - start) * 1000, 2)
        
        logger.info(
    "",
    extra={
        "event": "HTTP Request",
        "method": scope["method"],
        "path": scope["path"],
        "status_code": status_code,
        "duration_ms": dur_ms,  # ✅ use the computed variable
        "request_id": request_id_ctx.get(),
        "user_id": user_id_ctx.get(),
    },
)
