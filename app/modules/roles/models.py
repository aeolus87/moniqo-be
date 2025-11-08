"""
Roles module models.

Database models for roles collection.
"""

from datetime import datetime
from typing import Optional, List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def create_role(
    db: AsyncIOMotorDatabase,
    name: str,
    description: str,
    permissions: List[str]
) -> dict:
    """
    Create a new role in the database.
    
    Args:
        db: Database instance
        name: Role name (e.g., "Admin", "User")
        description: Role description
        permissions: List of permission IDs
        
    Returns:
        Created role document
        
    Raises:
        Exception: If creation fails
    """
    try:
        # Convert permission IDs to ObjectId
        permission_ids = [ObjectId(perm_id) for perm_id in permissions]
        
        role_doc = {
            "name": name,
            "description": description,
            "permissions": permission_ids,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_deleted": False
        }
        
        result = await db.roles.insert_one(role_doc)
        role_doc["_id"] = str(result.inserted_id)
        # Convert ObjectIds back to strings for response
        role_doc["permissions"] = permissions
        
        logger.info(f"Role created: name={name}, id={result.inserted_id}")
        return role_doc
        
    except Exception as e:
        logger.error(f"Failed to create role: {str(e)}")
        raise


async def find_role_by_name(
    db: AsyncIOMotorDatabase,
    name: str
) -> Optional[dict]:
    """
    Find role by name.
    
    Args:
        db: Database instance
        name: Role name
        
    Returns:
        Role document or None if not found
    """
    try:
        role = await db.roles.find_one({
            "name": name,
            "is_deleted": False
        })
        
        if role:
            role["_id"] = str(role["_id"])
            # Convert permission ObjectIds to strings
            role["permissions"] = [str(perm_id) for perm_id in role.get("permissions", [])]
        
        return role
        
    except Exception as e:
        logger.error(f"Failed to find role by name: {str(e)}")
        return None


async def find_role_by_id(
    db: AsyncIOMotorDatabase,
    role_id: str
) -> Optional[dict]:
    """
    Find role by ID.
    
    Args:
        db: Database instance
        role_id: Role ID
        
    Returns:
        Role document or None if not found
    """
    try:
        role = await db.roles.find_one({
            "_id": ObjectId(role_id),
            "is_deleted": False
        })
        
        if role:
            role["_id"] = str(role["_id"])
            # Convert permission ObjectIds to strings
            role["permissions"] = [str(perm_id) for perm_id in role.get("permissions", [])]
        
        return role
        
    except Exception as e:
        logger.error(f"Failed to find role by ID: {str(e)}")
        return None


async def find_roles(
    db: AsyncIOMotorDatabase,
    limit: int = 10,
    offset: int = 0
) -> tuple[list[dict], int]:
    """
    Find all roles (paginated).
    
    Args:
        db: Database instance
        limit: Number of roles per page
        offset: Number of roles to skip
        
    Returns:
        Tuple of (list of roles, total count)
    """
    try:
        query = {"is_deleted": False}
        
        cursor = db.roles.find(query).sort("created_at", -1).skip(offset).limit(limit)
        roles = await cursor.to_list(length=limit)
        
        # Convert ObjectIds to strings
        for role in roles:
            role["_id"] = str(role["_id"])
            role["permissions"] = [str(perm_id) for perm_id in role.get("permissions", [])]
        
        total = await db.roles.count_documents(query)
        
        return roles, total
        
    except Exception as e:
        logger.error(f"Failed to find roles: {str(e)}")
        return [], 0


async def update_role(
    db: AsyncIOMotorDatabase,
    role_id: str,
    update_data: dict
) -> Optional[dict]:
    """
    Update role by ID.
    
    Args:
        db: Database instance
        role_id: Role ID
        update_data: Data to update
        
    Returns:
        Updated role document or None if not found
    """
    try:
        # Convert permission IDs to ObjectId if present
        if "permissions" in update_data:
            update_data["permissions"] = [ObjectId(perm_id) for perm_id in update_data["permissions"]]
        
        update_data["updated_at"] = datetime.utcnow()
        
        result = await db.roles.find_one_and_update(
            {"_id": ObjectId(role_id), "is_deleted": False},
            {"$set": update_data},
            return_document=True
        )
        
        if result:
            result["_id"] = str(result["_id"])
            # Convert permission ObjectIds to strings
            result["permissions"] = [str(perm_id) for perm_id in result.get("permissions", [])]
            logger.info(f"Role updated: id={role_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to update role: {str(e)}")
        return None


async def soft_delete_role(
    db: AsyncIOMotorDatabase,
    role_id: str
) -> bool:
    """
    Soft delete role by ID.
    
    Args:
        db: Database instance
        role_id: Role ID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        result = await db.roles.update_one(
            {"_id": ObjectId(role_id), "is_deleted": False},
            {
                "$set": {
                    "is_deleted": True,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"Role soft deleted: id={role_id}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Failed to soft delete role: {str(e)}")
        return False

