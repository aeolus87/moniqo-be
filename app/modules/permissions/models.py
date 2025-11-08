"""
Permissions module models.

Database models for permissions collection.
"""

from datetime import datetime
from typing import Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def create_permission(
    db: AsyncIOMotorDatabase,
    resource: str,
    action: str,
    description: str
) -> dict:
    """
    Create a new permission in the database.
    
    Args:
        db: Database instance
        resource: Resource name (e.g., "users", "plans")
        action: Action name (e.g., "read", "write", "delete")
        description: Permission description
        
    Returns:
        Created permission document
        
    Raises:
        Exception: If creation fails
    """
    try:
        permission_doc = {
            "resource": resource,
            "action": action,
            "description": description,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_deleted": False
        }
        
        result = await db.permissions.insert_one(permission_doc)
        permission_doc["_id"] = str(result.inserted_id)
        
        logger.info(f"Permission created: resource={resource}, action={action}, id={result.inserted_id}")
        return permission_doc
        
    except Exception as e:
        logger.error(f"Failed to create permission: {str(e)}")
        raise


async def find_permission_by_resource_action(
    db: AsyncIOMotorDatabase,
    resource: str,
    action: str
) -> Optional[dict]:
    """
    Find permission by resource and action.
    
    Args:
        db: Database instance
        resource: Resource name
        action: Action name
        
    Returns:
        Permission document or None if not found
    """
    try:
        permission = await db.permissions.find_one({
            "resource": resource,
            "action": action,
            "is_deleted": False
        })
        
        if permission:
            permission["_id"] = str(permission["_id"])
        
        return permission
        
    except Exception as e:
        logger.error(f"Failed to find permission by resource/action: {str(e)}")
        return None


async def find_permission_by_id(
    db: AsyncIOMotorDatabase,
    permission_id: str
) -> Optional[dict]:
    """
    Find permission by ID.
    
    Args:
        db: Database instance
        permission_id: Permission ID
        
    Returns:
        Permission document or None if not found
    """
    try:
        permission = await db.permissions.find_one({
            "_id": ObjectId(permission_id),
            "is_deleted": False
        })
        
        if permission:
            permission["_id"] = str(permission["_id"])
        
        return permission
        
    except Exception as e:
        logger.error(f"Failed to find permission by ID: {str(e)}")
        return None


async def find_permissions(
    db: AsyncIOMotorDatabase,
    limit: int = 10,
    offset: int = 0
) -> tuple[list[dict], int]:
    """
    Find all permissions (paginated).
    
    Args:
        db: Database instance
        limit: Number of permissions per page
        offset: Number of permissions to skip
        
    Returns:
        Tuple of (list of permissions, total count)
    """
    try:
        query = {"is_deleted": False}
        
        cursor = db.permissions.find(query).sort("created_at", -1).skip(offset).limit(limit)
        permissions = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string
        for permission in permissions:
            permission["_id"] = str(permission["_id"])
        
        total = await db.permissions.count_documents(query)
        
        return permissions, total
        
    except Exception as e:
        logger.error(f"Failed to find permissions: {str(e)}")
        return [], 0


async def update_permission(
    db: AsyncIOMotorDatabase,
    permission_id: str,
    update_data: dict
) -> Optional[dict]:
    """
    Update permission by ID.
    
    Args:
        db: Database instance
        permission_id: Permission ID
        update_data: Data to update
        
    Returns:
        Updated permission document or None if not found
    """
    try:
        update_data["updated_at"] = datetime.utcnow()
        
        result = await db.permissions.find_one_and_update(
            {"_id": ObjectId(permission_id), "is_deleted": False},
            {"$set": update_data},
            return_document=True
        )
        
        if result:
            result["_id"] = str(result["_id"])
            logger.info(f"Permission updated: id={permission_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to update permission: {str(e)}")
        return None


async def soft_delete_permission(
    db: AsyncIOMotorDatabase,
    permission_id: str
) -> bool:
    """
    Soft delete permission by ID.
    
    Args:
        db: Database instance
        permission_id: Permission ID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        result = await db.permissions.update_one(
            {"_id": ObjectId(permission_id), "is_deleted": False},
            {
                "$set": {
                    "is_deleted": True,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"Permission soft deleted: id={permission_id}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Failed to soft delete permission: {str(e)}")
        return False

