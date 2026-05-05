"""
Cart CRUD operations
"""
# This file is obsolete now - cart operations are handled by Redis in cart_service.py
# All cart functionality moved to app/services/cart_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.cart import Cart

async def get_cart_by_user_id(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(Cart).where(Cart.user_id == user_id)
    )
    return result.scalar_one_or_none()