"""
Cart schema definitions
"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Base schema
class CartBase(BaseModel):
    user_id: int

# Create schema
class CartCreate(CartBase):
    pass

# Response schema
class CartResponse(CartBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Cart item schema
class CartItemBase(BaseModel):
    product_id: int
    quantity: int

class CartItemCreate(CartItemBase):
    pass

class CartItemResponse(CartItemBase):
    id: int

    class Config:
        from_attributes = True