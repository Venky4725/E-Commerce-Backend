"""
Product schema definitions
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# Base schema
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    stock_quantity: int = 0

# Create schema
class ProductCreate(ProductBase):
    pass

# Response schema
class ProductResponse(ProductBase):
    id: int
    image_url: Optional[str] = None
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
