"""
Orders routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_db
from app.schemas.order_schema import OrderCreate, OrderResponse
from app.crud.order_crud import create_order, get_orders, get_orders_by_user_id, update_order, get_order
from app.models.user import User
from app.services.order_service import OrderService
from enum import Enum

router = APIRouter()

@router.post("/", response_model=OrderResponse)
async def create_new_order(order: OrderCreate, db: AsyncSession = Depends(get_db)):
    # Validate user exists before creating order to prevent FK violations
    result = await db.execute(select(User).filter(User.id == order.user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="User does not exist"
        )
        
    db_order = await create_order(db, order)
    # Process order with email task
    await OrderService.process_order({
        "id": db_order.id,
        "user_id": db_order.user_id,
        "status": db_order.status.value,
        "total_amount": db_order.total_amount,
        "shipping_address": db_order.shipping_address,
        "billing_address": db_order.billing_address,
    })
    return db_order

@router.get("/", response_model=list[OrderResponse])
async def read_orders(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    orders = await get_orders(db, skip=skip, limit=limit)
    return orders

@router.get("/user/{user_id}", response_model=list[OrderResponse])
async def read_user_orders(user_id: int, db: AsyncSession = Depends(get_db)):
    orders = await get_orders_by_user_id(db, user_id)
    return orders

@router.put("/{order_id}/status")
async def update_order_status(
    order_id: int,
    status: str,
    db: AsyncSession = Depends(get_db)
):
    """Update order status with progression validation"""
    # Get the current order
    db_order = await get_order(db, order_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Define status progression
    status_order = [
        "PENDING",
        "CONFIRMED", 
        "SHIPPED",
        "DELIVERED"
    ]
    
    # Get current status position
    try:
        current_index = status_order.index(db_order.status.value)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid current order status")
        
    # Get requested status position  
    try:
        requested_index = status_order.index(status.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status requested")
    
    # Validate status progression
    if requested_index < current_index:
        raise HTTPException(
            status_code=400, 
            detail="Status progression invalid. Cannot go backwards."
        )
    
    # Update order status only if valid progression
    if requested_index > current_index:
        # Update order status
        update_data = {"status": status.upper()}
        db_order = await update_order(db, order_id, update_data)
        
        # Process order with email task (optional)
        # await OrderService.process_order_update(db_order.__dict__)
        
        return {"message": f"Order status updated to {status.upper()}"}
    else:
        # Status hasn't changed
        return {"message": f"Order status remains {db_order.status.value}"}
