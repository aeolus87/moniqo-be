"""
Users module service layer.

Business logic for user operations.
"""

from typing import List, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.exceptions import UserNotFoundError, ValidationError
from app.modules.users import models as user_models
from app.modules.users.schemas import UserUpdate, UserResponse, UserListResponse
from app.utils.cache import CacheManager
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Cache manager for users
cache = CacheManager("users")


async def get_user_by_id(
    db: AsyncIOMotorDatabase,
    user_id: str,
    include_auth: bool = True
) -> UserResponse:
    """
    Get user by ID.
    
    Args:
        db: Database instance
        user_id: User ID
        include_auth: Include auth email in response
        
    Returns:
        UserResponse: User data
        
    Raises:
        UserNotFoundError: If user not found
    """
    try:
        user = await user_models.find_user_by_id(db, ObjectId(user_id))
        
        if not user:
            raise UserNotFoundError(f"User with ID {user_id} not found")
        
        # Get auth email if needed
        email = ""
        if include_auth:
            auth = await db["auth"].find_one({"_id": user["auth_id"], "is_deleted": False})
            if auth:
                email = auth["email"]
        
        # Generate default avatar if not set
        avatar_url = user.get("avatar_url")
        if not avatar_url:
            avatar_url = user_models.generate_default_avatar_url(user["first_name"])
        
        return UserResponse(
            id=str(user["_id"]),
            email=email,
            first_name=user["first_name"],
            last_name=user["last_name"],
            birthday=user["birthday"],
            avatar_url=avatar_url,
            phone_number=user.get("phone_number"),
            user_role=str(user.get("user_role")) if user.get("user_role") else None,
            created_at=user["created_at"].isoformat(),
            updated_at=user["updated_at"].isoformat()
        )
        
    except UserNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting user by ID: {str(e)}")
        raise


async def get_user_by_auth_id(
    db: AsyncIOMotorDatabase,
    auth_id: ObjectId
) -> Optional[dict]:
    """
    Get user by auth ID.
    
    Args:
        db: Database instance
        auth_id: Auth record ID
        
    Returns:
        dict: User data or None
    """
    return await user_models.find_user_by_auth_id(db, auth_id)


async def update_user(
    db: AsyncIOMotorDatabase,
    user_id: str,
    update_data: UserUpdate
) -> UserResponse:
    """
    Update user data.
    
    Args:
        db: Database instance
        user_id: User ID
        update_data: Update data
        
    Returns:
        UserResponse: Updated user data
        
    Raises:
        UserNotFoundError: If user not found
    """
    # Convert Pydantic model to dict, excluding None values
    update_dict = update_data.model_dump(exclude_none=True)
    
    # Convert nested Pydantic models to dicts
    if "birthday" in update_dict and update_dict["birthday"]:
        update_dict["birthday"] = {
            "day": update_dict["birthday"]["day"],
            "month": update_dict["birthday"]["month"],
            "year": update_dict["birthday"]["year"]
        }
    
    if "phone_number" in update_dict and update_dict["phone_number"]:
        update_dict["phone_number"] = {
            "country_code": update_dict["phone_number"]["country_code"],
            "mobile_number": update_dict["phone_number"]["mobile_number"]
        }
    
    try:
        updated_user = await user_models.update_user(db, ObjectId(user_id), update_dict)
        
        if not updated_user:
            raise UserNotFoundError(f"User with ID {user_id} not found")
        
        # Invalidate cache
        await cache.invalidate_all()
        
        logger.info(f"User updated: id={user_id}")
        
        return await get_user_by_id(db, user_id)
        
    except UserNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        raise


async def soft_delete_user(
    db: AsyncIOMotorDatabase,
    user_id: str
) -> bool:
    """
    Soft delete user and associated auth record.
    
    Args:
        db: Database instance
        user_id: User ID
        
    Returns:
        bool: True if successful
        
    Raises:
        UserNotFoundError: If user not found
    """
    try:
        # Get user to find auth_id
        user = await user_models.find_user_by_id(db, ObjectId(user_id))
        
        if not user:
            raise UserNotFoundError(f"User with ID {user_id} not found")
        
        # Soft delete user
        user_deleted = await user_models.soft_delete_user(db, ObjectId(user_id))
        
        # Soft delete auth
        from app.modules.auth import models as auth_models
        auth_deleted = await auth_models.soft_delete_auth(db, user["auth_id"])
        
        if user_deleted and auth_deleted:
            # Invalidate cache
            await cache.invalidate_all()
            
            logger.info(f"User and auth soft deleted: user_id={user_id}")
            return True
        
        return False
        
    except UserNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error soft deleting user: {str(e)}")
        raise


async def list_users(
    db: AsyncIOMotorDatabase,
    limit: int = 10,
    offset: int = 0
) -> tuple[List[UserListResponse], int]:
    """
    List users with pagination.
    
    Args:
        db: Database instance
        limit: Number of users per page
        offset: Number of users to skip
        
    Returns:
        tuple: (list of users, total count)
    """
    # Check cache
    cache_key = f"list:limit={limit}&offset={offset}"
    cached = await cache.get("list", limit=limit, offset=offset)
    
    if cached:
        logger.debug("Returning cached user list")
        return cached["users"], cached["total"]
    
    try:
        users, total = await user_models.list_users(db, limit, offset)
        
        # Get auth emails for all users
        auth_ids = [user["auth_id"] for user in users]
        auth_cursor = db["auth"].find({"_id": {"$in": auth_ids}, "is_deleted": False})
        auth_records = await auth_cursor.to_list(length=len(auth_ids))
        auth_map = {str(auth["_id"]): auth["email"] for auth in auth_records}
        
        # Build response
        user_list = []
        for user in users:
            email = auth_map.get(str(user["auth_id"]), "")
            avatar_url = user.get("avatar_url")
            if not avatar_url:
                avatar_url = user_models.generate_default_avatar_url(user["first_name"])
            
            user_list.append(UserListResponse(
                id=str(user["_id"]),
                email=email,
                first_name=user["first_name"],
                last_name=user["last_name"],
                avatar_url=avatar_url,
                created_at=user["created_at"].isoformat()
            ))
        
        # Cache result
        await cache.set("list", {"users": user_list, "total": total}, limit=limit, offset=offset)
        
        return user_list, total
        
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        return [], 0

