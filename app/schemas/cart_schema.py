"""
Cart schema definitions
"""
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime


# ── Cart Item ──────────────────────────────────────────────────────────────────

class CartItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0, description="Must be at least 1")


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=0, description="Set to 0 to remove the item")


class CartItemResponse(BaseModel):
    id: int
    cart_id: int
    product_id: int
    quantity: int

    class Config:
        from_attributes = True


# ── Cart ───────────────────────────────────────────────────────────────────────

class CartResponse(BaseModel):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    cart_items: List[CartItemResponse] = []

    class Config:
        from_attributes = True
