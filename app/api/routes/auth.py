"""
Authentication routes
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db, get_current_user
from app.schemas.user_schema import UserCreate, UserLogin, Token, UserResponse, UserUpdate, PasswordChange
from app.core.security import create_access_token, get_current_token_data, get_password_hash, verify_password
from datetime import timedelta
from app.core.config import settings
from app.crud.user_crud import create_user, get_user_by_username, authenticate_user
from app.schemas.user_schema import TokenData
from app.models.user import User
from fastapi.security import OAuth2PasswordRequestForm

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    db_user = await get_user_by_username(db, user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    db_user = await create_user(db, user)
    logger.info(f"✅ New user registered: {user.username} (email: {user.email})")
    return UserResponse.from_orm(db_user)


@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Login with username or email.
    Returns JWT access token.
    """
    # username field can contain username OR email
    user = await authenticate_user(db, form_data.username, form_data.password)

    if not user:
        logger.warning(f"❌ Failed login attempt for: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    access_token = create_access_token(
        data={"sub": user.username}, 
        expires_delta=access_token_expires
    )

    # Log successful login with admin status
    admin_status = "ADMIN" if user.is_superuser else "USER"
    logger.info(f"✅ Login successful: {user.username} ({admin_status}) - email: {user.email}")

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
@router.post("/refresh", response_model=Token)
async def refresh_access_token(token_data: TokenData = Depends(get_current_token_data)):
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": token_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Get current authenticated user profile with admin status."""
    logger.debug(f"📋 Profile accessed: {current_user.username} (admin: {current_user.is_superuser})")
    return UserResponse.from_orm(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update current user profile.
    
    Allows updating:
    - username
    - email
    - phone
    - address
    """
    logger.info(f"📝 User {current_user.username} updating profile")
    
    # Check if username is being changed and if it's already taken
    if user_update.username and user_update.username != current_user.username:
        existing_user = await db.execute(
            select(User).where(User.username == user_update.username)
        )
        if existing_user.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Username already taken"
            )
        current_user.username = user_update.username
        logger.info(f"   ✏️  Username changed to: {user_update.username}")
    
    # Check if email is being changed and if it's already taken
    if user_update.email and user_update.email != current_user.email:
        existing_user = await db.execute(
            select(User).where(User.email == user_update.email)
        )
        if existing_user.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Email already taken"
            )
        current_user.email = user_update.email
        logger.info(f"   ✉️  Email changed to: {user_update.email}")
    
    # Update phone
    if user_update.phone is not None:
        current_user.phone = user_update.phone
        logger.info(f"   📱 Phone updated")
    
    # Update address
    if user_update.address is not None:
        current_user.address = user_update.address
        logger.info(f"   🏠 Address updated")
    
    await db.commit()
    await db.refresh(current_user)
    
    logger.info(f"✅ Profile updated successfully for user {current_user.username}")
    return UserResponse.from_orm(current_user)


@router.patch("/me/password", status_code=200)
async def change_current_user_password(
    password_change: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Change current user password.
    
    Requires:
    - current_password: Current password for verification
    - new_password: New password (min 6 characters)
    """
    logger.info(f"🔐 User {current_user.username} attempting password change")
    
    # Verify current password
    if not verify_password(password_change.current_password, current_user.hashed_password):
        logger.warning(f"❌ Invalid current password for user {current_user.username}")
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(password_change.new_password)
    await db.commit()
    
    logger.info(f"✅ Password changed successfully for user {current_user.username}")
    return {"message": "Password changed successfully"}
