"""
Notification service
"""
import logging
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.schemas.notification_schema import NotificationCreate, NotificationResponse

logger = logging.getLogger(__name__)


class NotificationService:
    
    @staticmethod
    async def create_notification(
        notification_data: NotificationCreate,
        db: AsyncSession
    ) -> Notification:
        """Create a new notification."""
        notification = Notification(
            user_id=notification_data.user_id,
            title=notification_data.title,
            message=notification_data.message,
            type=notification_data.type,
            related_order_id=notification_data.related_order_id,
            related_product_id=notification_data.related_product_id,
        )
        
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        
        logger.info(f"📬 Created notification for user {notification_data.user_id}: {notification_data.title}")
        return notification
    
    @staticmethod
    async def get_user_notifications(
        user_id: int,
        db: AsyncSession,
        unread_only: bool = False
    ) -> List[Notification]:
        """
        Get all notifications for a specific user.
        
        IMPORTANT: Only returns notifications where notification.user_id == user_id.
        This ensures users only see their own notifications.
        Admins only see notifications for orders they placed as customers.
        """
        query = select(Notification).where(Notification.user_id == user_id)
        
        if unread_only:
            query = query.where(Notification.is_read == False)
        
        query = query.order_by(Notification.created_at.desc())
        
        result = await db.execute(query)
        notifications = list(result.scalars().all())
        
        logger.debug(f"📬 Fetched {len(notifications)} notifications for user_id={user_id} (unread_only={unread_only})")
        return notifications
    
    @staticmethod
    async def mark_as_read(
        notification_id: int,
        user_id: int,
        db: AsyncSession
    ) -> Notification:
        """Mark a notification as read."""
        result = await db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id
            )
        )
        notification = result.scalar_one_or_none()
        
        if notification:
            notification.is_read = True
            await db.commit()
            await db.refresh(notification)
            logger.info(f"✅ Notification {notification_id} marked as read")
        
        return notification
    
    @staticmethod
    async def mark_all_as_read(
        user_id: int,
        db: AsyncSession
    ) -> int:
        """Mark all notifications as read for a user."""
        result = await db.execute(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.is_read == False
            )
        )
        notifications = list(result.scalars().all())
        
        count = 0
        for notification in notifications:
            notification.is_read = True
            count += 1
        
        await db.commit()
        logger.info(f"✅ Marked {count} notifications as read for user {user_id}")
        return count
    
    @staticmethod
    async def notify_product_unavailable(
        product_id: int,
        product_name: str,
        user_ids: List[int],
        db: AsyncSession
    ) -> int:
        """Notify users that a product they ordered is no longer available."""
        count = 0
        for user_id in user_ids:
            notification = NotificationCreate(
                user_id=user_id,
                title="Product No Longer Available",
                message=f"The product '{product_name}' from your order is no longer available. It has been removed by the administrator.",
                type="product_unavailable",
                related_product_id=product_id
            )
            await NotificationService.create_notification(notification, db)
            count += 1
        
        logger.info(f"📬 Notified {count} users about unavailable product: {product_name}")
        return count
    
    @staticmethod
    async def notify_order_status_change(
        user_id: int,
        order_id: int,
        new_status: str,
        db: AsyncSession
    ) -> Notification:
        """
        Notify user about order status change with product names.
        
        IMPORTANT: Only the order owner (user_id) receives the notification.
        Admins who update the status do NOT receive notifications.
        
        Messages include product names for better UX:
        - Single item: "Your Mobile order has been shipped."
        - Multiple items: "Your order containing Mobile and 2 more items has been shipped."
        """
        from app.models.order_item import OrderItem
        
        # Fetch order items to get product names
        order_items_result = await db.execute(
            select(OrderItem).where(OrderItem.order_id == order_id)
        )
        order_items = list(order_items_result.scalars().all())
        
        # Build product description
        product_description = "order"
        if order_items:
            # Get first product name
            first_product = order_items[0].product_name or "product"
            
            if len(order_items) == 1:
                # Single product: "Your Mobile order"
                product_description = f"{first_product} order"
            else:
                # Multiple products: "Your order containing Mobile and 2 more items"
                additional_count = len(order_items) - 1
                product_description = f"order containing {first_product} and {additional_count} more item{'s' if additional_count > 1 else ''}"
        
        # Generate status-specific messages with product names
        status_templates = {
            "CONFIRMED": {
                "title": "Order Confirmed",
                "message": f"Your {product_description} has been confirmed and is being processed."
            },
            "PROCESSING": {
                "title": "Order Processing",
                "message": f"Your {product_description} is being processed and will be shipped soon."
            },
            "SHIPPED": {
                "title": "Order Shipped",
                "message": f"Your {product_description} has been shipped and is on the way!"
            },
            "DELIVERED": {
                "title": "Order Delivered",
                "message": f"Your {product_description} was delivered successfully. Thank you for shopping with us!"
            },
            "CANCELLED": {
                "title": "Order Cancelled",
                "message": f"Your {product_description} was cancelled by admin. The amount will be refunded to your account."
            }
        }
        
        # Get status-specific title and message
        status_info = status_templates.get(new_status, {
            "title": f"Order {new_status.title()}",
            "message": f"Your {product_description} status has been updated to {new_status}."
        })
        
        notification = NotificationCreate(
            user_id=user_id,  # Only order owner receives notification
            title=status_info["title"],
            message=status_info["message"],
            type="order_status_update",
            related_order_id=order_id
        )
        
        logger.info(f"📬 Creating notification for ORDER OWNER (user_id={user_id}) about order #{order_id} ({product_description}) status: {new_status}")
        return await NotificationService.create_notification(notification, db)
