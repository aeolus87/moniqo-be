"""
Roles module service.

Business logic for role operations.
"""

from motor.motor_asyncio import AsyncIOMotorDatabase
from app.modules.roles import models as role_models
from app.modules.roles.schemas import RoleCreate, RoleUpdate, RoleResponse
from app.core.exceptions import DuplicateResourceError, ResourceNotFoundError
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def create_role(
    db: AsyncIOMotorDatabase,
    role_data: RoleCreate
) -> RoleResponse:
    """
    Create a new role.
    
    Args:
        db: Database instance
        role_data: Role creation data
        
    Returns:
        Created role
        
    Raises:
        DuplicateResourceError: If role with same name already exists
    """
    # Check if role already exists
    existing_role = await role_models.find_role_by_name(db, role_data.name)
    
    if existing_role:
        logger.warning(f"Role creation attempt with duplicate name: {role_data.name}")
        raise DuplicateResourceError(f"Role with name '{role_data.name}' already exists")
    
    # Create role
    role_doc = await role_models.create_role(
        db,
        role_data.name,
        role_data.description,
        role_data.permissions
    )
    
    logger.info(f"Role created successfully: {role_data.name}")
    return RoleResponse(**role_doc)


async def get_role_by_id(
    db: AsyncIOMotorDatabase,
    role_id: str
) -> RoleResponse:
    """
    Get role by ID.
    
    Args:
        db: Database instance
        role_id: Role ID
        
    Returns:
        Role data
        
    Raises:
        ResourceNotFoundError: If role not found
    """
    role = await role_models.find_role_by_id(db, role_id)
    
    if not role:
        logger.warning(f"Role not found: id={role_id}")
        raise ResourceNotFoundError(f"Role with ID {role_id} not found")
    
    return RoleResponse(**role)


async def list_roles(
    db: AsyncIOMotorDatabase,
    limit: int = 10,
    offset: int = 0
) -> tuple[list[RoleResponse], int]:
    """
    List all roles (paginated).
    
    Args:
        db: Database instance
        limit: Number of roles per page
        offset: Number of roles to skip
        
    Returns:
        Tuple of (list of roles, total count)
    """
    roles, total = await role_models.find_roles(db, limit, offset)
    
    role_responses = [RoleResponse(**role) for role in roles]
    
    logger.info(f"Listed {len(role_responses)} roles (total: {total})")
    return role_responses, total


async def update_role(
    db: AsyncIOMotorDatabase,
    role_id: str,
    role_data: RoleUpdate
) -> RoleResponse:
    """
    Update role by ID.
    
    Args:
        db: Database instance
        role_id: Role ID
        role_data: Role update data
        
    Returns:
        Updated role
        
    Raises:
        ResourceNotFoundError: If role not found
        DuplicateResourceError: If updating to duplicate name
    """
    # Build update dict (only include fields that were provided)
    update_dict = role_data.model_dump(exclude_unset=True)
    
    if not update_dict:
        # No fields to update, just return existing role
        return await get_role_by_id(db, role_id)
    
    # If name is being updated, check for duplicates
    if "name" in update_dict:
        existing_role = await role_models.find_role_by_name(db, update_dict["name"])
        if existing_role and existing_role["_id"] != role_id:
            logger.warning(f"Role update attempt with duplicate name: {update_dict['name']}")
            raise DuplicateResourceError(f"Role with name '{update_dict['name']}' already exists")
    
    # Update role
    updated_role = await role_models.update_role(db, role_id, update_dict)
    
    if not updated_role:
        logger.warning(f"Role not found for update: id={role_id}")
        raise ResourceNotFoundError(f"Role with ID {role_id} not found")
    
    logger.info(f"Role updated successfully: id={role_id}")
    return RoleResponse(**updated_role)


async def delete_role(
    db: AsyncIOMotorDatabase,
    role_id: str
) -> bool:
    """
    Soft delete role by ID.
    
    Args:
        db: Database instance
        role_id: Role ID
        
    Returns:
        True if successful
        
    Raises:
        ResourceNotFoundError: If role not found
    """
    success = await role_models.soft_delete_role(db, role_id)
    
    if not success:
        logger.warning(f"Role not found for deletion: id={role_id}")
        raise ResourceNotFoundError(f"Role with ID {role_id} not found")
    
    logger.info(f"Role deleted successfully: id={role_id}")
    return True

