"""
Users module models.

MongoDB models for users collection.
"""

from datetime import datetime
from typing import Optional, List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def create_user(
    db: AsyncIOMotorDatabase,
    user_data: dict
) -> dict:
    """
    Create a new user record.
    
    Args:
        db: Database instance
        user_data: User data dictionary
        
    Returns:
        dict: Created user record
        
    Raises:
        Exception: If creation fails
    """
    user_data["created_at"] = datetime.utcnow()
    user_data["updated_at"] = datetime.utcnow()
    user_data["is_deleted"] = False
    
    try:
        result = await db["users"].insert_one(user_data)
        user_data["_id"] = result.inserted_id
        logger.info(f"User created: id={result.inserted_id}")
        return user_data
    except Exception as e:
        logger.error(f"Failed to create user: {str(e)}")
        raise


async def find_user_by_id(
    db: AsyncIOMotorDatabase,
    user_id: ObjectId,
    include_deleted: bool = False
) -> Optional[dict]:
    """
    Find user by ID.
    
    Args:
        db: Database instance
        user_id: User ID
        include_deleted: Include soft-deleted records
        
    Returns:
        dict: User record or None if not found
    """
    query = {"_id": user_id}
    
    if not include_deleted:
        query["is_deleted"] = False
    
    try:
        user = await db["users"].find_one(query)
        return user
    except Exception as e:
        logger.error(f"Failed to find user by ID: {str(e)}")
        return None


async def find_user_by_auth_id(
    db: AsyncIOMotorDatabase,
    auth_id: ObjectId,
    include_deleted: bool = False
) -> Optional[dict]:
    """
    Find user by auth ID.
    
    Args:
        db: Database instance
        auth_id: Auth record ID
        include_deleted: Include soft-deleted records
        
    Returns:
        dict: User record or None if not found
    """
    query = {"auth_id": auth_id}
    
    if not include_deleted:
        query["is_deleted"] = False
    
    try:
        user = await db["users"].find_one(query)
        return user
    except Exception as e:
        logger.error(f"Failed to find user by auth_id: {str(e)}")
        return None


async def update_user(
    db: AsyncIOMotorDatabase,
    user_id: ObjectId,
    update_data: dict
) -> Optional[dict]:
    """
    Update user record.
    
    Args:
        db: Database instance
        user_id: User ID
        update_data: Fields to update
        
    Returns:
        dict: Updated user record or None if not found
    """
    # Add updated_at timestamp
    update_data["updated_at"] = datetime.utcnow()
    
    try:
        result = await db["users"].update_one(
            {"_id": user_id, "is_deleted": False},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            logger.info(f"User updated: id={user_id}")
            # Return updated user
            return await find_user_by_id(db, user_id)
        return None
    except Exception as e:
        logger.error(f"Failed to update user: {str(e)}")
        return None


async def soft_delete_user(
    db: AsyncIOMotorDatabase,
    user_id: ObjectId
) -> bool:
    """
    Soft delete user record.
    
    Args:
        db: Database instance
        user_id: User ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        result = await db["users"].update_one(
            {"_id": user_id, "is_deleted": False},
            {
                "$set": {
                    "is_deleted": True,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"User soft deleted: id={user_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to soft delete user: {str(e)}")
        return False


async def list_users(
    db: AsyncIOMotorDatabase,
    limit: int = 10,
    offset: int = 0,
    include_deleted: bool = False
) -> tuple[List[dict], int]:
    """
    List users with pagination.
    
    Args:
        db: Database instance
        limit: Number of users per page
        offset: Number of users to skip
        include_deleted: Include soft-deleted records
        
    Returns:
        tuple: (list of users, total count)
    """
    query = {}
    
    if not include_deleted:
        query["is_deleted"] = False
    
    try:
        # Get total count
        total = await db["users"].count_documents(query)
        
        # Get paginated results
        cursor = db["users"].find(query).sort("created_at", -1).skip(offset).limit(limit)
        users = await cursor.to_list(length=limit)
        
        return users, total
    except Exception as e:
        logger.error(f"Failed to list users: {str(e)}")
        return [], 0


def generate_default_avatar_url(first_name: str) -> str:
    """
    Generate default avatar URL from first name initial.
    
    Args:
        first_name: User's first name
        
    Returns:
        str: Avatar URL
        
    Example:
        >>> generate_default_avatar_url("John")
        "https://ui-avatars.com/api/?name=J&size=200&background=random"
    """
    initial = first_name[0].upper() if first_name else "U"
    return f"https://ui-avatars.com/api/?name={initial}&size=200&background=random"

