# app/routes/proxy.py
from fastapi import APIRouter, Depends, Request, HTTPException
from starlette.responses import StreamingResponse, Response
from starlette.requests import ClientDisconnect
import httpx
import logging

from app.core.config import CORE_SERVICE_URL, EEG_SERVICE_URL
from app.core.security import get_current_user_payload, oauth2_scheme
from app.core.request_logger import get_request_id


logger = logging.getLogger("gateway.proxy")

router = APIRouter()

def require_roles(*allowed):
    def checker(payload = Depends(get_current_user_payload)):
        roles = payload.get("roles") or []
        if allowed and not any(r in roles for r in allowed):
            raise HTTPException(status_code=403, detail="Forbidden")
        return payload
    return checker


async def _forward_request(upstream_url: str, request: Request, token: str, payload: dict):
    method = request.method
    headers = dict(request.headers)
    headers.pop("host", None)
    headers["authorization"] = f"Bearer {token}"
    headers["x-user-id"] = payload.get("sub", "")
    headers["x-request-id"] = get_request_id() or ""

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            # Stream the request body instead of buffering it all at once
            # This prevents ClientDisconnect errors when clients close connections
            resp = await client.request(
                method,
                upstream_url,
                content=request.stream(),  # Stream instead of await request.body()
                headers=headers,
                params=request.query_params
            )
            return StreamingResponse(
                resp.aiter_bytes(),
                status_code=resp.status_code,
                headers={
                    k: v
                    for k, v in resp.headers.items()
                    if k.lower() not in {"content-encoding", "transfer-encoding", "connection"}
                },
            )
    except ClientDisconnect:
        logger.warning(f"Client disconnected during proxy to {upstream_url}")
        raise HTTPException(status_code=499, detail="Client closed connection")
    except httpx.TimeoutException:
        logger.error(f"Timeout proxying to {upstream_url}")
        raise HTTPException(status_code=504, detail="Gateway timeout")
    except Exception as e:
        logger.error(f"Unexpected error proxying to {upstream_url}: {e}")
        raise HTTPException(status_code=502, detail="Bad gateway")


# ✅ SIMPLE: Keep your original approach - /core/* and /eeg/* routing
@router.api_route("/core/{path:path}", methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"])
async def proxy_core(
    path: str,
    request: Request,
    payload: dict = Depends(get_current_user_payload),
    token: str = Depends(oauth2_scheme),
):
    """Route /core/* requests to core-service"""
    upstream_url = f"{CORE_SERVICE_URL.rstrip('/')}/api/{path}"
    return await _forward_request(upstream_url, request, token, payload)


@router.api_route("/eeg/{path:path}", methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"])
async def proxy_eeg(
    path: str,
    request: Request,
    payload: dict = Depends(get_current_user_payload),
    token: str = Depends(oauth2_scheme),
):
    """Route /eeg/* requests to eeg-service"""
    upstream_url = f"{EEG_SERVICE_URL.rstrip('/')}/api/{path}"
    return await _forward_request(upstream_url, request, token, payload)
