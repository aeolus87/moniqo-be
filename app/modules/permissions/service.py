"""
Permissions module service.

Business logic for permission operations.
"""

from motor.motor_asyncio import AsyncIOMotorDatabase
from app.modules.permissions import models as permission_models
from app.modules.permissions.schemas import PermissionCreate, PermissionUpdate, PermissionResponse
from app.shared.exceptions import DuplicateResourceError, ResourceNotFoundError
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def create_permission(
    db: AsyncIOMotorDatabase,
    permission_data: PermissionCreate
) -> PermissionResponse:
    """
    Create a new permission.
    
    Args:
        db: Database instance
        permission_data: Permission creation data
        
    Returns:
        Created permission
        
    Raises:
        DuplicateResourceError: If permission with same resource/action already exists
    """
    # Check if permission already exists
    existing_permission = await permission_models.find_permission_by_resource_action(
        db,
        permission_data.resource,
        permission_data.action
    )
    
    if existing_permission:
        logger.warning(f"Permission creation attempt with duplicate resource/action: {permission_data.resource}:{permission_data.action}")
        raise DuplicateResourceError(
            f"Permission with resource '{permission_data.resource}' and action '{permission_data.action}' already exists"
        )
    
    # Create permission
    permission_doc = await permission_models.create_permission(
        db,
        permission_data.resource,
        permission_data.action,
        permission_data.description
    )
    
    logger.info(f"Permission created successfully: {permission_data.resource}:{permission_data.action}")
    return PermissionResponse(**permission_doc)


async def get_permission_by_id(
    db: AsyncIOMotorDatabase,
    permission_id: str
) -> PermissionResponse:
    """
    Get permission by ID.
    
    Args:
        db: Database instance
        permission_id: Permission ID
        
    Returns:
        Permission data
        
    Raises:
        ResourceNotFoundError: If permission not found
    """
    permission = await permission_models.find_permission_by_id(db, permission_id)
    
    if not permission:
        logger.warning(f"Permission not found: id={permission_id}")
        raise ResourceNotFoundError(f"Permission with ID {permission_id} not found")
    
    return PermissionResponse(**permission)


async def list_permissions(
    db: AsyncIOMotorDatabase,
    limit: int = 10,
    offset: int = 0
) -> tuple[list[PermissionResponse], int]:
    """
    List all permissions (paginated).
    
    Args:
        db: Database instance
        limit: Number of permissions per page
        offset: Number of permissions to skip
        
    Returns:
        Tuple of (list of permissions, total count)
    """
    permissions, total = await permission_models.find_permissions(db, limit, offset)
    
    permission_responses = [PermissionResponse(**perm) for perm in permissions]
    
    logger.info(f"Listed {len(permission_responses)} permissions (total: {total})")
    return permission_responses, total


async def update_permission(
    db: AsyncIOMotorDatabase,
    permission_id: str,
    permission_data: PermissionUpdate
) -> PermissionResponse:
    """
    Update permission by ID.
    
    Args:
        db: Database instance
        permission_id: Permission ID
        permission_data: Permission update data
        
    Returns:
        Updated permission
        
    Raises:
        ResourceNotFoundError: If permission not found
    """
    # Build update dict (only include fields that were provided)
    update_dict = permission_data.model_dump(exclude_unset=True)
    
    if not update_dict:
        # No fields to update, just return existing permission
        return await get_permission_by_id(db, permission_id)
    
    # Update permission
    updated_permission = await permission_models.update_permission(
        db,
        permission_id,
        update_dict
    )
    
    if not updated_permission:
        logger.warning(f"Permission not found for update: id={permission_id}")
        raise ResourceNotFoundError(f"Permission with ID {permission_id} not found")
    
    logger.info(f"Permission updated successfully: id={permission_id}")
    return PermissionResponse(**updated_permission)


async def delete_permission(
    db: AsyncIOMotorDatabase,
    permission_id: str
) -> bool:
    """
    Soft delete permission by ID.
    
    Args:
        db: Database instance
        permission_id: Permission ID
        
    Returns:
        True if successful
        
    Raises:
        ResourceNotFoundError: If permission not found
    """
    success = await permission_models.soft_delete_permission(db, permission_id)
    
    if not success:
        logger.warning(f"Permission not found for deletion: id={permission_id}")
        raise ResourceNotFoundError(f"Permission with ID {permission_id} not found")
    
    logger.info(f"Permission deleted successfully: id={permission_id}")
    return True

