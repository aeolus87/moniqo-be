"""
Notifications MongoDB model.

Handles database operations for user notifications.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Notification:
    """Notification model for database operations."""
    
    @staticmethod
    async def create_notification(
        db: AsyncIOMotorDatabase,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> dict:
        """
        Create a new notification.
        
        Args:
            db: Database connection
            user_id: User ID
            notification_type: Notification type (info, success, warning, error)
            title: Notification title
            message: Notification message
            metadata: Additional metadata (optional)
            
        Returns:
            dict: Created notification document
        """
        notification_doc = {
            "user_id": ObjectId(user_id),
            "type": notification_type,
            "title": title,
            "message": message,
            "metadata": metadata,
            "is_read": False,
            "read_at": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_deleted": False
        }
        
        result = await db.notifications.insert_one(notification_doc)
        notification_doc["_id"] = str(result.inserted_id)
        notification_doc["user_id"] = str(notification_doc["user_id"])
        
        logger.info(f"Notification created: notification_id={notification_doc['_id']}, user_id={user_id}, type={notification_type}")
        return notification_doc
    
    @staticmethod
    async def get_notification_by_id(
        db: AsyncIOMotorDatabase,
        notification_id: str
    ) -> dict | None:
        """
        Get notification by ID.
        
        Args:
            db: Database connection
            notification_id: Notification ID
            
        Returns:
            dict | None: Notification document or None if not found
        """
        try:
            notification = await db.notifications.find_one({
                "_id": ObjectId(notification_id),
                "is_deleted": False
            })
            
            if notification:
                notification["_id"] = str(notification["_id"])
                notification["user_id"] = str(notification["user_id"])
            
            return notification
        except Exception as e:
            logger.error(f"Error getting notification by ID: {str(e)}")
            return None
    
    @staticmethod
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
        # Build query
        query = {
            "user_id": ObjectId(user_id),
            "is_deleted": False
        }
        
        if is_read is not None:
            query["is_read"] = is_read
        
        if notification_type:
            query["type"] = notification_type
        
        # Get notifications
        cursor = db.notifications.find(query).sort("created_at", -1)
        
        total = await db.notifications.count_documents(query)
        
        notifications = await cursor.skip(offset).limit(limit).to_list(length=limit)
        
        # Convert ObjectId to string
        for notification in notifications:
            notification["_id"] = str(notification["_id"])
            notification["user_id"] = str(notification["user_id"])
        
        return notifications, total
    
    @staticmethod
    async def mark_as_read(
        db: AsyncIOMotorDatabase,
        notification_id: str
    ) -> dict | None:
        """
        Mark notification as read.
        
        Args:
            db: Database connection
            notification_id: Notification ID
            
        Returns:
            dict | None: Updated notification or None if not found
        """
        try:
            result = await db.notifications.find_one_and_update(
                {"_id": ObjectId(notification_id), "is_deleted": False},
                {"$set": {
                    "is_read": True,
                    "read_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }},
                return_document=True
            )
            
            if result:
                result["_id"] = str(result["_id"])
                result["user_id"] = str(result["user_id"])
                logger.info(f"Notification marked as read: notification_id={notification_id}")
            
            return result
        except Exception as e:
            logger.error(f"Error marking notification as read: {str(e)}")
            return None
    
    @staticmethod
    async def mark_all_as_read(
        db: AsyncIOMotorDatabase,
        user_id: str
    ) -> int:
        """
        Mark all user's unread notifications as read.
        
        Args:
            db: Database connection
            user_id: User ID
            
        Returns:
            int: Number of notifications marked as read
        """
        try:
            result = await db.notifications.update_many(
                {
                    "user_id": ObjectId(user_id),
                    "is_read": False,
                    "is_deleted": False
                },
                {"$set": {
                    "is_read": True,
                    "read_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }}
            )
            
            logger.info(f"Marked {result.modified_count} notifications as read for user: {user_id}")
            return result.modified_count
        except Exception as e:
            logger.error(f"Error marking all notifications as read: {str(e)}")
            return 0
    
    @staticmethod
    async def delete_notification(
        db: AsyncIOMotorDatabase,
        notification_id: str
    ) -> bool:
        """
        Soft delete notification.
        
        Args:
            db: Database connection
            notification_id: Notification ID
            
        Returns:
            bool: True if deleted, False otherwise
        """
        try:
            result = await db.notifications.update_one(
                {"_id": ObjectId(notification_id), "is_deleted": False},
                {"$set": {
                    "is_deleted": True,
                    "updated_at": datetime.utcnow()
                }}
            )
            
            if result.modified_count > 0:
                logger.info(f"Notification soft deleted: notification_id={notification_id}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error deleting notification: {str(e)}")
            return False
    
    @staticmethod
    async def get_unread_count(
        db: AsyncIOMotorDatabase,
        user_id: str
    ) -> int:
        """
        Get count of unread notifications for a user.
        
        Args:
            db: Database connection
            user_id: User ID
            
        Returns:
            int: Count of unread notifications
        """
        try:
            count = await db.notifications.count_documents({
                "user_id": ObjectId(user_id),
                "is_read": False,
                "is_deleted": False
            })
            
            return count
        except Exception as e:
            logger.error(f"Error getting unread count: {str(e)}")
            return 0

