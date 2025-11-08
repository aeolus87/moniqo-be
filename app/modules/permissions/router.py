"""
Permissions module router.

API endpoints for permission operations.
"""

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.config.database import get_database
from app.core.dependencies import get_current_active_superuser
from app.core.responses import success_response, error_response, paginated_response
from app.core.exceptions import DuplicateResourceError, ResourceNotFoundError
from app.modules.permissions import service as permission_service
from app.modules.permissions.schemas import PermissionCreate, PermissionUpdate, PermissionResponse
from app.utils.pagination import get_pagination_params
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/permissions", tags=["Permissions"])


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
    response_description="Permission created successfully"
)
async def create_permission(
    permission_data: PermissionCreate,
    current_user: dict = Depends(get_current_active_superuser),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create a new permission.
    
    Creates a new permission with the provided resource, action, and description.
    Only superusers can create permissions.
    
    Args:
        permission_data: Permission creation data
        current_user: Current authenticated superuser
        db: Database instance
        
    Returns:
        Standardized response with created permission
    """
    try:
        permission = await permission_service.create_permission(db, permission_data)
        
        return success_response(
            status_code=status.HTTP_201_CREATED,
            message="Permission created successfully",
            data=permission.model_dump(by_alias=True)
        )
        
    except DuplicateResourceError as e:
        logger.warning(f"Permission creation failed: {str(e)}")
        return error_json_response(
            status_code=e.status_code,
            message="Permission creation failed",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during permission creation: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Permission creation failed",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_description="Permissions retrieved successfully"
)
async def list_permissions(
    limit: int = Query(10, description="Number of items per page"),
    offset: int = Query(0, description="Number of items to skip"),
    current_user: dict = Depends(get_current_active_superuser),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    List all permissions (paginated).
    
    Returns a paginated list of permissions. Only superusers can list permissions.
    
    Args:
        limit: Number of permissions per page
        offset: Number of permissions to skip
        current_user: Current authenticated superuser
        db: Database instance
        
    Returns:
        Standardized paginated response with permissions
    """
    try:
        # Validate and normalize pagination params
        limit, offset = get_pagination_params(limit, offset)
        
        permissions, total = await permission_service.list_permissions(db, limit, offset)
        
        # Convert to dict
        permissions_dict = [permission.model_dump(by_alias=True) for permission in permissions]
        
        return paginated_response(
            status_code=status.HTTP_200_OK,
            message="Permissions retrieved successfully",
            items=permissions_dict,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error(f"Unexpected error during permissions listing: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to retrieve permissions",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.get(
    "/{permission_id}",
    status_code=status.HTTP_200_OK,
    response_description="Permission retrieved successfully"
)
async def get_permission(
    permission_id: str,
    current_user: dict = Depends(get_current_active_superuser),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get permission by ID.
    
    Returns permission data for the specified ID. Only superusers can get permissions.
    
    Args:
        permission_id: Permission ID
        current_user: Current authenticated superuser
        db: Database instance
        
    Returns:
        Standardized response with permission data
    """
    try:
        permission = await permission_service.get_permission_by_id(db, permission_id)
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Permission retrieved successfully",
            data=permission.model_dump(by_alias=True)
        )
        
    except ResourceNotFoundError as e:
        logger.warning(f"Permission not found: {str(e)}")
        return error_json_response(
            status_code=e.status_code,
            message="Permission not found",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during permission retrieval: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to retrieve permission",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.put(
    "/{permission_id}",
    status_code=status.HTTP_200_OK,
    response_description="Permission updated successfully"
)
async def update_permission(
    permission_id: str,
    permission_data: PermissionUpdate,
    current_user: dict = Depends(get_current_active_superuser),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update permission by ID.
    
    Updates permission data for the specified ID. Only superusers can update permissions.
    
    Args:
        permission_id: Permission ID
        permission_data: Permission update data
        current_user: Current authenticated superuser
        db: Database instance
        
    Returns:
        Standardized response with updated permission
    """
    try:
        permission = await permission_service.update_permission(db, permission_id, permission_data)
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Permission updated successfully",
            data=permission.model_dump(by_alias=True)
        )
        
    except ResourceNotFoundError as e:
        logger.warning(f"Permission not found: {str(e)}")
        return error_json_response(
            status_code=e.status_code,
            message="Permission update failed",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during permission update: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Permission update failed",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.delete(
    "/{permission_id}",
    status_code=status.HTTP_200_OK,
    response_description="Permission deleted successfully"
)
async def delete_permission(
    permission_id: str,
    current_user: dict = Depends(get_current_active_superuser),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete permission by ID (soft delete).
    
    Soft deletes a permission by marking it as deleted. Only superusers can delete permissions.
    
    Args:
        permission_id: Permission ID
        current_user: Current authenticated superuser
        db: Database instance
        
    Returns:
        Standardized response confirming deletion
    """
    try:
        await permission_service.delete_permission(db, permission_id)
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Permission deleted successfully",
            data={"_id": permission_id}
        )
        
    except ResourceNotFoundError as e:
        logger.warning(f"Permission not found: {str(e)}")
        return error_json_response(
            status_code=e.status_code,
            message="Permission deletion failed",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during permission deletion: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Permission deletion failed",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )

