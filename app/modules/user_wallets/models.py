"""
User wallets module models.

MongoDB models for user_wallets collection (user wallet instances).
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def create_user_wallet(
    db: AsyncIOMotorDatabase,
    wallet_data: dict
) -> dict:
    """
    Create a new user wallet instance.
    
    Args:
        db: Database instance
        wallet_data: Wallet data dictionary
        
    Returns:
        dict: Created wallet record
        
    Raises:
        Exception: If creation fails
    """
    wallet_data["created_at"] = datetime.utcnow()
    wallet_data["updated_at"] = datetime.utcnow()
    
    try:
        result = await db["user_wallets"].insert_one(wallet_data)
        wallet_data["_id"] = result.inserted_id
        logger.info(f"User wallet created: id={result.inserted_id}, user_id={wallet_data.get('user_id')}")
        return wallet_data
    except Exception as e:
        logger.error(f"Failed to create user wallet: {str(e)}")
        raise


async def find_user_wallet_by_id(
    db: AsyncIOMotorDatabase,
    wallet_id: ObjectId,
    user_id: Optional[ObjectId] = None
) -> Optional[dict]:
    """
    Find user wallet by ID.
    
    Args:
        db: Database instance
        wallet_id: Wallet instance ID
        user_id: Optional user ID to filter by ownership
        
    Returns:
        dict: Wallet record or None
    """
    query = {"_id": wallet_id}
    if user_id:
        query["user_id"] = user_id
    
    try:
        wallet = await db["user_wallets"].find_one(query)
        return wallet
    except Exception as e:
        logger.error(f"Failed to find user wallet by ID: {str(e)}")
        raise


async def list_user_wallets(
    db: AsyncIOMotorDatabase,
    user_id: ObjectId,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> tuple[List[dict], int]:
    """
    List user wallets with optional filtering.
    
    Args:
        db: Database instance
        user_id: User ID
        status: Optional filter by status
        limit: Maximum number of results
        offset: Number of results to skip
        
    Returns:
        tuple: (List of wallets, total count)
    """
    query: Dict[str, Any] = {"user_id": user_id}
    
    if status:
        query["status"] = status
    
    try:
        # Get total count
        total = await db["user_wallets"].count_documents(query)
        
        # Get paginated results, sorted by created_at desc
        cursor = db["user_wallets"].find(query).sort("created_at", -1).skip(offset).limit(limit)
        wallets = await cursor.to_list(length=limit)
        
        return wallets, total
    except Exception as e:
        logger.error(f"Failed to list user wallets: {str(e)}")
        raise


async def update_user_wallet(
    db: AsyncIOMotorDatabase,
    wallet_id: ObjectId,
    user_id: ObjectId,
    update_data: dict
) -> Optional[dict]:
    """
    Update user wallet.
    
    Args:
        db: Database instance
        wallet_id: Wallet instance ID
        user_id: User ID (for ownership check)
        update_data: Update data dictionary
        
    Returns:
        dict: Updated wallet record or None
    """
    update_data["updated_at"] = datetime.utcnow()
    
    try:
        result = await db["user_wallets"].find_one_and_update(
            {"_id": wallet_id, "user_id": user_id},
            {"$set": update_data},
            return_document=True
        )
        
        if result:
            logger.info(f"User wallet updated: id={wallet_id}")
        else:
            logger.warning(f"User wallet not found for update: id={wallet_id}")
        
        return result
    except Exception as e:
        logger.error(f"Failed to update user wallet: {str(e)}")
        raise


async def delete_user_wallet(
    db: AsyncIOMotorDatabase,
    wallet_id: ObjectId,
    user_id: ObjectId
) -> bool:
    """
    Delete user wallet (hard delete).
    
    Args:
        db: Database instance
        wallet_id: Wallet instance ID
        user_id: User ID (for ownership check)
        
    Returns:
        bool: True if wallet was deleted, False otherwise
    """
    try:
        result = await db["user_wallets"].delete_one(
            {"_id": wallet_id, "user_id": user_id}
        )
        
        if result.deleted_count > 0:
            logger.info(f"User wallet deleted: id={wallet_id}")
            return True
        else:
            logger.warning(f"User wallet not found for deletion: id={wallet_id}")
            return False
    except Exception as e:
        logger.error(f"Failed to delete user wallet: {str(e)}")
        raise


async def check_active_wallet_for_credential(
    db: AsyncIOMotorDatabase,
    credential_id: ObjectId
) -> Optional[dict]:
    """
    Check if there's an active wallet instance for a credential.
    
    Args:
        db: Database instance
        credential_id: Credential ID
        
    Returns:
        dict: Active wallet instance or None
    """
    try:
        wallet = await db["user_wallets"].find_one({
            "credential_id": credential_id,
            "status": "active"
        })
        return wallet
    except Exception as e:
        logger.error(f"Failed to check active wallet for credential: {str(e)}")
        raise
