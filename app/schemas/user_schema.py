"""
User schema definitions
"""
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional

# Base schema
class UserBase(BaseModel):
    username: str
    email: str

# Create schema
class UserCreate(UserBase):
    password: str

# Update profile schema
class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    
    @field_validator('username')
    @classmethod
    def username_min_length(cls, v):
        if v is not None and len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        return v

# Password change schema
class PasswordChange(BaseModel):
    """Schema for changing password."""
    current_password: str
    new_password: str
    
    @field_validator('new_password')
    @classmethod
    def password_min_length(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v

# Response schema
class UserResponse(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    is_admin: bool  # Alias for is_superuser for frontend compatibility
    phone: Optional[str] = None
    address: Optional[str] = None

    class Config:
        from_attributes = True
        
    @classmethod
    def from_orm(cls, obj):
        """Custom from_orm to set is_admin from is_superuser"""
        data = {
            "id": obj.id,
            "username": obj.username,
            "email": obj.email,
            "is_active": obj.is_active,
            "is_superuser": obj.is_superuser,
            "is_admin": obj.is_superuser,  # is_admin mirrors is_superuser
            "phone": getattr(obj, 'phone', None),
            "address": getattr(obj, 'address', None)
        }
        return cls(**data)

# Login schema
class UserLogin(BaseModel):
    username: str
    password: str

# Token schema
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None