from asyncio import Task
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from app.database import SessionLocal
from app.schemas.EarbudUUIDBase import (
    EarbudUUIDCreate,
    EarbudUUIDResponse,
    EarbudUUIDUpdate,
)
from app.models import EarbudUUID
from sqlalchemy.orm import Session
from datetime import datetime  # ADD THIS LINE
from app.schemas import user as user_schema
from app.services.user_service import UserService
from sqlalchemy.exc import IntegrityError
from app.schemas.user import (
    EmailRequest,
    ResetPasswordRequest,
    ResponseModel,
    VerifyCodeRequest,
)
from app.services.user_service import UserService
from app.core.security import (
    create_access_token,
    create_reset_token,
    get_current_user,
    get_current_user_payload,
    get_password_hash,
    verify_reset_token,
)
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel
from app.models.user import User
import string
import random
import time
import base64
import logging


from app.utils.email_utils import send_reset_email, send_forgot_password_code


class ThresholdUpdateRequest(BaseModel):
    focus_threshold: float
    stress_threshold: float


# Password hashing and validation
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter()

logger = logging.getLogger("gateway.user_controller")


def generate_verification_code():
    """Generate a timestamp-based verification code that expires automatically"""
    # Get current timestamp
    current_time = int(time.time())

    # Generate 6-digit random code
    random_code = "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(6)
    )

    # Combine timestamp and random code, then encode
    combined = f"{current_time}:{random_code}"
    encoded = base64.b64encode(combined.encode()).decode()

    return encoded


def verify_code_and_expiration(
    stored_code: str, provided_code: str, expiry_minutes: int = 5
):
    """Verify code and check if it has expired"""
    try:
        if stored_code != provided_code:
            return False, "Invalid verification code"

        # Decode the stored code
        decoded = base64.b64decode(stored_code.encode()).decode()
        timestamp_str, random_code = decoded.split(":")

        # Check expiration
        code_timestamp = int(timestamp_str)
        current_timestamp = int(time.time())

        # Check if expired (5 minutes = 300 seconds)
        if current_timestamp - code_timestamp > (expiry_minutes * 60):
            return False, "Verification code has expired"

        return True, "Code is valid"

    except Exception as e:
        return False, "Invalid verification code format"


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    logger.info("Login request received", extra={"email": form_data.username})

    # Step 1: Check if email exists in the database
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user:
        logger.warning(
            "Login failed - user not found", extra={"email": form_data.username}
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Step 2: Check if user is deleted (is_deleted == True)
    if hasattr(user, "is_deleted") and user.is_deleted:
        logger.warning(
            "Login failed - account is deleted", extra={"email": form_data.username}
        )
        raise HTTPException(
            status_code=401,
            detail="Your account has been deleted. Please contact support to restore your account.",
        )

    # Step 3: Also check deleted_at timestamp as backup
    if user.deleted_at is not None:
        logger.warning(
            "Login failed - account is deleted (by timestamp)",
            extra={"email": form_data.username},
        )
        raise HTTPException(
            status_code=401,
            detail="Your account has been deleted. Please contact support to restore your account.",
        )

    # Step 4: Verify password
    if not pwd_context.verify(form_data.password, user.password_hash):
        logger.warning(
            "Login failed - invalid password", extra={"email": form_data.username}
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Step 5: Login successful - create token
    roles = [user.role] if getattr(user, "role", None) else ["user"]
    token = create_access_token(
        data={"sub": str(user.id), "roles": roles, "email": user.email}
    )
    logger.info("Login successful", extra={"email": user.email, "roles": roles})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
def logout(current_user: str = Depends(get_current_user)):
    """
    Logout endpoint - In a stateless JWT system, logout is typically handled
    client-side by deleting the token. This endpoint exists for compatibility.
    """
    return {"message": "Logged out successfully"}


@router.post("/register")
def register(user: user_schema.UserCreate, db: Session = Depends(get_db)):
    service = UserService(db)
    logger.info("New User registeration attempt", extra={"email": user.email})
    try:
        new_user = service.create_user(user)
        logger.info(
            "User refistered successfully",
            extra={"email": user.email, "id": new_user.id},
        )
        return {
            "code": "00",
            "message": "User registered successfully",
            "data": user_schema.UserOut.from_orm(new_user),
        }
    except HTTPException as e:
        logger.warning(
            "User regsiteration failed (HTTPException)",
            extra={"email": user.email, "error": e.detail},
        )
        raise e
    except IntegrityError as e:
        db.rollback()
        logger.error(
            "Integrity error during registration",
            extra={"email": user.email, "error": str(e)},
        )
        return {
            "code": "01",
            "message": "Database constraint violation - user may already exist",
        }
    except Exception as e:
        db.rollback()
        logger.exception(
            "Unexpected error during registeration", extra={"email": user.email}
        )
        return {"code": "01", "message": f"Unexpected error: {str(e)}"}


# Protect update endpoint (only the user or admin can update)
@router.put("/users/thresholds")
def update_thresholds(
    thresholds: ThresholdUpdateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_payload),
):
    # Gateway JWT has nested structure issue
    # Extract user_id safely

    # Method 1: If current_user is the full JWT payload
    if isinstance(current_user, dict) and "sub" in current_user:
        jwt_payload = current_user
    else:
        # If get_current_user_payload already extracts
        jwt_payload = current_user

    # Extract user_id - handle nested dict
    user_id = jwt_payload.get("sub")

    # Debug
    print(f"🔍 Raw user_id: {user_id}, Type: {type(user_id)}")

    # Unwrap if nested
    if isinstance(user_id, dict):
        user_id = user_id.get("sub")
        print(f"🔍 Unwrapped user_id: {user_id}")

    # Convert to int
    try:
        user_id_int = int(user_id) if user_id else None
    except (ValueError, TypeError) as e:
        print(f"❌ Error converting user_id: {e}")
        raise HTTPException(status_code=401, detail="Invalid user ID format")

    # SIMPLEST: Query by ID only (remove email condition)
    user = db.query(User).filter(User.id == user_id_int).first()

    if not user:
        # Fallback: try with email if ID fails
        email = jwt_payload.get("email")
        if isinstance(email, dict):
            email = email.get("email")

        if email:
            user = db.query(User).filter(User.email == email).first()

    if not user:

        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    if not (0 <= thresholds.focus_threshold <= 3) or not (
        0 <= thresholds.stress_threshold <= 3
    ):
        raise HTTPException(
            status_code=400, detail="Thresholds must be between 0 and 3"
        )

    user.focus_threshold = thresholds.focus_threshold
    user.stress_threshold = thresholds.stress_threshold

    db.commit()
    db.refresh(user)

    return {
        "message": "Thresholds updated successfully",
        "focus_threshold": user.focus_threshold,
        "stress_threshold": user.stress_threshold,
    }


@router.get("/users/thresholds")
def get_thresholds(
    db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    logger.info("Get thresholds request", extra={"user_id": current_user})
    user = (
        db.query(User)
        .filter((User.id == current_user) | (User.email == current_user))
        .first()
    )
    if not user:
        logger.warning(
            "Get thresholds failed - invalid token", extra={"user_id": current_user}
        )
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return {
        "focus_threshold": user.focus_threshold or 2,
        "stress_threshold": user.stress_threshold or 2,
    }


# Protect update endpoint (only the user or admin can update)
@router.put("/users/{user_id}", response_model=ResponseModel)
def update_user(
    user_id: int,
    user_data: user_schema.UserUpdate,
    current_user: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    logger.info(
        "User update request", extra={"user_id": user_id, "requester": current_user}
    )
    user_service = UserService(db)

    try:
        # Extract user info from JWT payload
        requester_id = int(current_user.get("sub", 0))
        requester_roles = current_user.get("roles", [])

        updated_user = user_service.update_user(
            user_id=user_id,
            user_data=user_data,
            db=db,
            current_user_id=requester_id,
            current_user_roles=requester_roles,
        )

        if updated_user:
            logger.info("User updated successfully", extra={"user_id": user_id})
            return ResponseModel(
                code="00",
                message="User updated successfully",
                data=user_schema.UserOut.from_orm(updated_user).dict(),
            )
        else:
            logger.warning(
                "User update failed - user not found", extra={"user_id": user_id}
            )
            raise HTTPException(status_code=404, detail="User not found")

    except HTTPException as e:
        raise e
    except IntegrityError as e:
        db.rollback()
        logger.error(
            "Integrity error during user update",
            extra={"user_id": user_id, "error": str(e)},
        )
        return ResponseModel(
            code="01", message="User with provided email or phone already exists"
        )
    except Exception as e:
        db.rollback()
        logger.exception(
            "Unexpected error during user update", extra={"user_id": user_id}
        )
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    
# Protect delete endpoint (only the user or admin can delete)
@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    current_user: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    # Log without the current_user dict in extra
    logger.info(f"User deletion request for user_id: {user_id}")

    try:
        # Direct simple extraction
        requester_id = (
            int(current_user.get("sub", 0)) if isinstance(current_user, dict) else 0
        )
        requester_roles = (
            current_user.get("roles", []) if isinstance(current_user, dict) else []
        )

        user_service = UserService(db)
        deleted_user = user_service.delete_user(
            user_id=user_id,
            current_user_id=requester_id,
            current_user_roles=requester_roles,
        )

        logger.info(f"User {user_id} deleted by user {requester_id}")
        return {"message": "User deleted successfully", "deleted_user_id": user_id}

    except ValueError as e:
        # Handle case where current_user.get("sub") might not be convertible to int
        logger.error(f"ValueError in delete_user: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        logger.error(f"Error in delete_user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# Optional: Add a restore endpoint
@router.patch("/users/{user_id}/restore", response_model=ResponseModel)
def restore_user(
    user_id: int,
    current_user: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    """
    Restore a soft-deleted user (admin only)
    """
    logger.info(
        "User restore request", extra={"user_id": user_id, "requester": current_user}
    )

    requester_roles = current_user.get("roles", [])

    # Only admins can restore users
    if "admin" not in requester_roles:
        logger.warning(
            "User restore failed - unauthorized",
            extra={"user_id": user_id, "requester": current_user},
        )
        raise HTTPException(
            status_code=403, detail="Only administrators can restore users"
        )

    user_service = UserService(db)

    try:
        restored_user = user_service.restore_user(user_id=user_id)

        logger.info("User restored successfully", extra={"user_id": user_id})
        return ResponseModel(
            code="00",
            message="User account restored successfully",
            data={
                "restored_user_id": user_id,
                "email": restored_user.email,
                "is_active": restored_user.is_active,
                "restored_at": datetime.utcnow().isoformat(),
            },
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        logger.exception(
            "Unexpected error during user restoration",
            extra={"user_id": user_id, "error": str(e)},
        )
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# ==============================================
# PASSWORD RESET ENDPOINTS (NEW CODE-BASED SYSTEM)
# ==============================================


# Step 1: Request verification code
@router.post("/forgot-password")
def forgot_password(request: EmailRequest, db: Session = Depends(get_db)):
    logger.info("Password reset request", extra={"email": request.email})
    user_service = UserService(db)
    user = user_service.get_user_by_email(request.email)

    if not user:
        logger.warning(
            "Password reset failed - user not found", extra={"email": request.email}
        )
        raise HTTPException(status_code=404, detail="User not found")

    verification_code = generate_verification_code()
    user.forgot_password_code = verification_code
    db.commit()

    try:
        decoded = base64.b64decode(verification_code.encode()).decode()
        _, display_code = decoded.split(":")
    except:
        display_code = verification_code[:6]

    if send_forgot_password_code(user.email, display_code):
        logger.info("Password reset code sent", extra={"email": request.email})
        return {"message": "Verification code sent to your email"}
    else:
        logger.error(
            "Failed to send password reset email", extra={"email": request.email}
        )
        raise HTTPException(status_code=500, detail="Failed to send email")


# Step 2: Verify code and reset password
@router.post("/verify-reset-code")
def verify_reset_code(request: VerifyCodeRequest, db: Session = Depends(get_db)):
    logger.info("Password reset verification attempt", extra={"email": request.email})
    user_service = UserService(db)
    user = user_service.get_user_by_email(request.email)

    if not user:
        logger.warning(
            "Password reset verification failed - user not found",
            extra={"email": request.email},
        )
        raise HTTPException(status_code=404, detail="User not found")

    if not user.forgot_password_code:
        logger.warning(
            "Password reset verification failed - no code found",
            extra={"email": request.email},
        )
        raise HTTPException(status_code=400, detail="No verification code found")

    try:
        decoded = base64.b64decode(user.forgot_password_code.encode()).decode()
        timestamp_str, stored_random_code = decoded.split(":")

        if stored_random_code != request.code:
            logger.warning(
                "Password reset verification failed - invalid code",
                extra={"email": request.email},
            )
            raise HTTPException(status_code=400, detail="Invalid verification code")

        is_valid, message = verify_code_and_expiration(
            user.forgot_password_code, user.forgot_password_code, 5
        )

        if not is_valid:
            user.forgot_password_code = None
            db.commit()
            logger.warning(
                "Password reset verification failed - expired code",
                extra={"email": request.email},
            )
            raise HTTPException(status_code=400, detail=message)

    except ValueError as e:
        logger.error(
            "Password reset verification failed - invalid format",
            extra={"email": request.email, "error": str(e)},
        )
        raise HTTPException(status_code=400, detail="Invalid verification code format")

    hashed_pwd = get_password_hash(request.new_password)
    user.password_hash = hashed_pwd
    user.forgot_password_code = None
    db.commit()

    logger.info("Password reset successful", extra={"email": request.email})
    return {"message": "Password has been reset successfully"}


@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    logger.info("Legacy password reset attempt")
    try:
        email = verify_reset_token(request.token)
        if not email:
            logger.warning("Legacy password reset failed - invalid token")
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired reset token. Please use /forgot-password to get a new verification code.",
            )

        user_service = UserService(db)
        user = user_service.get_user_by_email(email)
        if not user:
            logger.warning(
                "Legacy password reset failed - user not found", extra={"email": email}
            )
            raise HTTPException(status_code=404, detail="User not found")

        hashed_pwd = get_password_hash(request.new_password)
        user.password_hash = hashed_pwd
        db.commit()

        logger.info("Legacy password reset successful", extra={"email": email})
        return {
            "message": "Password has been reset successfully",
            "note": "This endpoint is deprecated. Please use /verify-reset-code for future password resets.",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Legacy password reset failed", extra={"error": str(e)})
        raise HTTPException(
            status_code=400,
            detail="Invalid token format. Please use /forgot-password to get a verification code instead.",
        )


# Add this to your user_controller.py


@router.get("/profile")
def get_user_profile(
    current_user: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    user_id = int(current_user.get("sub"))
    logger.info("Profile fetch request", extra={"user_id": user_id})

    try:
        user_service = UserService(db)
        user = user_service.get_user_by_id(user_id)

        if not user:
            logger.warning(
                "Profile fetch failed - user not found", extra={"user_id": user_id}
            )
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "gender": user.gender,
            "created_at": user.created_at,
        }
    except Exception as e:
        logger.exception("Profile fetch failed", extra={"user_id": user_id})
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/profile")
def update_user_profile(
    profile_data: dict,
    current_user: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    user_id = int(current_user.get("sub"))
    logger.info(
        "Profile update request",
        extra={"user_id": user_id, "fields": list(profile_data.keys())},
    )

    try:
        user_service = UserService(db)
        user = user_service.get_user_by_id(user_id)

        if not user:
            logger.warning(
                "Profile update failed - user not found", extra={"user_id": user_id}
            )
            raise HTTPException(status_code=404, detail="User not found")

        allowed_fields = ["full_name", "gender"]
        for field, value in profile_data.items():
            if field in allowed_fields:
                setattr(user, field, value)

        db.commit()
        logger.info("Profile updated successfully", extra={"user_id": user_id})

        return {
            "message": "Profile updated successfully",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "gender": user.gender,
            },
        }
    except Exception as e:
        db.rollback()
        logger.exception("Profile update failed", extra={"user_id": user_id})
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================
# EARBUD MANAGEMENT ENDPOINTS
# ==============================================


# 1. Bulk Upload - Accept multiple users' earbud data
@router.post("/earbuds/bulk-upload", response_model=List[EarbudUUIDResponse])
def bulk_upload_earbuds(
    earbuds_data: List[EarbudUUIDCreate],
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_payload),
):
    user_id = int(current_user.get("sub"))
    roles = current_user.get("roles", [])
    logger.info(
        "Bulk earbud upload request",
        extra={"admin_id": user_id, "count": len(earbuds_data)},
    )

    try:
        if "admin" not in roles and "user" not in roles:
            logger.warning(
                "Bulk upload failed - unauthorized", extra={"user_id": user_id}
            )
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        if not earbuds_data:
            logger.warning("Bulk upload failed - no data", extra={"admin_id": user_id})
            raise HTTPException(status_code=400, detail="No earbud data provided")

        results = []
        for i, earbud_item in enumerate(earbuds_data):
            try:
                existing_record = (
                    db.query(EarbudUUID)
                    .filter(EarbudUUID.user_id == earbud_item.user_id)
                    .first()
                )

                if existing_record:
                    for field, value in earbud_item.dict().items():
                        if hasattr(existing_record, field) and value is not None:
                            setattr(existing_record, field, value)
                    results.append(existing_record)
                else:
                    new_record = EarbudUUID(**earbud_item.dict())
                    db.add(new_record)
                    results.append(new_record)

            except Exception as item_error:
                logger.error(
                    "Failed to process earbud item",
                    extra={
                        "index": i,
                        "user_id": earbud_item.user_id,
                        "error": str(item_error),
                    },
                )
                continue

        db.commit()
        for obj in results:
            db.refresh(obj)

        logger.info(
            "Bulk upload successful",
            extra={"admin_id": user_id, "processed": len(results)},
        )
        return results

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Bulk upload failed", extra={"admin_id": user_id})
        raise HTTPException(status_code=500, detail=f"Bulk upload failed: {str(e)}")


# 2. Get specific user's earbud data
@router.get("/earbuds/user/{user_id}", response_model=List[EarbudUUIDResponse])
def get_user_earbuds(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_payload),
):
    requester_id = int(current_user.get("sub"))
    roles = current_user.get("roles", [])
    logger.info(
        "Get user earbuds request",
        extra={"requester_id": requester_id, "target_user_id": user_id},
    )

    if requester_id != user_id and "admin" not in roles:
        logger.warning(
            "Get earbuds failed - forbidden",
            extra={"requester_id": requester_id, "target_user_id": user_id},
        )
        raise HTTPException(status_code=403, detail="Forbidden")

    records = db.query(EarbudUUID).filter(EarbudUUID.user_id == user_id).all()
    if not records:
        logger.warning("Get earbuds - no records found", extra={"user_id": user_id})
        raise HTTPException(
            status_code=404, detail="No earbud records found for this user"
        )

    return records


# 3. Get all users' earbud data (Admin only)
@router.get("/earbuds/all", response_model=List[EarbudUUIDResponse])
def get_all_earbuds(
    db: Session = Depends(get_db), current_user: str = Depends(get_current_user_payload)
):
    requester_id = int(current_user.get("sub"))
    roles = current_user.get("roles", [])
    logger.info("Get all earbuds request", extra={"admin_id": requester_id})

    if "admin" not in roles:
        logger.warning(
            "Get all earbuds failed - unauthorized", extra={"user_id": requester_id}
        )
        raise HTTPException(status_code=403, detail="Admin access required")

    records = db.query(EarbudUUID).all()
    logger.info(
        "Retrieved all earbuds", extra={"admin_id": requester_id, "count": len(records)}
    )
    return records

    records = db.query(EarbudUUID).all()
    return records


# 4. Bulk update multiple users' earbud data
@router.put("/earbuds/bulk-update")
def bulk_update_earbuds(
    updates_data: List[EarbudUUIDUpdate],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_payload),
):
    requester_id = int(current_user.get("sub"))
    roles = current_user.get("roles", [])

    if "admin" not in roles:
        raise HTTPException(status_code=403, detail="Admin access required")

    if not updates_data:
        raise HTTPException(status_code=400, detail="No update data provided")

    results = []
    users_not_found = []

    for update_item in updates_data:
        try:
            update_dict = update_item.dict(exclude_unset=True)
            user_id = update_dict.get("user_id")

            if not user_id:
                users_not_found.append({"user_id": None})
                continue

            # Check if user exists
            user_exists = db.query(User).filter(User.id == user_id).first()
            if not user_exists:
                users_not_found.append({"user_id": user_id})
                continue

            # Find bud by USER_ID
            existing_bud = (
                db.query(EarbudUUID).filter(EarbudUUID.user_id == user_id).first()
            )

            if existing_bud:
                update_dict_no_user = {
                    k: v for k, v in update_dict.items() if k != "user_id"
                }
                for field, value in update_dict_no_user.items():
                    if hasattr(existing_bud, field):
                        setattr(existing_bud, field, value)
                results.append(existing_bud)
            else:
                new_bud = EarbudUUID(**update_dict)
                db.add(new_bud)
                results.append(new_bud)

        except Exception:
            users_not_found.append(
                {"user_id": user_id if "user_id" in locals() else None}
            )
            continue

    # Commit all changes
    try:
        db.commit()
        for obj in results:
            db.refresh(obj)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database update failed")

    # Prepare response
    response_data = {"data": results}

    # Add users_not_found if any
    if users_not_found:
        response_data["users_not_found"] = users_not_found

    return response_data


# 5. Delete specific user's earbud data
@router.delete("/earbuds/user/{user_id}")
def delete_user_earbuds(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_payload),
):
    requester_id = int(current_user.get("sub"))
    roles = current_user.get("roles", [])
    logger.info(
        "Delete user earbuds request",
        extra={"requester_id": requester_id, "target_user_id": user_id},
    )

    if requester_id != user_id and "admin" not in roles:
        logger.warning(
            "Delete earbuds failed - forbidden",
            extra={"requester_id": requester_id, "target_user_id": user_id},
        )
        raise HTTPException(status_code=403, detail="Forbidden")

    records = db.query(EarbudUUID).filter(EarbudUUID.user_id == user_id).all()
    if not records:
        logger.warning(
            "Delete earbuds failed - no records found", extra={"user_id": user_id}
        )
        raise HTTPException(status_code=404, detail="No earbud records found")

    deleted_count = len(records)
    for record in records:
        db.delete(record)

    db.commit()
    logger.info(
        "Earbuds deleted successfully",
        extra={"user_id": user_id, "count": deleted_count},
    )

    return {
        "message": f"Successfully deleted {deleted_count} earbud records for user {user_id}",
        "deleted_count": deleted_count,
        "user_id": user_id,
    }


# Additional endpoint to match frontend expectations
@router.get("/earbud/uuids/{user_id}", response_model=List[EarbudUUIDResponse])
def get_user_earbud_uuids(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_payload),
):
    requester_id = int(current_user.get("sub"))
    roles = current_user.get("roles", [])
    logger.info(
        "Get earbud UUIDs request",
        extra={"requester_id": requester_id, "target_user_id": user_id},
    )

    records = db.query(EarbudUUID).filter(EarbudUUID.user_id == user_id).all()
    if not records:
        logger.warning(
            "Get earbud UUIDs - no records found", extra={"user_id": user_id}
        )
        raise HTTPException(status_code=404, detail="No earbud records found")

    return records
