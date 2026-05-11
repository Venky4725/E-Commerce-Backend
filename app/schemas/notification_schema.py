"""
Notification schema definitions
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class NotificationCreate(BaseModel):
    """Schema for creating a notification."""
    user_id: int
    title: str
    message: str
    type: str  # order_cancelled, product_unavailable, order_shipped, admin_update
    related_order_id: Optional[int] = None
    related_product_id: Optional[int] = None


class NotificationResponse(BaseModel):
    """Schema for notification response."""
    id: int
    user_id: int
    title: str
    message: str
    type: str
    is_read: bool
    related_order_id: Optional[int] = None
    related_product_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationMarkRead(BaseModel):
    """Schema for marking notification as read."""
    is_read: bool = True
