"""
Product CRUD operations
"""
from typing import Optional, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.models.product import Product
from app.schemas.product_schema import ProductCreate


async def get_product(db: AsyncSession, product_id: int) -> Optional[Product]:
    result = await db.execute(select(Product).where(Product.id == product_id))
    return result.scalar_one_or_none()


async def get_products(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> Tuple[List[Product], int]:
    """
    Returns (products, total_count) with optional search, sort, and pagination.
    """
    query = select(Product)
    count_query = select(func.count()).select_from(Product)

    # Search filter
    if search:
        search_filter = or_(
            Product.name.ilike(f"%{search}%"),
            Product.description.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # Sorting
    sort_col = getattr(Product, sort_by, Product.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    # Total count
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Paginated results
    result = await db.execute(query.offset(skip).limit(limit))
    products = list(result.scalars().all())

    return products, total


async def get_products_by_name(db: AsyncSession, name: str) -> List[Product]:
    result = await db.execute(
        select(Product).where(Product.name.ilike(f"%{name}%"))
    )
    return list(result.scalars().all())


async def create_product(db: AsyncSession, product: ProductCreate) -> Product:
    db_product = Product(**product.model_dump())
    db.add(db_product)
    try:
        await db.commit()
        await db.refresh(db_product)
    except Exception:
        await db.rollback()
        raise
    return db_product


async def update_product(db: AsyncSession, product_id: int, product_data: dict) -> Optional[Product]:
    db_product = await get_product(db, product_id)
    if not db_product:
        return None
    # Only update provided (non-None) fields
    for key, value in product_data.items():
        if value is not None:
            setattr(db_product, key, value)
    try:
        await db.commit()
        await db.refresh(db_product)
    except Exception:
        await db.rollback()
        raise
    return db_product


async def delete_product(db: AsyncSession, product_id: int) -> Optional[Product]:
    db_product = await get_product(db, product_id)
    if not db_product:
        return None
    try:
        await db.delete(db_product)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return db_product


async def reduce_stock(db: AsyncSession, product_id: int, quantity: int) -> Optional[Product]:
    """Reduce stock by quantity. Raises ValueError if insufficient stock."""
    db_product = await get_product(db, product_id)
    if not db_product:
        raise ValueError(f"Product {product_id} not found")
    if db_product.stock_quantity < quantity:
        raise ValueError(
            f"Insufficient stock for '{db_product.name}'. "
            f"Available: {db_product.stock_quantity}, requested: {quantity}"
        )
    db_product.stock_quantity -= quantity
    await db.flush()  # part of a larger transaction — caller commits
    return db_product
