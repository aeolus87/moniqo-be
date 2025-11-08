"""
Users module router.

API endpoints for user operations.
"""

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.config.database import get_database
from app.core.dependencies import get_current_user, require_permission
from app.core.responses import success_response, error_response, paginated_response
from app.core.exceptions import UserNotFoundError, ValidationError
from app.modules.users import service as user_service
from app.modules.users.schemas import UserUpdate, UserResponse
from app.utils.pagination import get_pagination_params
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


def error_json_response(status_code: int, message: str, error_code: str, error_message: str) -> JSONResponse:
    """Helper to create JSON error response with proper status code."""
    response = error_response(
        status_code=status_code,
        message=message,
        error_code=error_code,
        error_message=error_message
    )
    return JSONResponse(status_code=status_code, content=response)


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    response_description="Current user retrieved successfully"
)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get current user information.
    
    Returns the authenticated user's profile data.
    
    Args:
        current_user: Current authenticated user
        db: Database instance
        
    Returns:
        Standardized response with user data
    """
    try:
        user = await user_service.get_user_by_id(db, str(current_user["_id"]))
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="User retrieved successfully",
            data=user.model_dump()
        )
        
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to retrieve user",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.put(
    "/me",
    status_code=status.HTTP_200_OK,
    response_description="User updated successfully"
)
async def update_current_user(
    update_data: UserUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update current user information.
    
    Updates the authenticated user's profile data.
    
    Args:
        update_data: Update data
        current_user: Current authenticated user
        db: Database instance
        
    Returns:
        Standardized response with updated user data
    """
    try:
        user = await user_service.update_user(db, str(current_user["_id"]), update_data)
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="User updated successfully",
            data=user.model_dump()
        )
        
    except ValidationError as e:
        logger.warning(f"User update validation failed: {str(e)}")
        return error_json_response(
            status_code=e.status_code,
            message="Update failed",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating current user: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Update failed",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.delete(
    "/me",
    status_code=status.HTTP_200_OK,
    response_description="User deleted successfully"
)
async def delete_current_user(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete current user account.
    
    Soft deletes the authenticated user's account.
    
    Args:
        current_user: Current authenticated user
        db: Database instance
        
    Returns:
        Standardized response
    """
    try:
        await user_service.soft_delete_user(db, str(current_user["_id"]))
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="User deleted successfully",
            data=None
        )
        
    except UserNotFoundError as e:
        logger.warning(f"User deletion failed: {str(e)}")
        return error_json_response(
            status_code=e.status_code,
            message="Deletion failed",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting current user: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Deletion failed",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_description="Users retrieved successfully",
    dependencies=[Depends(require_permission("users", "read"))]
)
async def list_users(
    limit: int = Query(10, description="Number of items per page"),
    offset: int = Query(0, description="Number of items to skip"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    List all users (paginated).
    
    Returns a paginated list of users. Requires admin permission.
    
    Args:
        limit: Number of users per page
        offset: Number of users to skip
        current_user: Current authenticated user
        db: Database instance
        
    Returns:
        Standardized paginated response with users
    """
    try:
        # Validate and normalize pagination params
        limit, offset = get_pagination_params(limit, offset)
        
        users, total = await user_service.list_users(db, limit, offset)
        
        # Convert to dict
        users_dict = [user.model_dump() for user in users]
        
        return paginated_response(
            status_code=status.HTTP_200_OK,
            message="Users retrieved successfully",
            items=users_dict,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to retrieve users",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.get(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    response_description="User retrieved successfully",
    dependencies=[Depends(require_permission("users", "read"))]
)
async def get_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get user by ID.
    
    Returns user information by ID. Requires admin permission.
    
    Args:
        user_id: User ID
        current_user: Current authenticated user
        db: Database instance
        
    Returns:
        Standardized response with user data
    """
    try:
        user = await user_service.get_user_by_id(db, user_id)
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="User retrieved successfully",
            data=user.model_dump()
        )
        
    except UserNotFoundError as e:
        logger.warning(f"User not found: {str(e)}")
        return error_json_response(
            status_code=e.status_code,
            message="User not found",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to retrieve user",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.put(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    response_description="User updated successfully",
    dependencies=[Depends(require_permission("users", "write"))]
)
async def update_user(
    user_id: str,
    update_data: UserUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update user by ID.
    
    Updates user information by ID. Requires admin permission.
    
    Args:
        user_id: User ID
        update_data: Update data
        current_user: Current authenticated user
        db: Database instance
        
    Returns:
        Standardized response with updated user data
    """
    try:
        user = await user_service.update_user(db, user_id, update_data)
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="User updated successfully",
            data=user.model_dump()
        )
        
    except UserNotFoundError as e:
        logger.warning(f"User update failed: {str(e)}")
        return error_json_response(
            status_code=e.status_code,
            message="Update failed",
            error_code=e.code,
            error_message=str(e)
        )
    except ValidationError as e:
        logger.warning(f"User update validation failed: {str(e)}")
        return error_json_response(
            status_code=e.status_code,
            message="Update failed",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Update failed",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    response_description="User deleted successfully",
    dependencies=[Depends(require_permission("users", "delete"))]
)
async def delete_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete user by ID.
    
    Soft deletes user by ID. Requires admin permission.
    
    Args:
        user_id: User ID
        current_user: Current authenticated user
        db: Database instance
        
    Returns:
        Standardized response
    """
    try:
        await user_service.soft_delete_user(db, user_id)
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="User deleted successfully",
            data=None
        )
        
    except UserNotFoundError as e:
        logger.warning(f"User deletion failed: {str(e)}")
        return error_json_response(
            status_code=e.status_code,
            message="Deletion failed",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Deletion failed",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )

