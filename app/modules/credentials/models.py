"""
Credentials module models.

MongoDB models for credentials collection (user wallet credentials).
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def create_credentials(
    db: AsyncIOMotorDatabase,
    credentials_data: dict
) -> dict:
    """
    Create a new credentials record.
    
    Args:
        db: Database instance
        credentials_data: Credentials data dictionary
        
    Returns:
        dict: Created credentials record
        
    Raises:
        Exception: If creation fails
    """
    credentials_data["created_at"] = datetime.utcnow()
    credentials_data["updated_at"] = datetime.utcnow()
    credentials_data["is_active"] = True
    credentials_data.setdefault("is_connected", False)
    credentials_data.setdefault("connection_error", None)
    credentials_data.setdefault("last_verified_at", None)
    
    try:
        result = await db["credentials"].insert_one(credentials_data)
        credentials_data["_id"] = result.inserted_id
        logger.info(f"Credentials created: id={result.inserted_id}, user_id={credentials_data.get('user_id')}")
        return credentials_data
    except Exception as e:
        logger.error(f"Failed to create credentials: {str(e)}")
        raise


async def find_credentials_by_id(
    db: AsyncIOMotorDatabase,
    credentials_id: ObjectId,
    user_id: Optional[ObjectId] = None
) -> Optional[dict]:
    """
    Find credentials by ID.
    
    Args:
        db: Database instance
        credentials_id: Credentials ID
        user_id: Optional user ID to filter by ownership
        
    Returns:
        dict: Credentials record or None
    """
    query = {"_id": credentials_id, "is_active": True}
    if user_id:
        query["user_id"] = user_id
    
    try:
        credentials = await db["credentials"].find_one(query)
        return credentials
    except Exception as e:
        logger.error(f"Failed to find credentials by ID: {str(e)}")
        raise


async def list_user_credentials(
    db: AsyncIOMotorDatabase,
    user_id: ObjectId,
    wallet_id: Optional[ObjectId] = None,
    is_active: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0
) -> tuple[List[dict], int]:
    """
    List user credentials with optional filtering.
    
    Args:
        db: Database instance
        user_id: User ID
        wallet_id: Optional filter by wallet ID
        is_active: Optional filter by active status
        limit: Maximum number of results
        offset: Number of results to skip
        
    Returns:
        tuple: (List of credentials, total count)
    """
    query: Dict[str, Any] = {"user_id": user_id}
    
    if wallet_id:
        query["wallet_id"] = wallet_id
    
    if is_active is not None:
        query["is_active"] = is_active
    else:
        # Default to active only
        query["is_active"] = True
    
    try:
        # Get total count
        total = await db["credentials"].count_documents(query)
        
        # Get paginated results, sorted by created_at desc
        cursor = db["credentials"].find(query).sort("created_at", -1).skip(offset).limit(limit)
        credentials = await cursor.to_list(length=limit)
        
        return credentials, total
    except Exception as e:
        logger.error(f"Failed to list user credentials: {str(e)}")
        raise


async def update_credentials(
    db: AsyncIOMotorDatabase,
    credentials_id: ObjectId,
    user_id: ObjectId,
    update_data: dict
) -> Optional[dict]:
    """
    Update credentials.
    
    Args:
        db: Database instance
        credentials_id: Credentials ID
        user_id: User ID (for ownership check)
        update_data: Update data dictionary
        
    Returns:
        dict: Updated credentials record or None
    """
    update_data["updated_at"] = datetime.utcnow()
    
    try:
        result = await db["credentials"].find_one_and_update(
            {"_id": credentials_id, "user_id": user_id, "is_active": True},
            {"$set": update_data},
            return_document=True
        )
        
        if result:
            logger.info(f"Credentials updated: id={credentials_id}")
        else:
            logger.warning(f"Credentials not found for update: id={credentials_id}")
        
        return result
    except Exception as e:
        logger.error(f"Failed to update credentials: {str(e)}")
        raise


async def delete_credentials(
    db: AsyncIOMotorDatabase,
    credentials_id: ObjectId,
    user_id: ObjectId
) -> bool:
    """
    Soft delete credentials (set is_active=False).
    
    Args:
        db: Database instance
        credentials_id: Credentials ID
        user_id: User ID (for ownership check)
        
    Returns:
        bool: True if credentials were deleted, False otherwise
    """
    try:
        result = await db["credentials"].update_one(
            {"_id": credentials_id, "user_id": user_id, "is_active": True},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
        )
        
        if result.modified_count > 0:
            logger.info(f"Credentials soft deleted: id={credentials_id}")
            return True
        else:
            logger.warning(f"Credentials not found for deletion: id={credentials_id}")
            return False
    except Exception as e:
        logger.error(f"Failed to soft delete credentials: {str(e)}")
        raise
