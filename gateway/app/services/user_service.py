from sqlalchemy.orm import Session
from app import models
from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from fastapi import HTTPException

class UserService:
    def __init__(self, db: Session):
        self.db = db

    def create_user(self, user: UserCreate):
        # Check if user already exists by email
        existing_user = self.get_user_by_email(user.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="User with provided email already exists")
        
        # Check if phone number already exists (if provided and not empty)
        phone = getattr(user, "phone", None)
        if phone and phone.strip():
            existing_phone = self.db.query(User).filter(User.phone == phone).first()
            if existing_phone:
                raise HTTPException(status_code=400, detail="User with provided phone already exists")
        
        # Ensure gender is provided (required field)
        gender = getattr(user, "gender", None)
        if not gender or not gender.strip():
            raise HTTPException(status_code=400, detail="Gender is required")
        
        # Normalize gender to match database constraints (Male, Female, Other)
        gender_lower = gender.lower().strip()
        if gender_lower in ['male', 'm']:
            gender = 'Male'
        elif gender_lower in ['female', 'f']:
            gender = 'Female'
        elif gender_lower in ['other', 'o']:
            gender = 'Other'
        else:
            raise HTTPException(status_code=400, detail="Gender must be Male, Female, or Other")
        
        # Hash the password before saving
        db_user = models.user.User(
            full_name=user.full_name,
            email=user.email,
            password_hash=get_password_hash(user.password),
            gender=gender,
            dob=getattr(user, "dob", None),
            nationality=getattr(user, "nationality", None),
            phone=phone if phone and phone.strip() else None,
            city=getattr(user, "city", None),
            country=getattr(user, "country", None),
            occupation=getattr(user, "occupation", None),
            marital_status=getattr(user, "marital_status", None),
            sleep_hours=getattr(user, "sleep_hours", None),
            exercise_frequency=getattr(user, "exercise_frequency", None),
            smoking_status=getattr(user, "smoking_status", None),
            alcohol_consumption=getattr(user, "alcohol_consumption", None),
            role=getattr(user,"role","user")
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def update_user(
        self, 
        user_id: int, 
        user_data: UserUpdate, 
        db: Session, 
        current_user_id: int, 
        current_user_roles: list = None
    ):
        """
        Update user information - allows updating all user fields
        """
        if current_user_roles is None:
            current_user_roles = []
        
        # Fetch the user to update
        user = self.db.query(models.user.User).filter(models.user.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Authorization check
        if user_id != current_user_id and "admin" not in current_user_roles:
            raise HTTPException(status_code=403, detail="Not authorized to update this user")

        # Convert input to dict and exclude unset fields
        update_data = user_data.dict(exclude_unset=True)
        
        # Handle email update with validation
        if "email" in update_data and update_data["email"] != user.email:
            new_email = update_data["email"]
            # Check if new email already exists for another user
            existing_user = self.db.query(User).filter(
                User.email == new_email,
                User.id != user_id
            ).first()
            if existing_user:
                raise HTTPException(
                    status_code=400, 
                    detail="Email already in use by another user"
                )
        
        # Handle password update
        if "password" in update_data:
            update_data["password_hash"] = get_password_hash(update_data.pop("password"))
        
        # Handle gender normalization if being updated
        if "gender" in update_data and update_data["gender"]:
            gender = update_data["gender"].lower().strip()
            if gender in ['male', 'm']:
                update_data["gender"] = 'Male'
            elif gender in ['female', 'f']:
                update_data["gender"] = 'Female'
            elif gender in ['other', 'o']:
                update_data["gender"] = 'Other'
            else:
                raise HTTPException(status_code=400, detail="Gender must be Male, Female, or Other")
        
        # Handle phone number - check for duplicates if being updated
        if "phone" in update_data:
            phone = update_data["phone"]
            if phone and phone.strip():
                # Check if another user already has this phone number
                existing_phone = self.db.query(User).filter(
                    User.phone == phone,
                    User.id != user_id
                ).first()
                if existing_phone:
                    raise HTTPException(status_code=400, detail="Phone number already in use")
            else:
                # Set to None if empty string
                update_data["phone"] = None
        
        # Handle numeric fields with validation
        # Sleep hours validation (0-24)
        if "sleep_hours" in update_data and update_data["sleep_hours"] is not None:
            sleep_hours = update_data["sleep_hours"]
            if not (0 <= sleep_hours <= 24):
                raise HTTPException(
                    status_code=400, 
                    detail="Sleep hours must be between 0 and 24"
                )
        
        # Focus threshold validation (0-3)
        if "focus_threshold" in update_data and update_data["focus_threshold"] is not None:
            focus_threshold = update_data["focus_threshold"]
            if not (0 <= focus_threshold <= 3):
                raise HTTPException(
                    status_code=400, 
                    detail="Focus threshold must be between 0 and 3"
                )
        
        # Stress threshold validation (0-3)
        if "stress_threshold" in update_data and update_data["stress_threshold"] is not None:
            stress_threshold = update_data["stress_threshold"]
            if not (0 <= stress_threshold <= 3):
                raise HTTPException(
                    status_code=400, 
                    detail="Stress threshold must be between 0 and 3"
                )
        
        # Handle role updates - only admins can change roles
        if "role" in update_data and update_data["role"] != user.role:
            if "admin" not in current_user_roles:
                raise HTTPException(
                    status_code=403, 
                    detail="Only administrators can change user roles"
                )
            # Validate role
            valid_roles = ["user", "admin", "doctor", "researcher"]
            if update_data["role"] not in valid_roles:
                raise HTTPException(
                    status_code=400,
                    detail=f"Role must be one of: {', '.join(valid_roles)}"
                )
        
        # Apply updates
        for key, value in update_data.items():
            if hasattr(user, key):
                setattr(user, key, value)

        self.db.commit()
        self.db.refresh(user)
        return user

    def delete_user(self, user_id: int, current_user_id: int, current_user_roles: list = None):
        """
        Soft delete a user by setting is_deleted=True and deleted_at timestamp
        """
        if current_user_roles is None:
            current_user_roles = []
        
        # Fetch the user to delete
        user = self.db.query(models.user.User).filter(models.user.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Authorization check
        if user_id != current_user_id and "admin" not in current_user_roles:
            raise HTTPException(status_code=403, detail="Not authorized to delete this user")

        # Check if user is already deleted
        if hasattr(user, 'is_deleted') and user.is_deleted:
            raise HTTPException(status_code=400, detail="User account is already deleted")
        
        # SOFT DELETE - Set is_deleted=True and deleted_at timestamp
        try:
            from datetime import datetime
            
            # Set is_deleted to True
            if hasattr(user, 'is_deleted'):
                user.is_deleted = True
            
            # Set deleted_at timestamp
            if hasattr(user, 'deleted_at'):
                user.deleted_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(user)
            
            return user
            
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")

    def get_user_by_email(self, email: str):
        # Get user by email
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_id(self, user_id: int):
        # Get user by ID
        return self.db.query(User).filter(User.id == user_id).first()

    def verify_user_password(self, stored_hash: str, password: str) -> bool:
        # Verify the password against the stored hash
        return verify_password(password, stored_hash)