"""
Admin service - Dashboard statistics and analytics
"""
import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.product import Product
from app.models.order import Order, OrderStatus

logger = logging.getLogger(__name__)


class AdminService:
    
    @staticmethod
    async def get_dashboard_stats(db: AsyncSession) -> dict:
        """
        Get admin dashboard statistics.
        
        Returns:
            - total_revenue: Sum of all DELIVERED orders
            - total_users: Count of all users
            - total_products: Count of all active products
            - total_orders: Count of all orders
            - delivered_orders: Count of DELIVERED orders
            - pending_orders: Count of PENDING orders
            - confirmed_orders: Count of CONFIRMED orders
            - processing_orders: Count of PROCESSING orders
            - shipped_orders: Count of SHIPPED orders
            - cancelled_orders: Count of CANCELLED orders
        """
        logger.info("📊 Calculating admin dashboard statistics...")
        
        # Calculate total revenue (sum of DELIVERED orders only)
        revenue_result = await db.execute(
            select(func.sum(Order.total_amount))
            .where(Order.status == OrderStatus.DELIVERED)
        )
        total_revenue = revenue_result.scalar() or 0.0
        logger.info(f"   💰 Total revenue (DELIVERED orders): ${total_revenue:.2f}")
        
        # Count total users
        users_result = await db.execute(
            select(func.count(User.id))
        )
        total_users = users_result.scalar() or 0
        logger.info(f"   👥 Total users: {total_users}")
        
        # Count total products (active only)
        products_result = await db.execute(
            select(func.count(Product.id))
            .where(Product.is_active == True)
        )
        total_products = products_result.scalar() or 0
        logger.info(f"   📦 Total active products: {total_products}")
        
        # Count total orders
        total_orders_result = await db.execute(
            select(func.count(Order.id))
        )
        total_orders = total_orders_result.scalar() or 0
        logger.info(f"   📋 Total orders: {total_orders}")
        
        # Count orders by status
        delivered_result = await db.execute(
            select(func.count(Order.id))
            .where(Order.status == OrderStatus.DELIVERED)
        )
        delivered_orders = delivered_result.scalar() or 0
        
        pending_result = await db.execute(
            select(func.count(Order.id))
            .where(Order.status == OrderStatus.PENDING)
        )
        pending_orders = pending_result.scalar() or 0
        
        confirmed_result = await db.execute(
            select(func.count(Order.id))
            .where(Order.status == OrderStatus.CONFIRMED)
        )
        confirmed_orders = confirmed_result.scalar() or 0
        
        processing_result = await db.execute(
            select(func.count(Order.id))
            .where(Order.status == OrderStatus.PROCESSING)
        )
        processing_orders = processing_result.scalar() or 0
        
        shipped_result = await db.execute(
            select(func.count(Order.id))
            .where(Order.status == OrderStatus.SHIPPED)
        )
        shipped_orders = shipped_result.scalar() or 0
        
        cancelled_result = await db.execute(
            select(func.count(Order.id))
            .where(Order.status == OrderStatus.CANCELLED)
        )
        cancelled_orders = cancelled_result.scalar() or 0
        
        logger.info(f"   📊 Orders by status:")
        logger.info(f"      - DELIVERED: {delivered_orders}")
        logger.info(f"      - PENDING: {pending_orders}")
        logger.info(f"      - CONFIRMED: {confirmed_orders}")
        logger.info(f"      - PROCESSING: {processing_orders}")
        logger.info(f"      - SHIPPED: {shipped_orders}")
        logger.info(f"      - CANCELLED: {cancelled_orders}")
        
        stats = {
            "total_revenue": round(total_revenue, 2),
            "total_users": total_users,
            "total_products": total_products,
            "total_orders": total_orders,
            "delivered_orders": delivered_orders,
            "pending_orders": pending_orders,
            "confirmed_orders": confirmed_orders,
            "processing_orders": processing_orders,
            "shipped_orders": shipped_orders,
            "cancelled_orders": cancelled_orders,
        }
        
        logger.info("✅ Dashboard statistics calculated successfully")
        return stats
    
    @staticmethod
    async def get_revenue_by_period(db: AsyncSession, period: str = "all") -> dict:
        """
        Get revenue statistics by time period.
        
        Args:
            period: "today", "week", "month", "year", or "all"
        
        Returns:
            Revenue statistics for the specified period
        """
        # This can be extended to filter by date ranges
        # For now, returns all-time revenue
        stats = await AdminService.get_dashboard_stats(db)
        return {
            "period": period,
            "revenue": stats["total_revenue"],
            "delivered_orders": stats["delivered_orders"]
        }
