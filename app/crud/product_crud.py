"""
Product CRUD operations
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.product import Product
from app.schemas.product_schema import ProductCreate

async def get_product(db: AsyncSession, product_id: int):
    result = await db.execute(select(Product).filter(Product.id == product_id))
    return result.scalar_one_or_none()

async def get_products(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(Product).offset(skip).limit(limit))
    return result.scalars().all()

async def get_products_by_name(db: AsyncSession, name: str):
    result = await db.execute(select(Product).filter(Product.name.contains(name)))
    return result.scalars().all()

async def create_product(db: AsyncSession, product: ProductCreate):
    db_product = Product(**product.model_dump())
    db.add(db_product)
    try:
        await db.commit()
        await db.refresh(db_product)
    except Exception:
        await db.rollback()
        raise
    return db_product

async def update_product(db: AsyncSession, product_id: int, product_data: dict):
    db_product = await get_product(db, product_id)
    if db_product:
        for key, value in product_data.items():
            setattr(db_product, key, value)
        try:
            await db.commit()
            await db.refresh(db_product)
        except Exception:
            await db.rollback()
            raise
    return db_product

async def delete_product(db: AsyncSession, product_id: int):
    db_product = await get_product(db, product_id)
    if db_product:
        try:
            await db.delete(db_product)
            await db.commit()
        except Exception:
            await db.rollback()
            raise
    return db_product
