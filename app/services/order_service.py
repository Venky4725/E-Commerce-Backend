"""
Order service — checkout flow with stock validation and cart clearing
"""
import logging
from datetime import datetime
from typing import List

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cart import Cart, CartItem
from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.models.product import Product
from app.schemas.order_schema import OrderResponse, OrderItemResponse

logger = logging.getLogger(__name__)


async def _fetch_cart_items(user_id: int, db: AsyncSession):
    """Fetch cart and its items for the given user."""
    cart_result = await db.execute(
        select(Cart).where(Cart.user_id == user_id).order_by(Cart.id.asc()).limit(1)
    )
    cart = cart_result.scalars().first()
    if not cart:
        return None, []

    items_result = await db.execute(
        select(CartItem).where(CartItem.cart_id == cart.id)
    )
    return cart, list(items_result.scalars().all())


def _build_order_response(order: Order, order_items: List[OrderItem], products: dict) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        status=order.status.value,
        total_amount=order.total_amount,
        shipping_address=order.shipping_address,
        billing_address=order.billing_address,
        phone=order.phone,
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=[  # renamed from order_items
            OrderItemResponse(
                id=oi.id,
                product_id=oi.product_id,
                quantity=oi.quantity,
                price=oi.price,
                product={
                    "id": products[oi.product_id].id if oi.product_id in products else oi.product_id,
                    "name": oi.product_name or (products[oi.product_id].name if oi.product_id in products else "Unknown Product"),
                    "price": oi.price,  # Use stored price from order item
                    "image_url": oi.product_image_url or (products[oi.product_id].image_url if oi.product_id in products else None),
                    "stock_quantity": products[oi.product_id].stock_quantity if oi.product_id in products else 0,
                } if (oi.product_id in products or oi.product_name) else None,
            )
            for oi in order_items
        ],
    )


class OrderService:

    @staticmethod
    async def checkout(
        user_id: int,
        shipping_address: str,
        billing_address: str,
        phone: str = None,
        db: AsyncSession = None,
    ) -> OrderResponse:
        """
        Full checkout flow:
          1. Load cart items
          2. Validate stock for every item
          3. Create Order + OrderItems
          4. Reduce stock for each product
          5. Clear the cart
          All steps run in a single transaction — rolls back on any failure.
        """
        cart, cart_items = await _fetch_cart_items(user_id, db)

        if not cart or not cart_items:
            raise HTTPException(status_code=400, detail="Cart is empty")

        # Load all products in one query
        product_ids = [ci.product_id for ci in cart_items]
        products_result = await db.execute(
            select(Product).where(Product.id.in_(product_ids))
        )
        products = {p.id: p for p in products_result.scalars().all()}

        # ── Validate stock ────────────────────────────────────────────────────
        for ci in cart_items:
            product = products.get(ci.product_id)
            if not product:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product {ci.product_id} not found",
                )
            if ci.quantity > product.stock_quantity:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Insufficient stock for '{product.name}'. "
                        f"Available: {product.stock_quantity}, in cart: {ci.quantity}"
                    ),
                )

        # ── Calculate total ───────────────────────────────────────────────────
        total = round(sum(
            products[ci.product_id].price * ci.quantity
            for ci in cart_items
        ), 2)

        # ── Create Order ──────────────────────────────────────────────────────
        now = datetime.utcnow()
        order = Order(
            user_id=user_id,
            status=OrderStatus.PENDING,
            total_amount=total,
            shipping_address=shipping_address,
            billing_address=billing_address,
            phone=phone,
            created_at=now,
            updated_at=now,
        )
        db.add(order)
        await db.flush()  # get order.id

        # ── Create OrderItems + reduce stock ──────────────────────────────────
        order_items = []
        for ci in cart_items:
            product = products[ci.product_id]
            oi = OrderItem(
                order_id=order.id,
                product_id=ci.product_id,
                quantity=ci.quantity,
                price=product.price,
                product_name=product.name,  # Store product snapshot
                product_image_url=product.image_url,  # Store product snapshot
            )
            db.add(oi)
            product.stock_quantity -= ci.quantity  # reduce stock
            order_items.append(oi)

        # ── Clear cart ────────────────────────────────────────────────────────
        await db.execute(
            CartItem.__table__.delete().where(CartItem.cart_id == cart.id)
        )
        await db.execute(
            Cart.__table__.update()
            .where(Cart.id == cart.id)
            .values(updated_at=now)
        )

        await db.commit()

        # Invalidate cart cache
        try:
            from app.core.redis_client import redis_client, is_redis_available
            if await is_redis_available():
                await redis_client.delete(f"cart:user:{user_id}")
        except Exception as exc:
            logger.warning("Redis cart invalidation failed (ignored): %s", exc)

        # Trigger confirmation email (non-blocking)
        try:
            from app.tasks.email_tasks import send_order_confirmation_email
            send_order_confirmation_email.delay(
                user_email="",
                order_id=order.id,
                order_details={"id": order.id, "total": total},
            )
        except Exception as exc:
            logger.warning("Order email task could not be queued: %s", exc)

        # Re-fetch order items with IDs
        oi_result = await db.execute(
            select(OrderItem).where(OrderItem.order_id == order.id)
        )
        order_items = list(oi_result.scalars().all())

        # Refresh products (stock changed)
        products_result = await db.execute(
            select(Product).where(Product.id.in_(product_ids))
        )
        products = {p.id: p for p in products_result.scalars().all()}

        return _build_order_response(order, order_items, products)

    @staticmethod
    async def get_order(order_id: int, db: AsyncSession) -> OrderResponse:
        order_result = await db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = order_result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        oi_result = await db.execute(
            select(OrderItem).where(OrderItem.order_id == order_id)
        )
        order_items = list(oi_result.scalars().all())

        product_ids = [oi.product_id for oi in order_items]
        products_result = await db.execute(
            select(Product).where(Product.id.in_(product_ids))
        )
        products = {p.id: p for p in products_result.scalars().all()}

        return _build_order_response(order, order_items, products)

    @staticmethod
    async def get_user_orders(user_id: int, db: AsyncSession) -> List[OrderResponse]:
        orders_result = await db.execute(
            select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc())
        )
        orders = list(orders_result.scalars().all())

        responses = []
        for order in orders:
            oi_result = await db.execute(
                select(OrderItem).where(OrderItem.order_id == order.id)
            )
            order_items = list(oi_result.scalars().all())

            product_ids = [oi.product_id for oi in order_items]
            products_result = await db.execute(
                select(Product).where(Product.id.in_(product_ids))
            )
            products = {p.id: p for p in products_result.scalars().all()}

            responses.append(_build_order_response(order, order_items, products))

        return responses

    @staticmethod
    async def get_all_orders(
        db: AsyncSession, skip: int = 0, limit: int = 50
    ) -> List[OrderResponse]:
        orders_result = await db.execute(
            select(Order).order_by(Order.created_at.desc()).offset(skip).limit(limit)
        )
        orders = list(orders_result.scalars().all())

        responses = []
        for order in orders:
            oi_result = await db.execute(
                select(OrderItem).where(OrderItem.order_id == order.id)
            )
            order_items = list(oi_result.scalars().all())

            product_ids = [oi.product_id for oi in order_items]
            products_result = await db.execute(
                select(Product).where(Product.id.in_(product_ids))
            )
            products = {p.id: p for p in products_result.scalars().all()}

            responses.append(_build_order_response(order, order_items, products))

        return responses

    @staticmethod
    async def update_order_status(
        order_id: int, new_status: str, db: AsyncSession
    ) -> OrderResponse:
        """
        Update order status.
        Valid progressions:
        - PENDING → CONFIRMED/PROCESSING → SHIPPED → DELIVERED
        - PENDING/CONFIRMED/PROCESSING → CANCELLED
        """
        order_result = await db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = order_result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        # Normalize status to uppercase
        new_status = new_status.upper()
        
        # Validate status value
        valid_statuses = ["PENDING", "CONFIRMED", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED"]
        if new_status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {new_status}. Valid statuses: {', '.join(valid_statuses)}"
            )

        # Status progression validation
        current = order.status.value
        
        # Define allowed transitions
        allowed_transitions = {
            "PENDING": ["CONFIRMED", "PROCESSING", "CANCELLED"],
            "CONFIRMED": ["PROCESSING", "SHIPPED", "CANCELLED"],
            "PROCESSING": ["SHIPPED", "CANCELLED"],
            "SHIPPED": ["DELIVERED"],
            "DELIVERED": [],  # Cannot change from DELIVERED
            "CANCELLED": []   # Cannot change from CANCELLED
        }
        
        # Check if transition is allowed
        if new_status == current:
            # Same status, just return the order
            return await OrderService.get_order(order_id, db)
        
        if new_status not in allowed_transitions.get(current, []):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot change order status from {current} to {new_status}. Allowed transitions from {current}: {', '.join(allowed_transitions.get(current, []))}"
            )

        # Update order status
        old_status = order.status.value
        order.status = OrderStatus[new_status]
        order.updated_at = datetime.utcnow()
        await db.commit()
        
        # Create notification for user
        try:
            from app.services.notification_service import NotificationService
            # IMPORTANT: Notification is sent to ORDER OWNER (order.user_id), NOT the admin who updated it
            await NotificationService.notify_order_status_change(
                user_id=order.user_id,  # Order owner receives notification
                order_id=order.id,
                new_status=new_status,
                db=db
            )
            logger.info(f"📬 Notification sent to ORDER OWNER (user_id={order.user_id}) for order {order.id} status change: {old_status} → {new_status}")
        except Exception as e:
            logger.warning(f"⚠️  Failed to create notification: {e}")

        return await OrderService.get_order(order_id, db)

    @staticmethod
    async def process_order(order_data: dict):
        """Legacy helper — kept for backward compatibility."""
        try:
            from app.tasks.email_tasks import send_order_confirmation_email
            send_order_confirmation_email.delay(
                user_email=order_data.get("user_email", ""),
                order_id=order_data.get("id", 0),
                order_details=order_data,
            )
        except Exception as exc:
            logger.warning("Order email task could not be queued: %s", exc)
        return order_data

    @staticmethod
    async def delete_order(
        order_id: int, user_id: int, is_superuser: bool, db: AsyncSession
    ) -> None:
        """
        Delete an order.
        - Admin can delete any order regardless of status
        - Regular users can only delete their own PENDING orders
        - Deletes order items first, then order
        """
        # Fetch order
        order_result = await db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = order_result.scalar_one_or_none()
        
        if not order:
            logger.warning(f"❌ Order {order_id} not found")
            raise HTTPException(status_code=404, detail=f"Order with ID {order_id} not found")

        # Authorization check
        is_owner = order.user_id == user_id
        
        if not is_owner and not is_superuser:
            logger.warning(f"❌ User {user_id} attempted to delete order {order_id} (not owner, not admin)")
            raise HTTPException(
                status_code=403,
                detail="Access denied. You can only delete your own orders.",
            )
        
        # Status check for regular users (admin can delete any status)
        if not is_superuser and order.status != OrderStatus.PENDING:
            logger.warning(f"❌ User {user_id} attempted to delete non-PENDING order {order_id} (status: {order.status.value})")
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete order with status {order.status.value}. Only PENDING orders can be deleted by users. Contact admin for assistance.",
            )
        
        # Log deletion
        role = "admin" if is_superuser else "user"
        logger.info(f"🗑️  Deleting order {order_id} (status: {order.status.value}) by {role} {user_id}")
        
        # Get order items before deletion (for notification)
        order_items_result = await db.execute(
            select(OrderItem).where(OrderItem.order_id == order_id)
        )
        order_items = list(order_items_result.scalars().all())
        
        # Delete order items first
        deleted_items = await db.execute(
            OrderItem.__table__.delete().where(OrderItem.order_id == order_id)
        )
        logger.debug(f"   Deleted {deleted_items.rowcount} order items")
        
        # Delete order
        await db.delete(order)
        await db.commit()
        
        # Create notification if deleted by admin
        if is_superuser and not is_owner:
            try:
                from app.services.notification_service import NotificationService
                from app.schemas.notification_schema import NotificationCreate
                
                # Build product description for notification
                product_description = "order"
                if order_items:
                    first_product = order_items[0].product_name or "product"
                    if len(order_items) == 1:
                        product_description = f"{first_product} order"
                    else:
                        additional_count = len(order_items) - 1
                        product_description = f"order containing {first_product} and {additional_count} more item{'s' if additional_count > 1 else ''}"
                
                notification = NotificationCreate(
                    user_id=order.user_id,
                    title="Order Deleted by Admin",
                    message=f"Your {product_description} has been deleted by an administrator. If you have any questions, please contact support.",
                    type="order_deleted",
                    related_order_id=order_id
                )
                await NotificationService.create_notification(notification, db)
                logger.info(f"📬 Notification sent to user {order.user_id} about order {order_id} ({product_description}) deletion")
            except Exception as e:
                logger.warning(f"⚠️  Failed to create notification: {e}")
        
        logger.info(f"✅ Order {order_id} deleted successfully by {role} {user_id}")

    @staticmethod
    async def update_order(
        order_id: int,
        user_id: int,
        is_superuser: bool,
        update_data: dict,
        db: AsyncSession,
    ) -> OrderResponse:
        """
        Update order details (shipping address, phone, etc.).
        Only allowed if order status is PENDING.
        Only owner or admin can update.
        """
        order_result = await db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = order_result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        # Authorization check
        if order.user_id != user_id and not is_superuser:
            raise HTTPException(
                status_code=403,
                detail="You can only update your own orders",
            )

        # Status check
        if order.status != OrderStatus.PENDING:
            raise HTTPException(
                status_code=403,
                detail=f"Cannot update order with status {order.status.value}. Only PENDING orders can be updated.",
            )

        # Update fields
        for key, value in update_data.items():
            if value is not None and hasattr(order, key):
                setattr(order, key, value)

        order.updated_at = datetime.utcnow()
        await db.commit()

        return await OrderService.get_order(order_id, db)

    @staticmethod
    async def cancel_order(
        order_id: int,
        user_id: int,
        is_superuser: bool,
        db: AsyncSession,
    ) -> OrderResponse:
        """
        Cancel an order by setting status to CANCELLED.
        - Only owner or admin can cancel
        - Only PENDING/CONFIRMED/PROCESSING orders can be cancelled
        - Restores product stock
        - Order remains in history with CANCELLED status
        """
        # Fetch order
        order_result = await db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = order_result.scalar_one_or_none()
        
        if not order:
            logger.warning(f"❌ Order {order_id} not found for cancellation")
            raise HTTPException(status_code=404, detail=f"Order with ID {order_id} not found")

        # Authorization check
        is_owner = order.user_id == user_id
        
        if not is_owner and not is_superuser:
            logger.warning(f"❌ User {user_id} attempted to cancel order {order_id} (not owner, not admin)")
            raise HTTPException(
                status_code=403,
                detail="Access denied. You can only cancel your own orders.",
            )

        # Status check - can only cancel PENDING, CONFIRMED, or PROCESSING orders
        if order.status.value not in ["PENDING", "CONFIRMED", "PROCESSING"]:
            logger.warning(f"❌ Attempted to cancel order {order_id} with status {order.status.value}")
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel order with status {order.status.value}. Only PENDING, CONFIRMED, or PROCESSING orders can be cancelled.",
            )

        role = "admin" if is_superuser else "user"
        logger.info(f"🔄 Cancelling order {order_id} by {role} {user_id}")

        # Get order items
        oi_result = await db.execute(
            select(OrderItem).where(OrderItem.order_id == order_id)
        )
        order_items = list(oi_result.scalars().all())

        # Restore stock for each product
        product_ids = [oi.product_id for oi in order_items]
        if product_ids:
            products_result = await db.execute(
                select(Product).where(Product.id.in_(product_ids))
            )
            products = {p.id: p for p in products_result.scalars().all()}

            for oi in order_items:
                if oi.product_id in products:
                    products[oi.product_id].stock_quantity += oi.quantity
                    logger.info(
                        f"   ↩️  Restored {oi.quantity} units of product {oi.product_id} "
                        f"(order {order_id} cancelled)"
                    )

        # Update order status to CANCELLED instead of deleting
        old_status = order.status.value
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.utcnow()
        await db.commit()
        
        # Create notification if cancelled by admin
        if is_superuser and not is_owner:
            try:
                from app.services.notification_service import NotificationService
                from app.schemas.notification_schema import NotificationCreate
                
                # Build product description for notification
                product_description = "order"
                if order_items:
                    first_product = order_items[0].product_name or "product"
                    if len(order_items) == 1:
                        product_description = f"{first_product} order"
                    else:
                        additional_count = len(order_items) - 1
                        product_description = f"order containing {first_product} and {additional_count} more item{'s' if additional_count > 1 else ''}"
                
                notification = NotificationCreate(
                    user_id=order.user_id,
                    title="Order Cancelled by Admin",
                    message=f"Your {product_description} has been cancelled by an administrator. The amount will be refunded to your account.",
                    type="order_cancelled",
                    related_order_id=order_id
                )
                await NotificationService.create_notification(notification, db)
                logger.info(f"📬 Notification sent to user {order.user_id} about order {order_id} ({product_description}) cancellation")
            except Exception as e:
                logger.warning(f"⚠️  Failed to create notification: {e}")
        
        logger.info(f"✅ Order {order_id} cancelled successfully by {role} {user_id} (status: {old_status} → CANCELLED)")
        
        # Return the updated order
        return await OrderService.get_order(order_id, db)

    @staticmethod
    async def clear_all_orders(db: AsyncSession) -> None:
        """
        DEV ONLY: Delete all orders and order items.
        Use for testing/development cleanup.
        """
        await db.execute(OrderItem.__table__.delete())
        await db.execute(Order.__table__.delete())
        await db.commit()
