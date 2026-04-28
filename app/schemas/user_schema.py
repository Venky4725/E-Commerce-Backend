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

    class Config:
        from_attributes = True

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