"""
Order CRUD operations
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.order import Order
from app.schemas.order_schema import OrderCreate

async def get_order(db: AsyncSession, order_id: int):
    result = await db.execute(select(Order).filter(Order.id == order_id))
    return result.scalar_one_or_none()

async def get_orders(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(Order).offset(skip).limit(limit))
    return result.scalars().all()

async def get_orders_by_user_id(db: AsyncSession, user_id: int):
    result = await db.execute(select(Order).filter(Order.user_id == user_id))
    return result.scalars().all()

async def create_order(db: AsyncSession, order: OrderCreate):
    db_order = Order(**order.model_dump())
    db.add(db_order)
    try:
        await db.commit()
        await db.refresh(db_order)
    except Exception:
        await db.rollback()
        raise
    return db_order

async def update_order(db: AsyncSession, order_id: int, order_data: dict):
    db_order = await get_order(db, order_id)
    if db_order:
        for key, value in order_data.items():
            setattr(db_order, key, value)
        try:
            await db.commit()
            await db.refresh(db_order)
        except Exception:
            await db.rollback()
            raise
    return db_order

async def delete_order(db: AsyncSession, order_id: int):
    db_order = await get_order(db, order_id)
    if db_order:
        try:
            await db.delete(db_order)
            await db.commit()
        except Exception:
            await db.rollback()
            raise
    return db_order
