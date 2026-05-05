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
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.cart_schema import CartResponse, CartItemCreate, CartItemUpdate
from app.services.cart_service import CartService

router = APIRouter()


@router.post("/", response_model=CartResponse, status_code=200)
async def get_or_create_my_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's cart, or create one if it doesn't exist."""
    return await CartService.get_or_create_cart(current_user.id, db)


@router.get("/me", response_model=CartResponse)
async def get_my_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cart = await CartService.get_cart(current_user.id, db)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    return cart


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
    return await CartService.add_item(current_user.id, item.product_id, item.quantity, db)


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
