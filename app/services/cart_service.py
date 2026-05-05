"""
Cart service — Cache-Aside Pattern

Flow:
  READ  → Redis first → DB fallback → populate cache
  WRITE → DB always  → update/invalidate cache if Redis is up

Redis is NEVER the source of truth. DB is always authoritative.
All Redis calls are wrapped in try/except — Redis failure never breaks the API.
"""
import json
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import redis_client, is_redis_available
from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.schemas.cart_schema import CartResponse, CartItemResponse

logger = logging.getLogger(__name__)

_CART_TTL = 300  # Redis TTL in seconds


# ── Helpers ────────────────────────────────────────────────────────────────────

def _cart_key(user_id: int) -> str:
    return f"cart:user:{user_id}"


def _build_response(cart_id: int, user_id: int, created_at: datetime,
                    updated_at: datetime, items: list) -> CartResponse:
    """Build CartResponse from raw values — never touches ORM attributes."""
    return CartResponse(
        id=cart_id,
        user_id=user_id,
        created_at=created_at,
        updated_at=updated_at,
        cart_items=[
            CartItemResponse(
                id=i.id,
                cart_id=i.cart_id,
                product_id=i.product_id,
                quantity=i.quantity,
            )
            for i in items
        ],
    )


def _serialize(cart_id: int, user_id: int, created_at: datetime,
               updated_at: datetime, items: list) -> str:
    return json.dumps({
        "id": cart_id,
        "user_id": user_id,
        "created_at": created_at.isoformat(),
        "updated_at": updated_at.isoformat(),
        "cart_items": [
            {"id": i.id, "cart_id": i.cart_id,
             "product_id": i.product_id, "quantity": i.quantity}
            for i in items
        ],
    })


def _deserialize(data: dict) -> CartResponse:
    return CartResponse(
        id=data["id"],
        user_id=data["user_id"],
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
        cart_items=[CartItemResponse(**i) for i in data.get("cart_items", [])],
    )


async def _cache_set(user_id: int, cart_id: int, created_at: datetime,
                     updated_at: datetime, items: list) -> None:
    """Write to Redis. Silently skipped if Redis is down."""
    if not await is_redis_available():
        return
    try:
        await redis_client.setex(
            _cart_key(user_id),
            _CART_TTL,
            _serialize(cart_id, user_id, created_at, updated_at, items),
        )
    except Exception as exc:
        logger.warning("Redis SET failed (ignored): %s", exc)


async def _cache_delete(user_id: int) -> None:
    """Invalidate Redis cache. Silently skipped if Redis is down."""
    if not await is_redis_available():
        return
    try:
        await redis_client.delete(_cart_key(user_id))
    except Exception as exc:
        logger.warning("Redis DELETE failed (ignored): %s", exc)


async def _fetch_cart(user_id: int, db: AsyncSession) -> Optional[Cart]:
    """Fetch the cart row from DB. Always returns the oldest cart for the user."""
    result = await db.execute(
        select(Cart)
        .where(Cart.user_id == user_id)
        .order_by(Cart.id.asc())
        .limit(1)
    )
    return result.scalars().first()


async def _fetch_items(cart_id: int, db: AsyncSession) -> List[CartItem]:
    """Fetch all cart items for a given cart_id directly — no ORM lazy load."""
    result = await db.execute(
        select(CartItem).where(CartItem.cart_id == cart_id)
    )
    return list(result.scalars().all())


# ── Service ────────────────────────────────────────────────────────────────────

class CartService:

    # ── READ ──────────────────────────────────────────────────────────────────

    @staticmethod
    async def get_cart(user_id: int, db: AsyncSession) -> Optional[CartResponse]:
        """
        Cache-aside read:
          1. Try Redis
          2. Miss / Redis down → DB
          3. Populate cache from DB result
        """
        # 1. Try Redis
        if await is_redis_available():
            try:
                raw = await redis_client.get(_cart_key(user_id))
                if raw:
                    logger.debug("Cart cache HIT for user %s", user_id)
                    return _deserialize(json.loads(raw))
            except Exception as exc:
                logger.warning("Redis GET failed (ignored): %s", exc)

        # 2. DB
        logger.debug("Cart cache MISS for user %s — querying DB", user_id)
        cart = await _fetch_cart(user_id, db)
        if not cart:
            return None

        items = await _fetch_items(cart.id, db)

        # 3. Populate cache
        await _cache_set(cart.user_id, cart.id, cart.created_at, cart.updated_at, items)

        return _build_response(cart.id, cart.user_id, cart.created_at, cart.updated_at, items)

    @staticmethod
    async def get_or_create_cart(user_id: int, db: AsyncSession) -> CartResponse:
        """Return existing cart or create a new one. One cart per user guaranteed."""
        existing = await CartService.get_cart(user_id, db)
        if existing:
            return existing
        return await CartService.create_cart(user_id, db)

    # ── CREATE ────────────────────────────────────────────────────────────────

    @staticmethod
    async def create_cart(user_id: int, db: AsyncSession) -> CartResponse:
        """
        Create a cart. If one already exists, return it — never creates duplicates.
        """
        cart = await _fetch_cart(user_id, db)
        if cart:
            items = await _fetch_items(cart.id, db)
            await _cache_set(cart.user_id, cart.id, cart.created_at, cart.updated_at, items)
            return _build_response(cart.id, cart.user_id, cart.created_at, cart.updated_at, items)

        now = datetime.utcnow()
        cart = Cart(user_id=user_id, created_at=now, updated_at=now)
        db.add(cart)
        await db.commit()

        # Read back the generated id without touching expired ORM attributes
        cart = await _fetch_cart(user_id, db)
        await _cache_set(cart.user_id, cart.id, cart.created_at, cart.updated_at, [])
        return _build_response(cart.id, cart.user_id, cart.created_at, cart.updated_at, [])

    # ── ITEMS ─────────────────────────────────────────────────────────────────

    @staticmethod
    async def add_item(
        user_id: int, product_id: int, quantity: int, db: AsyncSession
    ) -> CartResponse:
        """
        Add item to cart (auto-creates cart if needed).
        If product already in cart, increments quantity.
        Always writes to DB first, then updates cache.
        """
        cart = await _fetch_cart(user_id, db)
        if not cart:
            now = datetime.utcnow()
            cart = Cart(user_id=user_id, created_at=now, updated_at=now)
            db.add(cart)
            await db.flush()  # get cart.id before adding items

        # Check for existing item
        result = await db.execute(
            select(CartItem).where(
                CartItem.cart_id == cart.id,
                CartItem.product_id == product_id,
            )
        )
        existing = result.scalars().first()

        if existing:
            existing.quantity += quantity
        else:
            db.add(CartItem(
                cart_id=cart.id,
                product_id=product_id,
                quantity=quantity,
            ))

        # Update timestamp
        await db.execute(
            Cart.__table__.update()
            .where(Cart.id == cart.id)
            .values(updated_at=datetime.utcnow())
        )

        await db.commit()

        # Re-fetch clean state from DB
        cart = await _fetch_cart(user_id, db)
        items = await _fetch_items(cart.id, db)
        await _cache_set(cart.user_id, cart.id, cart.created_at, cart.updated_at, items)
        return _build_response(cart.id, cart.user_id, cart.created_at, cart.updated_at, items)

    @staticmethod
    async def update_item(
        user_id: int, product_id: int, quantity: int, db: AsyncSession
    ) -> CartResponse:
        """
        Set item quantity. quantity=0 removes the item.
        Always writes to DB, then updates cache.
        """
        cart = await _fetch_cart(user_id, db)
        if not cart:
            raise HTTPException(status_code=404, detail="Cart not found")

        result = await db.execute(
            select(CartItem).where(
                CartItem.cart_id == cart.id,
                CartItem.product_id == product_id,
            )
        )
        item = result.scalars().first()

        if not item:
            raise HTTPException(status_code=404, detail="Item not found in cart")

        if quantity <= 0:
            await db.delete(item)
        else:
            item.quantity = quantity

        await db.execute(
            Cart.__table__.update()
            .where(Cart.id == cart.id)
            .values(updated_at=datetime.utcnow())
        )

        await db.commit()

        cart = await _fetch_cart(user_id, db)
        items = await _fetch_items(cart.id, db)
        await _cache_set(cart.user_id, cart.id, cart.created_at, cart.updated_at, items)
        return _build_response(cart.id, cart.user_id, cart.created_at, cart.updated_at, items)

    @staticmethod
    async def remove_item(
        user_id: int, product_id: int, db: AsyncSession
    ) -> CartResponse:
        """Remove a specific product from the cart."""
        cart = await _fetch_cart(user_id, db)
        if not cart:
            raise HTTPException(status_code=404, detail="Cart not found")

        result = await db.execute(
            select(CartItem).where(
                CartItem.cart_id == cart.id,
                CartItem.product_id == product_id,
            )
        )
        item = result.scalars().first()

        if item:
            await db.delete(item)
            await db.execute(
                Cart.__table__.update()
                .where(Cart.id == cart.id)
                .values(updated_at=datetime.utcnow())
            )
            await db.commit()

        cart = await _fetch_cart(user_id, db)
        items = await _fetch_items(cart.id, db)
        await _cache_set(cart.user_id, cart.id, cart.created_at, cart.updated_at, items)
        return _build_response(cart.id, cart.user_id, cart.created_at, cart.updated_at, items)

    # ── TOTAL ─────────────────────────────────────────────────────────────────

    @staticmethod
    async def calculate_total(user_id: int, db: AsyncSession) -> float:
        cart = await _fetch_cart(user_id, db)
        if not cart:
            return 0.0

        items = await _fetch_items(cart.id, db)
        if not items:
            return 0.0

        product_ids = [i.product_id for i in items]
        result = await db.execute(
            select(Product).where(Product.id.in_(product_ids))
        )
        products = {p.id: p for p in result.scalars().all()}

        return round(sum(
            products[i.product_id].price * i.quantity
            for i in items
            if i.product_id in products
        ), 2)

    # ── DELETE CART ───────────────────────────────────────────────────────────

    @staticmethod
    async def delete_cart(user_id: int, db: AsyncSession) -> None:
        cart = await _fetch_cart(user_id, db)
        if cart:
            await db.delete(cart)
            await db.commit()
        await _cache_delete(user_id)
