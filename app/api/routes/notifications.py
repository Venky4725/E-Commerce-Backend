"""
Notification routes
"""
import logging
import traceback
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.notification_schema import NotificationResponse
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=list[NotificationResponse])
async def get_my_notifications(
    unread_only: bool = Query(False, description="Get only unread notifications"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all notifications for the current user.
    Set unread_only=true to get only unread notifications.
    """
    try:
        logger.info(f"📬 User {current_user.username} fetching notifications (unread_only={unread_only})")
        notifications = await NotificationService.get_user_notifications(
            current_user.id, db, unread_only
        )
        logger.info(f"   Found {len(notifications)} notifications")
        return notifications
    except Exception as e:
        logger.error(f"❌ Error fetching notifications for user {current_user.id}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch notifications: {str(e)}"
        )


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a notification as read."""
    try:
        notification = await NotificationService.mark_as_read(
            notification_id, current_user.id, db
        )
        
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        return notification
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error marking notification {notification_id} as read: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to mark notification as read: {str(e)}"
        )


@router.patch("/read-all", status_code=200)
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read for the current user."""
    try:
        count = await NotificationService.mark_all_as_read(current_user.id, db)
        return {"message": f"Marked {count} notifications as read", "count": count}
    except Exception as e:
        logger.error(f"❌ Error marking all notifications as read for user {current_user.id}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to mark all notifications as read: {str(e)}"
        )


@router.get("/unread-count", status_code=200)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get count of unread notifications for the current user."""
    try:
        notifications = await NotificationService.get_user_notifications(
            current_user.id, db, unread_only=True
        )
        count = len(notifications)
        logger.debug(f"📬 User {current_user.username} has {count} unread notifications")
        return {"count": count}
    except Exception as e:
        logger.error(f"❌ Error getting unread count for user {current_user.id}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get unread count: {str(e)}"
        )
