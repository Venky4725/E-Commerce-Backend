"""
Cart schema definitions
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class CartItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0, description="Must be at least 1")


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=0, description="Set to 0 to remove the item")


class ProductSnapshot(BaseModel):
    """Embedded product info returned inside cart items."""
    id: int
    name: str
    price: float
    image_url: Optional[str] = None
    stock_quantity: int

    class Config:
        from_attributes = True


class CartItemResponse(BaseModel):
    id: int
    cart_id: int
    product_id: int
    quantity: int
    product: Optional[ProductSnapshot] = None

    class Config:
        from_attributes = True


class CartResponse(BaseModel):
    id: int
    user_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    cart_items: List[CartItemResponse] = []

    class Config:
        from_attributes = True
