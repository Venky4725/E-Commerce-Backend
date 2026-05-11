"""
Admin routes - Dashboard statistics and analytics
"""
import logging
import traceback
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_admin_user
from app.models.user import User
from app.schemas.admin_schema import AdminDashboardStats, RevenueByPeriod
from app.services.admin_service import AdminService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stats", response_model=AdminDashboardStats)
async def get_dashboard_stats(
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
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
    
    Requires admin authentication.
    """
    try:
        logger.info(f"🔧 Admin {current_admin.username} fetching dashboard statistics")
        stats = await AdminService.get_dashboard_stats(db)
        return stats
    except Exception as e:
        logger.error(f"❌ Error fetching dashboard stats: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch dashboard statistics: {str(e)}"
        )


@router.get("/revenue", response_model=RevenueByPeriod)
async def get_revenue_stats(
    period: str = Query("all", description="Period: today, week, month, year, or all"),
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get revenue statistics by period.
    
    Currently returns all-time revenue.
    Can be extended to filter by date ranges.
    
    Requires admin authentication.
    """
    try:
        logger.info(f"🔧 Admin {current_admin.username} fetching revenue stats (period: {period})")
        stats = await AdminService.get_revenue_by_period(db, period)
        return stats
    except Exception as e:
        logger.error(f"❌ Error fetching revenue stats: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch revenue statistics: {str(e)}"
        )
