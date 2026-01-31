"""
Auth module models.

MongoDB models for authentication collection.
"""

from datetime import datetime
from typing import Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import OperationFailure
from app.utils.logger import get_logger
from app.shared.exceptions import DatabaseAuthorizationError

logger = get_logger(__name__)


async def create_auth(
    db: AsyncIOMotorDatabase,
    email: str,
    password_hash: str,
    is_verified: bool = False
) -> dict:
    """
    Create a new auth record.
    
    Args:
        db: Database instance
        email: User email (lowercase)
        password_hash: Hashed password
        is_verified: Email verification status
        
    Returns:
        dict: Created auth record
        
    Raises:
        Exception: If creation fails
    """
    auth_data = {
        "email": email.lower(),
        "password_hash": password_hash,
        "is_verified": is_verified,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "is_deleted": False
    }
    
    try:
        result = await db["auth"].insert_one(auth_data)
        auth_data["_id"] = result.inserted_id
        logger.info(f"Auth record created: email={email}, id={result.inserted_id}")
        return auth_data
    except OperationFailure as e:
        # Check for MongoDB authorization errors (code 13)
        if e.code == 13 or "not authorized" in str(e).lower() or "unauthorized" in str(e).lower():
            logger.error(f"MongoDB authorization error: {str(e)}")
            raise DatabaseAuthorizationError(
                f"MongoDB authorization failed: {str(e)}. "
                "Please ensure the MongoDB user has read/write permissions on the database."
            )
        logger.error(f"Failed to create auth record: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Failed to create auth record: {str(e)}")
        raise


async def find_auth_by_email(
    db: AsyncIOMotorDatabase,
    email: str,
    include_deleted: bool = False
) -> Optional[dict]:
    """
    Find auth record by email.
    
    Args:
        db: Database instance
        email: User email
        include_deleted: Include soft-deleted records
        
    Returns:
        dict: Auth record or None if not found
    """
    query = {"email": email.lower()}
    
    if not include_deleted:
        query["is_deleted"] = False
    
    try:
        auth = await db["auth"].find_one(query)
        return auth
    except Exception as e:
        logger.error(f"Failed to find auth by email: {str(e)}")
        return None


async def find_auth_by_id(
    db: AsyncIOMotorDatabase,
    auth_id: ObjectId,
    include_deleted: bool = False
) -> Optional[dict]:
    """
    Find auth record by ID.
    
    Args:
        db: Database instance
        auth_id: Auth record ID
        include_deleted: Include soft-deleted records
        
    Returns:
        dict: Auth record or None if not found
    """
    query = {"_id": auth_id}
    
    if not include_deleted:
        query["is_deleted"] = False
    
    try:
        auth = await db["auth"].find_one(query)
        return auth
    except Exception as e:
        logger.error(f"Failed to find auth by ID: {str(e)}")
        return None


async def update_auth(
    db: AsyncIOMotorDatabase,
    auth_id: ObjectId,
    update_data: dict
) -> bool:
    """
    Update auth record.
    
    Args:
        db: Database instance
        auth_id: Auth record ID
        update_data: Fields to update
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Add updated_at timestamp
    update_data["updated_at"] = datetime.utcnow()
    
    try:
        result = await db["auth"].update_one(
            {"_id": auth_id, "is_deleted": False},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            logger.info(f"Auth record updated: id={auth_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to update auth: {str(e)}")
        return False


async def verify_email(
    db: AsyncIOMotorDatabase,
    email: str
) -> bool:
    """
    Mark email as verified.
    
    Args:
        db: Database instance
        email: User email
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        result = await db["auth"].update_one(
            {"email": email.lower(), "is_deleted": False},
            {
                "$set": {
                    "is_verified": True,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"Email verified: email={email}")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to verify email: {str(e)}")
        return False


async def update_password(
    db: AsyncIOMotorDatabase,
    email: str,
    new_password_hash: str
) -> bool:
    """
    Update user password.
    
    Args:
        db: Database instance
        email: User email
        new_password_hash: New hashed password
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        result = await db["auth"].update_one(
            {"email": email.lower(), "is_deleted": False},
            {
                "$set": {
                    "password_hash": new_password_hash,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"Password updated: email={email}")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to update password: {str(e)}")
        return False


async def deactivate_account(
    db: AsyncIOMotorDatabase,
    auth_id: ObjectId
) -> bool:
    """
    Deactivate user account.
    
    Args:
        db: Database instance
        auth_id: Auth record ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        result = await db["auth"].update_one(
            {"_id": auth_id, "is_deleted": False},
            {
                "$set": {
                    "is_active": False,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"Account deactivated: id={auth_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to deactivate account: {str(e)}")
        return False


async def soft_delete_auth(
    db: AsyncIOMotorDatabase,
    auth_id: ObjectId
) -> bool:
    """
    Soft delete auth record.
    
    Args:
        db: Database instance
        auth_id: Auth record ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        result = await db["auth"].update_one(
            {"_id": auth_id, "is_deleted": False},
            {
                "$set": {
                    "is_deleted": True,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"Auth record soft deleted: id={auth_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to soft delete auth: {str(e)}")
        return False

