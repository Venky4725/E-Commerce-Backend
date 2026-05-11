"""
Admin schema definitions
"""
from pydantic import BaseModel


class AdminDashboardStats(BaseModel):
    """Admin dashboard statistics response."""
    total_revenue: float
    total_users: int
    total_products: int
    total_orders: int
    delivered_orders: int
    pending_orders: int
    confirmed_orders: int
    processing_orders: int
    shipped_orders: int
    cancelled_orders: int


class RevenueByPeriod(BaseModel):
    """Revenue statistics by period."""
    period: str
    revenue: float
    delivered_orders: int
