from fastapi import Request, HTTPException, status, Depends

# ✅ SIMPLIFIED: Trust X-User-ID header from Gateway
# Gateway has already verified JWT, so we don't need to do it again
# This reduces coupling and improves performance

def get_current_user_payload(request: Request) -> dict:
    """
    ✅ SIMPLE & SECURE: Extract user info from gateway headers.
    Gateway verified JWT and added X-User-ID header.
    We trust this because core-service is PRIVATE (only gateway can reach it).
    """
    user_id = request.headers.get("x-user-id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User-ID header (are you calling through gateway?)",
        )
    
    # Return same format as before for compatibility
    return {
        "sub": user_id,  # user_id
        "roles": []  # Can be extracted from x-user-roles header if needed
    }
