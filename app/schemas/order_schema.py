"""
Order schema definitions
"""
from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime
from enum import Enum

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

# Base schema
class OrderBase(BaseModel):
    user_id: int
    status: OrderStatus = OrderStatus.PENDING
    total_amount: float
    shipping_address: str
    billing_address: str

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value):
        if isinstance(value, str):
            return value.upper()
        return value

# Create schema
class OrderCreate(OrderBase):
    pass

# Response schema
class OrderResponse(OrderBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Order item schema
class OrderItemBase(BaseModel):
    product_id: int
    quantity: int
    price: float

class OrderItemCreate(OrderItemBase):
    pass

class OrderItemResponse(OrderItemBase):
    id: int

    class Config:
        from_attributes = True
