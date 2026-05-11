"""
Authentication routes
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.schemas.user_schema import UserCreate, UserLogin, Token, UserResponse
from app.core.security import create_access_token, get_current_token_data
from datetime import timedelta
from app.core.config import settings
from app.crud.user_crud import create_user, get_user_by_username, authenticate_user
from app.schemas.user_schema import TokenData
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
    token_data: TokenData = Depends(get_current_token_data),
    db: AsyncSession = Depends(get_db),
):
    """Get current authenticated user profile with admin status."""
    user = await get_user_by_username(db, token_data.username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    logger.debug(f"📋 Profile accessed: {user.username} (admin: {user.is_superuser})")
    return UserResponse.from_orm(user)
