"""
Core dependencies for FastAPI routes.

Provides dependencies for authentication and authorization.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.security import verify_token
from app.shared.exceptions import (
    TokenExpiredError,
    InvalidTokenError,
    InactiveAccountError,
    UserNotFoundError,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

# HTTP Bearer token scheme (auto_error=False to handle missing token manually)
security = HTTPBearer(auto_error=False)


async def get_db() -> AsyncIOMotorDatabase:
    """
    FastAPI dependency to get database instance.
    
    Automatically routes to correct database (real/demo) based on trading mode context.
    
    Returns:
        AsyncIOMotorDatabase: Database instance for current trading mode
    """
    # Lazy import to avoid circular import
    from app.core.database import db_provider
    return db_provider.get_db()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> dict:
    """
    Get current authenticated user from JWT token.
    
    Extracts and validates JWT token from Authorization header,
    then retrieves the user from database.
    
    Args:
        credentials: HTTP authorization credentials
        db: Database instance
        
    Returns:
        dict: Current user data
        
    Raises:
        HTTPException: If authentication fails
        
    Example:
        @router.get("/me")
        async def get_me(current_user: dict = Depends(get_current_user)):
            return current_user
    """
    # Check if credentials are provided
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = credentials.credentials
    
    try:
        # Verify and decode token
        payload = verify_token(token, token_type="access")
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
        
        # Get user from database
        user = await db["users"].find_one({"_id": ObjectId(user_id), "is_deleted": False})
        
        if not user:
            logger.warning(f"User not found for token: user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Get auth record to check if account is active
        auth = await db["auth"].find_one({"_id": user["auth_id"], "is_deleted": False})
        
        if not auth:
            logger.warning(f"Auth record not found: auth_id={user['auth_id']}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if not auth["is_active"]:
            logger.warning(f"Inactive account access attempt: user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )
        
        # Add email to user data for convenience
        user["email"] = auth["email"]
        
        return user
        
    except TokenExpiredError:
        logger.warning("Access attempt with expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except InvalidTokenError:
        logger.warning("Access attempt with invalid token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> Optional[dict]:
    """
    Get current user if authenticated, None otherwise.
    
    Similar to get_current_user but doesn't raise error if not authenticated.
    Useful for endpoints that have different behavior for authenticated vs anonymous users.
    
    Args:
        credentials: HTTP authorization credentials (optional)
        db: Database instance
        
    Returns:
        dict: Current user data or None
        
    Example:
        @router.get("/public")
        async def public_endpoint(current_user: Optional[dict] = Depends(get_current_user_optional)):
            if current_user:
                return {"message": f"Hello {current_user['first_name']}"}
            return {"message": "Hello guest"}
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


def require_permission(resource: str, action: str):
    """
    Dependency factory for permission checking.
    
    Creates a dependency that checks if current user has specific permission.
    Will be fully implemented in Sprint 19 after roles/permissions modules.
    
    Args:
        resource: Resource name (e.g., "users", "roles")
        action: Action name (e.g., "read", "write", "delete")
        
    Returns:
        Dependency function
        
    Example:
        @router.get("/users", dependencies=[Depends(require_permission("users", "read"))])
        async def list_users():
            pass
    """
    async def permission_checker(
        current_user: dict = Depends(get_current_user),
        db: AsyncIOMotorDatabase = Depends(get_db)
    ) -> dict:
        """
        Check if user has required permission.
        
        Args:
            current_user: Current authenticated user
            db: Database instance
            
        Returns:
            dict: Current user data
            
        Raises:
            HTTPException: If permission denied
        """
        logger.debug(f"Permission check: user={current_user.get('email')}, resource={resource}, action={action}")
        
        try:
            # 1. Get user's role ID
            user_role_id = current_user.get("user_role")
            
            if not user_role_id:
                logger.warning(f"User has no role assigned: user_id={current_user.get('_id')}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User has no role assigned"
                )
            
            # 2. Get user's role from database
            role = await db.roles.find_one({
                "_id": user_role_id if isinstance(user_role_id, ObjectId) else ObjectId(user_role_id),
                "is_deleted": False
            })
            
            if not role:
                logger.warning(f"Role not found for user: user_id={current_user.get('_id')}, role_id={user_role_id}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User role not found"
                )
            
            # 3. Get role's permissions
            permission_ids = role.get("permissions", [])
            
            if not permission_ids:
                logger.warning(f"User role has no permissions: user_id={current_user.get('_id')}, role={role.get('name')}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            
            # 4. Fetch permissions from database
            permissions = await db.permissions.find({
                "_id": {"$in": permission_ids},
                "is_deleted": False
            }).to_list(length=len(permission_ids))
            
            # 5. Check if required permission exists
            required_permission = f"{resource}:{action}"
            has_permission = any(
                f"{perm.get('resource')}:{perm.get('action')}" == required_permission
                for perm in permissions
            )
            
            if not has_permission:
                logger.warning(
                    f"Permission denied: user={current_user.get('email')}, "
                    f"required={required_permission}, role={role.get('name')}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required: {required_permission}"
                )
            
            logger.debug(f"Permission granted: user={current_user.get('email')}, permission={required_permission}")
            return current_user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error checking permissions: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error checking permissions"
            )
    
    return permission_checker


async def get_current_active_superuser(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> dict:
    """
    Get current user and verify they are a superuser.
    
    Args:
        current_user: Current authenticated user
        db: Database instance
        
    Returns:
        dict: Current user data
        
    Raises:
        HTTPException: If user is not a superuser
    """
    # TODO: Implement superuser check in Sprint 19
    # For now, check if user's email matches SUPERADMIN_EMAIL
    from app.core.config import settings
    
    superadmin_email = settings.SUPERADMIN_EMAIL if settings else "admin@example.com"
    
    if current_user.get("email") == superadmin_email:
        return current_user
    
    logger.warning(f"Non-superuser access attempt: user={current_user.get('email')}")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Superuser access required"
    )


def validate_object_id(id_value: str) -> str:
    """
    Validate ObjectId format and raise HTTPException if invalid.
    
    Args:
        id_value: Object ID string to validate
        
    Returns:
        str: Validated Object ID string
        
    Raises:
        HTTPException: If Object ID format is invalid
        
    Example:
        @router.get("/{credentials_id}")
        async def get_credentials(credentials_id: str = Path(...)):
            validate_object_id(credentials_id)
            # ... rest of handler
    """
    try:
        ObjectId(id_value)
        return id_value
    except InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ID format: '{id_value}' is not a valid Object ID"
        )


# Export dependencies
__all__ = [
    "get_db",
    "get_current_user",
    "get_current_user_optional",
    "require_permission",
    "get_current_active_superuser",
    "validate_object_id",
]


def get_wallet_factory():
    """Get wallet factory instance."""
    from app.infrastructure.exchanges.factory import WalletFactory
    return WalletFactory()

