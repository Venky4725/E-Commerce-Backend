"""
Cart routes

All endpoints derive the user identity from the JWT token.
No user_id is accepted from the request body — prevents spoofing.

Endpoints:
  POST   /cart/              → get or create cart
  GET    /cart/me            → get my cart
  DELETE /cart/me            → delete my cart
  POST   /cart/me/items      → add item
  PUT    /cart/me/items/{id} → update item quantity (0 = remove)
  DELETE /cart/me/items/{id} → remove item
  GET    /cart/me/total      → cart total
  GET    /cart/{user_id}     → admin: get any user's cart
"""
import logging
import traceback
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.cart_schema import CartResponse, CartItemCreate, CartItemUpdate
from app.services.cart_service import CartService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=CartResponse, status_code=200)
async def get_or_create_my_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's cart, or create one if it doesn't exist."""
    try:
        logger.debug(f"📦 Get or create cart for user {current_user.id}")
        return await CartService.get_or_create_cart(current_user.id, db)
    except Exception as e:
        logger.error(f"❌ Error getting/creating cart for user {current_user.id}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get or create cart: {str(e)}"
        )


@router.get("/me", response_model=CartResponse)
async def get_my_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's cart."""
    try:
        logger.debug(f"📦 Fetching cart for user {current_user.id}")
        cart = await CartService.get_cart(current_user.id, db)
        if not cart:
            logger.debug(f"   Cart not found for user {current_user.id}, returning empty cart")
            # Return empty cart instead of 404
            return CartResponse(
                id=0,
                user_id=current_user.id,
                created_at=None,
                updated_at=None,
                cart_items=[],
            )
        logger.debug(f"   Cart found with {len(cart.cart_items)} items")
        return cart
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching cart for user {current_user.id}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch cart: {str(e)}"
        )


@router.delete("/me", status_code=200)
async def delete_my_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await CartService.delete_cart(current_user.id, db)
    return {"message": "Cart deleted successfully"}


@router.post("/me/items", response_model=CartResponse, status_code=200)
async def add_item(
    item: CartItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a product to the cart. Auto-creates the cart if needed."""
    try:
        logger.debug(f"➕ Adding item to cart: user={current_user.id}, product={item.product_id}, qty={item.quantity}")
        return await CartService.add_item(current_user.id, item.product_id, item.quantity, db)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error adding item to cart: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add item to cart: {str(e)}"
        )


@router.put("/me/items/{product_id}", response_model=CartResponse)
async def update_item(
    product_id: int,
    item: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update item quantity. Send quantity=0 to remove the item."""
    return await CartService.update_item(current_user.id, product_id, item.quantity, db)


@router.delete("/me/items/{product_id}", response_model=CartResponse)
async def remove_item(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CartService.remove_item(current_user.id, product_id, db)


@router.get("/me/total")
async def get_cart_total(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    total = await CartService.calculate_total(current_user.id, db)
    return {"total": total}


@router.get("/{user_id}", response_model=CartResponse)
async def get_cart_by_user_id(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin endpoint — fetch any user's cart by user ID."""
    cart = await CartService.get_cart(user_id, db)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    return cart
