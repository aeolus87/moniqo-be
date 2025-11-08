"""
Plans API endpoints.

REST API routes for subscription plan management.
"""

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.config import get_database
from app.core.responses import success_response, error_response
from app.core.dependencies import get_current_user, require_permission
from app.modules.plans.schemas import PlanCreate, PlanUpdate, PlanResponse
from app.modules.plans import service as plans_service
from app.core.exceptions import DuplicateResourceError, ResourceNotFoundError
from app.utils.logger import get_logger
from app.utils.pagination import get_pagination_params, create_paginated_response

logger = get_logger(__name__)

router = APIRouter(prefix="/plans", tags=["plans"])


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
    response_description="Plan created successfully",
    dependencies=[Depends(require_permission("plans", "write"))]
)
async def create_plan(
    plan_data: PlanCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create a new plan.
    
    Requires: plans:write permission
    """
    try:
        plan = await plans_service.create_plan(db, plan_data)
        return success_response(
            status_code=status.HTTP_201_CREATED,
            message="Plan created successfully",
            data=plan
        )
    except DuplicateResourceError as e:
        logger.warning(f"Plan creation failed: {str(e)}")
        return error_json_response(
            status_code=e.status_code,
            message="Plan creation failed",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error creating plan: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Plan creation failed",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_description="Plans retrieved successfully",
    dependencies=[Depends(require_permission("plans", "read"))]
)
async def list_plans(
    limit: int = Query(10, description="Number of items per page"),
    offset: int = Query(0, description="Number of items to skip"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    List all plans with pagination.
    
    Requires: plans:read permission
    """
    try:
        # Normalize pagination parameters
        limit, offset = get_pagination_params(limit, offset)
        
        plans, total = await plans_service.list_plans(db, limit, offset)
        paginated_data = create_paginated_response(plans, total, limit, offset)
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Plans retrieved successfully",
            data=paginated_data
        )
    except Exception as e:
        logger.error(f"Error listing plans: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to retrieve plans",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.get(
    "/{plan_id}",
    status_code=status.HTTP_200_OK,
    response_description="Plan retrieved successfully",
    dependencies=[Depends(require_permission("plans", "read"))]
)
async def get_plan(
    plan_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get plan by ID.
    
    Requires: plans:read permission
    """
    try:
        plan = await plans_service.get_plan_by_id(db, plan_id)
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Plan retrieved successfully",
            data=plan
        )
    except ResourceNotFoundError as e:
        logger.warning(f"Plan not found: {plan_id}")
        return error_json_response(
            status_code=e.status_code,
            message="Plan not found",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Error retrieving plan: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to retrieve plan",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.put(
    "/{plan_id}",
    status_code=status.HTTP_200_OK,
    response_description="Plan updated successfully",
    dependencies=[Depends(require_permission("plans", "write"))]
)
async def update_plan(
    plan_id: str,
    plan_data: PlanUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update plan.
    
    Requires: plans:write permission
    """
    try:
        plan = await plans_service.update_plan(db, plan_id, plan_data)
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Plan updated successfully",
            data=plan
        )
    except ResourceNotFoundError as e:
        logger.warning(f"Plan not found: {plan_id}")
        return error_json_response(
            status_code=e.status_code,
            message="Plan not found",
            error_code=e.code,
            error_message=str(e)
        )
    except DuplicateResourceError as e:
        logger.warning(f"Plan update failed: {str(e)}")
        return error_json_response(
            status_code=e.status_code,
            message="Plan update failed",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating plan: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to update plan",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.delete(
    "/{plan_id}",
    status_code=status.HTTP_200_OK,
    response_description="Plan deleted successfully",
    dependencies=[Depends(require_permission("plans", "write"))]
)
async def delete_plan(
    plan_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Soft delete plan.
    
    Requires: plans:write permission
    """
    try:
        result = await plans_service.delete_plan(db, plan_id)
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Plan deleted successfully",
            data=result
        )
    except ResourceNotFoundError as e:
        logger.warning(f"Plan not found: {plan_id}")
        return error_json_response(
            status_code=e.status_code,
            message="Plan not found",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting plan: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to delete plan",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )

