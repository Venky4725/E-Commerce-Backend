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
    PROCESSING = "PROCESSING"  # Added for compatibility
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


# ── Order Item ─────────────────────────────────────────────────────────────────

class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    price: float  # price at time of purchase
    product: Optional[dict] = None  # embedded product snapshot

    class Config:
        from_attributes = True


# ── Order ──────────────────────────────────────────────────────────────────────

class OrderCheckout(BaseModel):
    """Used for POST /orders/ — checkout from cart."""
    shipping_address: str
    billing_address: Optional[str] = None  # optional, defaults to shipping_address
    phone: Optional[str] = None  # optional phone number


class OrderUpdate(BaseModel):
    """Used for PUT /orders/{id} — user can update their pending order."""
    shipping_address: Optional[str] = None
    billing_address: Optional[str] = None
    phone: Optional[str] = None


class OrderCreate(BaseModel):
    """Internal use — full order creation."""
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


class OrderStatusUpdate(BaseModel):
    status: OrderStatus

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value):
        if isinstance(value, str):
            return value.upper()
        return value


class OrderResponse(BaseModel):
    id: int
    user_id: int
    status: OrderStatus
    total_amount: float
    shipping_address: str
    billing_address: str
    phone: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemResponse] = []  # renamed from order_items

    class Config:
        from_attributes = True
