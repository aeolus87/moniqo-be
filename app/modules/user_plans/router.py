"""
User_Plans API endpoints.

REST API routes for subscription management.
"""

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.responses import success_response, error_response
from app.core.dependencies import get_current_user, require_permission
from app.modules.user_plans.schemas import UserPlanCreate, UserPlanUpdate, UserPlanResponse
from app.modules.user_plans import service as user_plans_service
from app.shared.exceptions import (
    DuplicateResourceError,
    ResourceNotFoundError,
    ValidationError,
    BadRequestError
)
from app.utils.logger import get_logger
from app.utils.pagination import get_pagination_params, create_paginated_response

logger = get_logger(__name__)

router = APIRouter(prefix="/user-plans", tags=["user-plans"])


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
    response_description="Subscription created successfully",
    dependencies=[Depends(require_permission("user_plans", "write"))]
)
async def create_subscription(
    subscription_data: UserPlanCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db())
):
    """
    Create a new subscription for the current user.
    
    Requires: user_plans:write permission
    """
    try:
        subscription = await user_plans_service.create_subscription(
            db,
            str(current_user["_id"]),
            subscription_data
        )
        return success_response(
            status_code=status.HTTP_201_CREATED,
            message="Subscription created successfully",
            data=subscription
        )
    except ResourceNotFoundError as e:
        logger.warning(f"Subscription creation failed: {str(e)}")
        return error_json_response(
            status_code=e.status_code,
            message="Subscription creation failed",
            error_code=e.code,
            error_message=str(e)
        )
    except DuplicateResourceError as e:
        logger.warning(f"Subscription creation failed: {str(e)}")
        return error_json_response(
            status_code=e.status_code,
            message="Subscription creation failed",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error creating subscription: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Subscription creation failed",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.get(
    "/current",
    status_code=status.HTTP_200_OK,
    response_description="Current subscription retrieved successfully",
    dependencies=[Depends(require_permission("user_plans", "read"))]
)
async def get_current_subscription(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db())
):
    """
    Get current user's active subscription.
    
    Requires: user_plans:read permission
    """
    try:
        subscription = await user_plans_service.get_current_subscription(
            db,
            str(current_user["_id"])
        )
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Current subscription retrieved successfully",
            data=subscription
        )
    except ResourceNotFoundError as e:
        logger.warning(f"No active subscription found for user: {current_user['_id']}")
        return error_json_response(
            status_code=e.status_code,
            message="No active subscription found",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Error retrieving current subscription: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to retrieve subscription",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_description="Subscriptions retrieved successfully",
    dependencies=[Depends(require_permission("user_plans", "read"))]
)
async def list_user_subscriptions(
    limit: int = Query(10, description="Number of items per page"),
    offset: int = Query(0, description="Number of items to skip"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db())
):
    """
    List current user's subscriptions with pagination.
    
    Requires: user_plans:read permission
    """
    try:
        # Normalize pagination parameters
        limit, offset = get_pagination_params(limit, offset)
        
        subscriptions, total = await user_plans_service.list_user_subscriptions(
            db,
            str(current_user["_id"]),
            limit,
            offset
        )
        paginated_data = create_paginated_response(subscriptions, total, limit, offset)
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Subscriptions retrieved successfully",
            data=paginated_data
        )
    except Exception as e:
        logger.error(f"Error listing subscriptions: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to retrieve subscriptions",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.get(
    "/{subscription_id}",
    status_code=status.HTTP_200_OK,
    response_description="Subscription retrieved successfully",
    dependencies=[Depends(require_permission("user_plans", "read"))]
)
async def get_subscription(
    subscription_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db())
):
    """
    Get subscription by ID (must belong to current user).
    
    Requires: user_plans:read permission
    """
    try:
        subscription = await user_plans_service.get_subscription_by_id(
            db,
            subscription_id,
            str(current_user["_id"])
        )
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Subscription retrieved successfully",
            data=subscription
        )
    except ResourceNotFoundError as e:
        logger.warning(f"Subscription not found: {subscription_id}")
        return error_json_response(
            status_code=e.status_code,
            message="Subscription not found",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Error retrieving subscription: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to retrieve subscription",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.put(
    "/{subscription_id}",
    status_code=status.HTTP_200_OK,
    response_description="Subscription updated successfully",
    dependencies=[Depends(require_permission("user_plans", "write"))]
)
async def update_subscription(
    subscription_id: str,
    subscription_data: UserPlanUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db())
):
    """
    Update subscription (must belong to current user).
    
    Requires: user_plans:write permission
    """
    try:
        subscription = await user_plans_service.update_subscription(
            db,
            subscription_id,
            str(current_user["_id"]),
            subscription_data
        )
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Subscription updated successfully",
            data=subscription
        )
    except ResourceNotFoundError as e:
        logger.warning(f"Subscription not found: {subscription_id}")
        return error_json_response(
            status_code=e.status_code,
            message="Subscription not found",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating subscription: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to update subscription",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.post(
    "/{subscription_id}/cancel",
    status_code=status.HTTP_200_OK,
    response_description="Subscription cancelled successfully",
    dependencies=[Depends(require_permission("user_plans", "write"))]
)
async def cancel_subscription(
    subscription_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db())
):
    """
    Cancel subscription (must belong to current user).
    
    Requires: user_plans:write permission
    """
    try:
        subscription = await user_plans_service.cancel_subscription(
            db,
            subscription_id,
            str(current_user["_id"])
        )
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Subscription cancelled successfully",
            data=subscription
        )
    except ResourceNotFoundError as e:
        logger.warning(f"Subscription not found: {subscription_id}")
        return error_json_response(
            status_code=e.status_code,
            message="Subscription not found",
            error_code=e.code,
            error_message=str(e)
        )
    except BadRequestError as e:
        logger.warning(f"Subscription cancellation failed: {str(e)}")
        return error_json_response(
            status_code=e.status_code,
            message="Subscription cancellation failed",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Error cancelling subscription: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to cancel subscription",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.post(
    "/{subscription_id}/renew",
    status_code=status.HTTP_200_OK,
    response_description="Subscription renewed successfully",
    dependencies=[Depends(require_permission("user_plans", "write"))]
)
async def renew_subscription(
    subscription_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db())
):
    """
    Renew subscription (extend end_date, must belong to current user).
    
    Requires: user_plans:write permission
    """
    try:
        subscription = await user_plans_service.renew_subscription(
            db,
            subscription_id,
            str(current_user["_id"])
        )
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Subscription renewed successfully",
            data=subscription
        )
    except ResourceNotFoundError as e:
        logger.warning(f"Subscription not found: {subscription_id}")
        return error_json_response(
            status_code=e.status_code,
            message="Subscription not found",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Error renewing subscription: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to renew subscription",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )

