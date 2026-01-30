"""
Roles module router.

API endpoints for role operations.
"""

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import db_provider
from app.core.dependencies import get_current_active_superuser
from app.core.responses import success_response, error_response, paginated_response
from app.shared.exceptions import DuplicateResourceError, ResourceNotFoundError
from app.modules.roles import service as role_service
from app.modules.roles.schemas import RoleCreate, RoleUpdate, RoleResponse
from app.utils.pagination import get_pagination_params
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/roles", tags=["Roles"])


def error_json_response(status_code: int, message: str, error_code: str, error_message: str) -> JSONResponse:
    """Helper to create JSON error response with proper status code."""
    response = error_response(
        status_code=status_code,
        message=message,
        error_code=error_code,
        error_message=error_message
    )
    return JSONResponse(status_code=status_code, content=response)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_description="Role created successfully"
)
async def create_role(
    role_data: RoleCreate,
    current_user: dict = Depends(get_current_active_superuser),
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db())
):
    """
    Create a new role.
    
    Creates a new role with the provided name, description, and permissions.
    Only superusers can create roles.
    
    Args:
        role_data: Role creation data
        current_user: Current authenticated superuser
        db: Database instance
        
    Returns:
        Standardized response with created role
    """
    try:
        role = await role_service.create_role(db, role_data)
        
        return success_response(
            status_code=status.HTTP_201_CREATED,
            message="Role created successfully",
            data=role.model_dump(by_alias=True)
        )
        
    except DuplicateResourceError as e:
        logger.warning(f"Role creation failed: {str(e)}")
        return error_json_response(
            status_code=e.status_code,
            message="Role creation failed",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during role creation: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Role creation failed",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_description="Roles retrieved successfully"
)
async def list_roles(
    limit: int = Query(10, description="Number of items per page"),
    offset: int = Query(0, description="Number of items to skip"),
    current_user: dict = Depends(get_current_active_superuser),
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db())
):
    """
    List all roles (paginated).
    
    Returns a paginated list of roles. Only superusers can list roles.
    
    Args:
        limit: Number of roles per page
        offset: Number of roles to skip
        current_user: Current authenticated superuser
        db: Database instance
        
    Returns:
        Standardized paginated response with roles
    """
    try:
        # Validate and normalize pagination params
        limit, offset = get_pagination_params(limit, offset)
        
        roles, total = await role_service.list_roles(db, limit, offset)
        
        # Convert to dict
        roles_dict = [role.model_dump(by_alias=True) for role in roles]
        
        return paginated_response(
            status_code=status.HTTP_200_OK,
            message="Roles retrieved successfully",
            items=roles_dict,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error(f"Unexpected error during roles listing: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to retrieve roles",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.get(
    "/{role_id}",
    status_code=status.HTTP_200_OK,
    response_description="Role retrieved successfully"
)
async def get_role(
    role_id: str,
    current_user: dict = Depends(get_current_active_superuser),
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db())
):
    """
    Get role by ID.
    
    Returns role data for the specified ID. Only superusers can get roles.
    
    Args:
        role_id: Role ID
        current_user: Current authenticated superuser
        db: Database instance
        
    Returns:
        Standardized response with role data
    """
    try:
        role = await role_service.get_role_by_id(db, role_id)
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Role retrieved successfully",
            data=role.model_dump(by_alias=True)
        )
        
    except ResourceNotFoundError as e:
        logger.warning(f"Role not found: {str(e)}")
        return error_json_response(
            status_code=e.status_code,
            message="Role not found",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during role retrieval: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to retrieve role",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.put(
    "/{role_id}",
    status_code=status.HTTP_200_OK,
    response_description="Role updated successfully"
)
async def update_role(
    role_id: str,
    role_data: RoleUpdate,
    current_user: dict = Depends(get_current_active_superuser),
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db())
):
    """
    Update role by ID.
    
    Updates role data for the specified ID. Only superusers can update roles.
    
    Args:
        role_id: Role ID
        role_data: Role update data
        current_user: Current authenticated superuser
        db: Database instance
        
    Returns:
        Standardized response with updated role
    """
    try:
        role = await role_service.update_role(db, role_id, role_data)
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Role updated successfully",
            data=role.model_dump(by_alias=True)
        )
        
    except (ResourceNotFoundError, DuplicateResourceError) as e:
        logger.warning(f"Role update failed: {str(e)}")
        return error_json_response(
            status_code=e.status_code,
            message="Role update failed",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during role update: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Role update failed",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_200_OK,
    response_description="Role deleted successfully"
)
async def delete_role(
    role_id: str,
    current_user: dict = Depends(get_current_active_superuser),
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db())
):
    """
    Delete role by ID (soft delete).
    
    Soft deletes a role by marking it as deleted. Only superusers can delete roles.
    
    Args:
        role_id: Role ID
        current_user: Current authenticated superuser
        db: Database instance
        
    Returns:
        Standardized response confirming deletion
    """
    try:
        await role_service.delete_role(db, role_id)
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Role deleted successfully",
            data={"_id": role_id}
        )
        
    except ResourceNotFoundError as e:
        logger.warning(f"Role not found: {str(e)}")
        return error_json_response(
            status_code=e.status_code,
            message="Role deletion failed",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during role deletion: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Role deletion failed",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )

