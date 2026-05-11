"""
User schema definitions
"""
from pydantic import BaseModel
from typing import Optional

# Base schema
class UserBase(BaseModel):
    username: str
    email: str

# Create schema
class UserCreate(UserBase):
    password: str

# Response schema
class UserResponse(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    is_admin: bool  # Alias for is_superuser for frontend compatibility

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
            "is_admin": obj.is_superuser  # is_admin mirrors is_superuser
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