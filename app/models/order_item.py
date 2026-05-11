"""
Order Item model
"""
from sqlalchemy import Column, Integer, ForeignKey, Float, String, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    
    # Product snapshot - stored at time of purchase
    product_name = Column(String, nullable=True)  # Product name at purchase time
    product_image_url = Column(String, nullable=True)  # Product image at purchase time

    # Relationships
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product")