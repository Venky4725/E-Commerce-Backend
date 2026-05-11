"""
User management routes
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.models.cart import Cart, CartItem
from app.models.notification import Notification
from app.schemas.user_schema import UserResponse, UserUpdate, PasswordChange
from app.core.security import get_password_hash, verify_password

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    """Get current user profile."""
    logger.debug(f"📋 Profile accessed: {current_user.username}")
    return UserResponse.from_orm(current_user)


@router.put("/me", response_model=UserResponse)
async def update_my_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update current user profile.
    
    Allows updating:
    - username
    - email
    - phone
    - address
    """
    logger.info(f"📝 User {current_user.username} updating profile")
    
    # Check if username is being changed and if it's already taken
    if user_update.username and user_update.username != current_user.username:
        existing_user = await db.execute(
            select(User).where(User.username == user_update.username)
        )
        if existing_user.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Username already taken"
            )
        current_user.username = user_update.username
        logger.info(f"   ✏️  Username changed to: {user_update.username}")
    
    # Check if email is being changed and if it's already taken
    if user_update.email and user_update.email != current_user.email:
        existing_user = await db.execute(
            select(User).where(User.email == user_update.email)
        )
        if existing_user.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Email already taken"
            )
        current_user.email = user_update.email
        logger.info(f"   ✉️  Email changed to: {user_update.email}")
    
    # Update phone
    if user_update.phone is not None:
        current_user.phone = user_update.phone
        logger.info(f"   📱 Phone updated")
    
    # Update address
    if user_update.address is not None:
        current_user.address = user_update.address
        logger.info(f"   🏠 Address updated")
    
    await db.commit()
    await db.refresh(current_user)
    
    logger.info(f"✅ Profile updated successfully for user {current_user.username}")
    return UserResponse.from_orm(current_user)


@router.patch("/me/password", status_code=200)
async def change_my_password(
    password_change: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Change current user password.
    
    Requires:
    - current_password: Current password for verification
    - new_password: New password (min 6 characters)
    """
    logger.info(f"🔐 User {current_user.username} attempting password change")
    
    # Verify current password
    if not verify_password(password_change.current_password, current_user.hashed_password):
        logger.warning(f"❌ Invalid current password for user {current_user.username}")
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(password_change.new_password)
    await db.commit()
    
    logger.info(f"✅ Password changed successfully for user {current_user.username}")
    return {"message": "Password changed successfully"}


@router.delete("/me", status_code=200)
async def delete_my_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete current user account.
    
    Account deletion logic:
    - KEEPS: DELIVERED orders (for analytics and history)
    - KEEPS: SHIPPED orders (already in transit)
    - CANCELS: PENDING, CONFIRMED, PROCESSING orders
    - DELETES: Cart items
    - DELETES: Notifications
    - SOFT DELETE: User marked as inactive (is_active = False)
    
    This ensures:
    - Revenue analytics remain accurate
    - Order history is preserved
    - Active orders are properly cancelled
    - User data is anonymized but not lost
    """
    logger.info(f"🗑️  User {current_user.username} (ID: {current_user.id}) requesting account deletion")
    
    # Get all user orders
    orders_result = await db.execute(
        select(Order).where(Order.user_id == current_user.id)
    )
    orders = list(orders_result.scalars().all())
    
    logger.info(f"   📦 Found {len(orders)} orders for user {current_user.id}")
    
    # Categorize orders
    delivered_orders = []
    shipped_orders = []
    cancelled_orders = []
    
    for order in orders:
        if order.status == OrderStatus.DELIVERED:
            delivered_orders.append(order)
        elif order.status == OrderStatus.SHIPPED:
            shipped_orders.append(order)
        elif order.status in [OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PROCESSING]:
            # Cancel these orders and restore stock
            old_status = order.status.value
            order.status = OrderStatus.CANCELLED
            cancelled_orders.append(order)
            
            # Restore stock for cancelled orders
            order_items_result = await db.execute(
                select(OrderItem).where(OrderItem.order_id == order.id)
            )
            order_items = list(order_items_result.scalars().all())
            
            for item in order_items:
                from app.models.product import Product
                product_result = await db.execute(
                    select(Product).where(Product.id == item.product_id)
                )
                product = product_result.scalar_one_or_none()
                if product:
                    product.stock_quantity += item.quantity
                    logger.info(f"      ↩️  Restored {item.quantity} units of product {item.product_id}")
            
            logger.info(f"      ❌ Order #{order.id} cancelled (was {old_status})")
    
    logger.info(f"   ✅ Kept {len(delivered_orders)} DELIVERED orders")
    logger.info(f"   ✅ Kept {len(shipped_orders)} SHIPPED orders")
    logger.info(f"   ❌ Cancelled {len(cancelled_orders)} active orders")
    
    # Delete cart items
    cart_result = await db.execute(
        select(Cart).where(Cart.user_id == current_user.id)
    )
    cart = cart_result.scalar_one_or_none()
    
    if cart:
        await db.execute(
            CartItem.__table__.delete().where(CartItem.cart_id == cart.id)
        )
        await db.delete(cart)
        logger.info(f"   🛒 Deleted cart")
    
    # Delete notifications
    notifications_result = await db.execute(
        select(Notification).where(Notification.user_id == current_user.id)
    )
    notifications = list(notifications_result.scalars().all())
    
    for notification in notifications:
        await db.delete(notification)
    
    logger.info(f"   📬 Deleted {len(notifications)} notifications")
    
    # Soft delete user (mark as inactive)
    current_user.is_active = False
    current_user.email = f"deleted_{current_user.id}@deleted.com"  # Anonymize email
    current_user.username = f"deleted_user_{current_user.id}"  # Anonymize username
    
    await db.commit()
    
    logger.info(f"✅ Account deleted successfully for user ID {current_user.id}")
    logger.info(f"   📊 Order summary:")
    logger.info(f"      - DELIVERED orders: {len(delivered_orders)} (kept for analytics)")
    logger.info(f"      - SHIPPED orders: {len(shipped_orders)} (kept)")
    logger.info(f"      - Cancelled orders: {len(cancelled_orders)}")
    
    return {
        "message": "Account deleted successfully",
        "orders_kept": len(delivered_orders) + len(shipped_orders),
        "orders_cancelled": len(cancelled_orders),
        "details": {
            "delivered_orders": len(delivered_orders),
            "shipped_orders": len(shipped_orders),
            "cancelled_orders": len(cancelled_orders)
        }
    }
