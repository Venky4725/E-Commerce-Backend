"""
Orders routes

POST /orders/                    — checkout from cart (authenticated)
GET  /orders/my                  — my orders (authenticated user)
GET  /orders/all                 — all orders (admin only)
GET  /orders/{id}                — single order (authenticated)
PUT  /orders/{id}/status         — update status (admin)
"""
import logging
import traceback
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, get_current_admin_user
from app.models.user import User
from app.schemas.order_schema import OrderCheckout, OrderResponse, OrderStatusUpdate, OrderUpdate
from app.services.order_service import OrderService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=OrderResponse, status_code=201)
async def checkout(
    order_data: OrderCheckout,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Checkout the current user's cart.
    - Validates stock for every item
    - Creates the order and order items
    - Reduces product stock
    - Clears the cart
    """
    try:
        logger.info(f"🛒 User {current_user.username} initiating checkout")
        # Use shipping_address for billing if not provided
        billing_addr = order_data.billing_address or order_data.shipping_address
        
        order = await OrderService.checkout(
            user_id=current_user.id,
            shipping_address=order_data.shipping_address,
            billing_address=billing_addr,
            phone=order_data.phone,
            db=db,
        )
        logger.info(f"✅ Checkout successful for user {current_user.username}, order ID: {order.id}")
        return order
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Checkout failed for user {current_user.id}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Checkout failed: {str(e)}"
        )


@router.get("/my", response_model=list[OrderResponse])
async def get_my_orders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all orders for the currently authenticated user.
    Returns only the logged-in user's orders.
    """
    try:
        logger.info(f"📋 User {current_user.username} fetching their orders")
        orders = await OrderService.get_user_orders(current_user.id, db)
        logger.info(f"   Found {len(orders)} orders for user {current_user.username}")
        return orders
    except Exception as e:
        logger.error(f"❌ Error fetching orders for user {current_user.id}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch orders: {str(e)}"
        )


@router.get("/all", response_model=list[OrderResponse])
async def get_all_orders(
    skip: int = Query(0, ge=0, description="Number of orders to skip"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of orders to return"),
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin only: Get all orders from all users with pagination.
    Requires admin authentication.
    """
    logger.info(f"🔧 Admin {current_admin.username} fetching all orders (skip={skip}, limit={limit})")
    orders = await OrderService.get_all_orders(db, skip=skip, limit=limit)
    logger.info(f"   Found {len(orders)} orders")
    return orders


@router.get("/user/{user_id}", response_model=list[OrderResponse])
async def get_user_orders(
    user_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin only: Get orders for a specific user by user ID.
    Requires admin authentication.
    """
    logger.info(f"🔧 Admin {current_admin.username} fetching orders for user {user_id}")
    orders = await OrderService.get_user_orders(user_id, db)
    logger.info(f"   Found {len(orders)} orders for user {user_id}")
    return orders


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single order by ID.
    Users can only view their own orders unless they are admin.
    """
    logger.info(f"📋 User {current_user.username} fetching order {order_id}")
    order = await OrderService.get_order(order_id, db)
    
    # Authorization check: users can only view their own orders
    if order.user_id != current_user.id and not current_user.is_superuser:
        logger.warning(f"❌ User {current_user.username} attempted to view order {order_id} (not owner)")
        raise HTTPException(
            status_code=403,
            detail="Access denied. You can only view your own orders."
        )
    
    return order


@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: int,
    order_update: OrderUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update order details (shipping address, billing address, phone).
    - Only owner or admin can update
    - Only PENDING orders can be updated
    """
    update_data = order_update.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided to update")
    
    return await OrderService.update_order(
        order_id,
        current_user.id,
        current_user.is_superuser,
        update_data,
        db,
    )


@router.put("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    status_update: OrderStatusUpdate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin: Update order status.
    Valid progression: PENDING → CONFIRMED → SHIPPED → DELIVERED
    CANCELLED is allowed from PENDING or CONFIRMED only.
    """
    logger.info(f"🔧 Admin {current_admin.username} updating order {order_id} status to {status_update.status.value}")
    return await OrderService.update_order_status(order_id, status_update.status.value, db)


@router.delete("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel an order (sets status to CANCELLED).
    - Only owner or admin can cancel
    - Only PENDING, CONFIRMED, or PROCESSING orders can be cancelled
    - Restores product stock automatically
    - Order remains in history with CANCELLED status
    """
    logger.info(f"🗑️  User {current_user.username} cancelling order {order_id}")
    order = await OrderService.cancel_order(order_id, current_user.id, current_user.is_superuser, db)
    return order


@router.delete("/{order_id}", status_code=200)
async def delete_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an order.
    - Admin can delete any order
    - Regular users can only delete their own PENDING orders
    - Deletes order items automatically
    """
    logger.info(f"🗑️  User {current_user.username} (admin: {current_user.is_superuser}) deleting order {order_id}")
    await OrderService.delete_order(order_id, current_user.id, current_user.is_superuser, db)
    logger.info(f"✅ Order {order_id} deleted successfully")
    return {"message": "Order deleted successfully", "order_id": order_id}


@router.delete("/", status_code=200)
async def clear_all_orders(
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    DEV ONLY: Delete all orders and order items.
    Requires admin access.
    """
    logger.warning(f"🔧 Admin {current_admin.username} clearing ALL orders!")
    await OrderService.clear_all_orders(db)
    return {"message": "All orders cleared successfully"}
