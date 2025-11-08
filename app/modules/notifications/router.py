"""
Notifications API endpoints.

REST API routes for notification management.
"""

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional
from app.config import get_database
from app.core.responses import success_response, error_response
from app.core.dependencies import get_current_user, require_permission
from app.modules.notifications.schemas import NotificationCreate, NotificationResponse
from app.modules.notifications import service as notifications_service
from app.core.exceptions import ResourceNotFoundError
from app.utils.logger import get_logger
from app.utils.pagination import get_pagination_params, create_paginated_response

logger = get_logger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


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
    response_description="Notification created successfully",
    dependencies=[Depends(require_permission("notifications", "write"))]
)
async def create_notification(
    notification_data: NotificationCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create a new notification for the current user.
    
    Requires: notifications:write permission
    """
    try:
        notification = await notifications_service.create_notification(
            db,
            str(current_user["_id"]),
            notification_data
        )
        return success_response(
            status_code=status.HTTP_201_CREATED,
            message="Notification created successfully",
            data=notification
        )
    except Exception as e:
        logger.error(f"Unexpected error creating notification: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Notification creation failed",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_description="Notifications retrieved successfully",
    dependencies=[Depends(require_permission("notifications", "read"))]
)
async def list_notifications(
    limit: int = Query(10, description="Number of items per page"),
    offset: int = Query(0, description="Number of items to skip"),
    is_read: Optional[bool] = Query(None, description="Filter by read status"),
    type: Optional[str] = Query(None, description="Filter by notification type"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    List current user's notifications with pagination and filters.
    
    Requires: notifications:read permission
    """
    try:
        # Normalize pagination parameters
        limit, offset = get_pagination_params(limit, offset)
        
        notifications, total = await notifications_service.list_user_notifications(
            db,
            str(current_user["_id"]),
            limit,
            offset,
            is_read,
            type
        )
        paginated_data = create_paginated_response(notifications, total, limit, offset)
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Notifications retrieved successfully",
            data=paginated_data
        )
    except Exception as e:
        logger.error(f"Error listing notifications: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to retrieve notifications",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.get(
    "/unread-count",
    status_code=status.HTTP_200_OK,
    response_description="Unread count retrieved successfully",
    dependencies=[Depends(require_permission("notifications", "read"))]
)
async def get_unread_count(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get count of unread notifications for current user.
    
    Requires: notifications:read permission
    """
    try:
        result = await notifications_service.get_unread_count(
            db,
            str(current_user["_id"])
        )
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Unread count retrieved successfully",
            data=result
        )
    except Exception as e:
        logger.error(f"Error getting unread count: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to retrieve unread count",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.get(
    "/{notification_id}",
    status_code=status.HTTP_200_OK,
    response_description="Notification retrieved successfully",
    dependencies=[Depends(require_permission("notifications", "read"))]
)
async def get_notification(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get notification by ID (must belong to current user).
    
    Requires: notifications:read permission
    """
    try:
        notification = await notifications_service.get_notification_by_id(
            db,
            notification_id,
            str(current_user["_id"])
        )
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Notification retrieved successfully",
            data=notification
        )
    except ResourceNotFoundError as e:
        logger.warning(f"Notification not found: {notification_id}")
        return error_json_response(
            status_code=e.status_code,
            message="Notification not found",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Error retrieving notification: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to retrieve notification",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.post(
    "/{notification_id}/read",
    status_code=status.HTTP_200_OK,
    response_description="Notification marked as read successfully",
    dependencies=[Depends(require_permission("notifications", "write"))]
)
async def mark_notification_as_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Mark notification as read (must belong to current user).
    
    Requires: notifications:write permission
    """
    try:
        notification = await notifications_service.mark_notification_as_read(
            db,
            notification_id,
            str(current_user["_id"])
        )
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Notification marked as read",
            data=notification
        )
    except ResourceNotFoundError as e:
        logger.warning(f"Notification not found: {notification_id}")
        return error_json_response(
            status_code=e.status_code,
            message="Notification not found",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to mark notification as read",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.post(
    "/read-all",
    status_code=status.HTTP_200_OK,
    response_description="All notifications marked as read successfully",
    dependencies=[Depends(require_permission("notifications", "write"))]
)
async def mark_all_as_read(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Mark all unread notifications as read for current user.
    
    Requires: notifications:write permission
    """
    try:
        result = await notifications_service.mark_all_notifications_as_read(
            db,
            str(current_user["_id"])
        )
        return success_response(
            status_code=status.HTTP_200_OK,
            message="All notifications marked as read",
            data=result
        )
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to mark all notifications as read",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_200_OK,
    response_description="Notification deleted successfully",
    dependencies=[Depends(require_permission("notifications", "write"))]
)
async def delete_notification(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Soft delete notification (must belong to current user).
    
    Requires: notifications:write permission
    """
    try:
        result = await notifications_service.delete_notification(
            db,
            notification_id,
            str(current_user["_id"])
        )
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Notification deleted successfully",
            data=result
        )
    except ResourceNotFoundError as e:
        logger.warning(f"Notification not found: {notification_id}")
        return error_json_response(
            status_code=e.status_code,
            message="Notification not found",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting notification: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to delete notification",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )

