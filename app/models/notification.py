"""
Notification model
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String, nullable=False)  # order_cancelled, product_unavailable, order_shipped, admin_update
    is_read = Column(Boolean, default=False)
    related_order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    related_product_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")
    order = relationship("Order", foreign_keys=[related_order_id])
