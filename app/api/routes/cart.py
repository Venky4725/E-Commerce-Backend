"""
Cart routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.schemas.cart_schema import CartCreate, CartResponse, CartItemCreate
from app.services.cart_service import CartService

router = APIRouter()

@router.post("/", response_model=CartResponse)
async def create_new_cart(cart: CartCreate):
    # Create cart in Redis
    try:
        cart_data = await CartService.create_cart(cart.user_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return cart_data

@router.get("/{user_id}", response_model=CartResponse)
async def read_cart(user_id: int):
    # Read cart from Redis 
    try:
        cart_data = await CartService.get_cart(user_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    if not cart_data:
        raise HTTPException(status_code=404, detail="Cart not found")
    return cart_data

@router.put("/{user_id}", response_model=CartResponse)
async def update_cart(user_id: int, cart: CartCreate):
    """Update cart for a user"""
    # Update cart in Redis
    try:
        cart_data = await CartService.update_cart(user_id, cart)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return cart_data

@router.delete("/{user_id}")
async def delete_cart(user_id: int):
    """Delete cart for a user"""
    # Delete cart from Redis
    try:
        await CartService.delete_cart(user_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"message": "Cart deleted successfully"}

@router.post("/{user_id}/items")
async def add_item_to_cart(user_id: int, item: CartItemCreate):
    # Add item to cart in Redis
    try:
        await CartService.add_item(user_id, item.product_id, item.quantity)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"message": "Item added to cart"}

@router.put("/{user_id}/items/{product_id}")
async def update_item_quantity(user_id: int, product_id: int, quantity: int):
    # Update item quantity in cart
    try:
        await CartService.update_item(user_id, product_id, quantity)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"message": "Item quantity updated"}

@router.delete("/{user_id}/items/{product_id}")
async def remove_item_from_cart(user_id: int, product_id: int):
    # Remove item from cart
    try:
        await CartService.remove_item(user_id, product_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"message": "Item removed from cart"}

@router.get("/{user_id}/total")
async def get_cart_total(user_id: int, db: AsyncSession = Depends(get_db)):
    # Calculate cart total
    try:
        total = await CartService.calculate_total(user_id, db)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"total": total}
