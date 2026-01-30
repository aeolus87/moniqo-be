"""
Notifications business logic.

Service layer for notification management operations.
"""

from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.modules.notifications.models import Notification
from app.modules.notifications.schemas import NotificationCreate
from app.shared.exceptions import ResourceNotFoundError
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def create_notification(
    db: AsyncIOMotorDatabase,
    user_id: str,
    notification_data: NotificationCreate
) -> dict:
    """
    Create a new notification for a user.
    
    Args:
        db: Database connection
        user_id: User ID
        notification_data: Notification creation data
        
    Returns:
        dict: Created notification
    """
    notification = await Notification.create_notification(
        db=db,
        user_id=user_id,
        notification_type=notification_data.type.value,
        title=notification_data.title,
        message=notification_data.message,
        metadata=notification_data.metadata
    )
    
    logger.info(f"Notification created successfully: {notification['_id']} for user {user_id}")
    return notification


async def get_notification_by_id(
    db: AsyncIOMotorDatabase,
    notification_id: str,
    user_id: str
) -> dict:
    """
    Get notification by ID.
    
    Args:
        db: Database connection
        notification_id: Notification ID
        user_id: User ID (for ownership verification)
        
    Returns:
        dict: Notification data
        
    Raises:
        ResourceNotFoundError: If notification not found or doesn't belong to user
    """
    notification = await Notification.get_notification_by_id(db, notification_id)
    if not notification:
        raise ResourceNotFoundError(f"Notification with ID '{notification_id}' not found")
    
    # Verify ownership
    if notification["user_id"] != user_id:
        raise ResourceNotFoundError(f"Notification with ID '{notification_id}' not found")
    
    return notification


async def list_user_notifications(
    db: AsyncIOMotorDatabase,
    user_id: str,
    limit: int = 10,
    offset: int = 0,
    is_read: Optional[bool] = None,
    notification_type: Optional[str] = None
) -> tuple[List[dict], int]:
    """
    List user's notifications with pagination and filters.
    
    Args:
        db: Database connection
        user_id: User ID
        limit: Number of items per page
        offset: Number of items to skip
        is_read: Filter by read status (optional)
        notification_type: Filter by type (optional)
        
    Returns:
        tuple: (list of notifications, total count)
    """
    notifications, total = await Notification.list_user_notifications(
        db,
        user_id,
        limit,
        offset,
        is_read,
        notification_type
    )
    
    logger.debug(f"Listed notifications: count={len(notifications)}, total={total} for user {user_id}")
    return notifications, total


async def mark_notification_as_read(
    db: AsyncIOMotorDatabase,
    notification_id: str,
    user_id: str
) -> dict:
    """
    Mark notification as read.
    
    Args:
        db: Database connection
        notification_id: Notification ID
        user_id: User ID (for ownership verification)
        
    Returns:
        dict: Updated notification
        
    Raises:
        ResourceNotFoundError: If notification not found or doesn't belong to user
    """
    # Verify ownership first
    notification = await Notification.get_notification_by_id(db, notification_id)
    if not notification:
        raise ResourceNotFoundError(f"Notification with ID '{notification_id}' not found")
    
    if notification["user_id"] != user_id:
        raise ResourceNotFoundError(f"Notification with ID '{notification_id}' not found")
    
    # Mark as read
    updated_notification = await Notification.mark_as_read(db, notification_id)
    if not updated_notification:
        raise ResourceNotFoundError(f"Notification with ID '{notification_id}' not found")
    
    logger.info(f"Notification marked as read successfully: {notification_id}")
    return updated_notification


async def mark_all_notifications_as_read(
    db: AsyncIOMotorDatabase,
    user_id: str
) -> dict:
    """
    Mark all user's unread notifications as read.
    
    Args:
        db: Database connection
        user_id: User ID
        
    Returns:
        dict: Result with count of marked notifications
    """
    marked_count = await Notification.mark_all_as_read(db, user_id)
    
    logger.info(f"Marked {marked_count} notifications as read for user {user_id}")
    return {
        "marked_count": marked_count,
        "message": f"Marked {marked_count} notifications as read"
    }


async def delete_notification(
    db: AsyncIOMotorDatabase,
    notification_id: str,
    user_id: str
) -> dict:
    """
    Soft delete notification.
    
    Args:
        db: Database connection
        notification_id: Notification ID
        user_id: User ID (for ownership verification)
        
    Returns:
        dict: Deletion confirmation
        
    Raises:
        ResourceNotFoundError: If notification not found or doesn't belong to user
    """
    # Verify ownership first
    notification = await Notification.get_notification_by_id(db, notification_id)
    if not notification:
        raise ResourceNotFoundError(f"Notification with ID '{notification_id}' not found")
    
    if notification["user_id"] != user_id:
        raise ResourceNotFoundError(f"Notification with ID '{notification_id}' not found")
    
    # Soft delete
    success = await Notification.delete_notification(db, notification_id)
    if not success:
        raise ResourceNotFoundError(f"Notification with ID '{notification_id}' not found")
    
    logger.info(f"Notification deleted successfully: {notification_id}")
    return {"message": "Notification deleted successfully", "notification_id": notification_id}


async def get_unread_count(
    db: AsyncIOMotorDatabase,
    user_id: str
) -> dict:
    """
    Get count of unread notifications for a user.
    
    Args:
        db: Database connection
        user_id: User ID
        
    Returns:
        dict: Unread count
    """
    count = await Notification.get_unread_count(db, user_id)
    
    logger.debug(f"Unread notification count for user {user_id}: {count}")
    return {"unread_count": count}

