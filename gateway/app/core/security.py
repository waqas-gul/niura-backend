from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from jose import jwt, JWTError, ExpiredSignatureError
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES, JWT_AUDIENCE, JWT_ISSUER, JWT_SECRET_KEY, ALGORITHM

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")



def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)



def create_access_token(data: dict, expires_delta: timedelta | None=None):
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # Use timezone-aware UTC datetime
    now = datetime.now(timezone.utc)
    claims = {
        
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": now,
        "nbf": now - timedelta(seconds=30),  # Allow 30 seconds clock skew
        "exp": now + expires_delta,
        **data
    }
    return jwt.encode(claims, JWT_SECRET_KEY, algorithm=ALGORITHM)

# def create_access_token(data: dict, expires_delta: timedelta = None):
#     if expires_delta is None:
#         expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     expire = datetime.utcnow() + expires_delta
#     to_encode = data.copy()
#     to_encode.update({"exp": expire})
#     encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)
#     return encoded_jwt

def verify_access_token(token: str):
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Disable nbf validation to handle clock skew issues
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM], audience=JWT_AUDIENCE,
                             options={"verify_aud": True, "verify_nbf": False})
        
        if not payload.get("sub"):
            logger.warning("❌ Token missing 'sub' claim")
            return None
        return payload
    except ExpiredSignatureError as e:
        logger.warning(f"⏰ Token expired: {str(e)}")
        return "EXPIRED"
    except JWTError as e:
        logger.error(f"❌ JWT validation failed: {type(e).__name__} - {str(e)}")
        return None
    
def get_current_user_payload(token: str = Depends(oauth2_scheme)):
    result=verify_access_token(token)
    if result == "EXPIRED":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    if result is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return result


def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Dependency to get current user from JWT token.
    Returns user_id (string) that can be used to query the database.
    """
    try:
        user_id = verify_access_token(token)
        if user_id == "EXPIRED":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer", "X-Error-Type": "TOKEN_EXPIRED"},
            )
        elif user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer", "X-Error-Type": "TOKEN_INVALID"},
            )
        return user_id
    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer", "X-Error-Type": "AUTH_FAILED"},
        )

def create_reset_token(email: str):
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    payload = {"sub": email, "exp": expire}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)

def verify_reset_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
