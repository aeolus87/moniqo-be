"""
Wallets module router.

API endpoints for wallet definition operations.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import db_provider
from app.core.context import TradingMode
from app.core.dependencies import get_current_user, require_permission
from app.core.responses import success_response, error_response, paginated_response
from app.shared.exceptions import ValidationError, NotFoundError
from app.modules.wallets import service as wallet_service
from app.modules.wallets.schemas import (
    CreateWalletDefinitionRequest,
    UpdateWalletDefinitionRequest,
    WalletDefinitionResponse
)
from app.utils.pagination import get_pagination_params
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/wallets", tags=["Wallets"])


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
    "/definitions",
    status_code=status.HTTP_201_CREATED,
    response_description="Wallet definition created successfully",
    dependencies=[Depends(require_permission("wallets", "write"))]
)
async def create_wallet_definition(
    wallet_data: CreateWalletDefinitionRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db_for_mode(TradingMode.DEMO))
):
    """
    Create a new wallet definition.
    
    Requires admin permissions (wallets:write).
    
    Args:
        wallet_data: Wallet definition data
        current_user: Current authenticated user
        db: Database instance
        
    Returns:
        Standardized response with created wallet definition
    """
    try:
        from bson import ObjectId
        wallet = await wallet_service.create_wallet_definition(
            db,
            wallet_data,
            ObjectId(str(current_user["_id"]))
        )
        
        return success_response(
            status_code=status.HTTP_201_CREATED,
            message="Wallet definition created successfully",
            data=wallet.model_dump()
        )
        
    except ValidationError as e:
        logger.error(f"Validation error creating wallet: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Validation failed",
            error_code="VALIDATION_ERROR",
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating wallet definition: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to create wallet definition",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.get(
    "/definitions",
    status_code=status.HTTP_200_OK,
    response_description="Wallet definitions retrieved successfully"
)
async def list_wallet_definitions(
    type: Optional[str] = Query(None, description="Filter by wallet type (cex, dex, perpetuals)"),
    is_active: Optional[str] = Query(None, description="Filter by active status (true/false)"),
    limit: int = Query(100, ge=1, le=5000, description="Number of items per page"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db_for_mode(TradingMode.DEMO))
):
    """
    List all wallet definitions.
    
    Public endpoint - no authentication required.
    Supports filtering by type and is_active.
    
    Args:
        type: Filter by wallet type
        is_active: Filter by active status
        limit: Number of items per page
        offset: Number of items to skip
        db: Database instance
        
    Returns:
        Standardized paginated response with wallet definitions
    """
    try:
        filters = {}
        if type:
            filters["type"] = type
        if is_active is not None:
            filters["is_active"] = is_active
        
        wallets, total = await wallet_service.list_wallet_definitions(
            db,
            filters,
            limit=limit,
            offset=offset
        )
        
        wallet_dicts = [wallet.model_dump() for wallet in wallets]
        
        return paginated_response(
            status_code=status.HTTP_200_OK,
            message="Wallet definitions retrieved successfully",
            items=wallet_dicts,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error(f"Error listing wallet definitions: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to retrieve wallet definitions",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.get(
    "/definitions/{slug}",
    status_code=status.HTTP_200_OK,
    response_description="Wallet definition retrieved successfully"
)
async def get_wallet_definition(
    slug: str,
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db_for_mode(TradingMode.DEMO))
):
    """
    Get wallet definition by slug.
    
    Public endpoint - no authentication required.
    
    Args:
        slug: Wallet slug identifier
        db: Database instance
        
    Returns:
        Standardized response with wallet definition
    """
    try:
        wallet = await wallet_service.get_wallet_definition(db, slug)
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Wallet definition retrieved successfully",
            data=wallet.model_dump()
        )
        
    except NotFoundError as e:
        logger.error(f"Wallet not found: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Wallet not found",
            error_code="NOT_FOUND",
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting wallet definition: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to retrieve wallet definition",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.patch(
    "/definitions/{slug}",
    status_code=status.HTTP_200_OK,
    response_description="Wallet definition updated successfully",
    dependencies=[Depends(require_permission("wallets", "write"))]
)
async def update_wallet_definition(
    slug: str,
    update_data: UpdateWalletDefinitionRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db_for_mode(TradingMode.DEMO))
):
    """
    Update wallet definition.
    
    Requires admin permissions (wallets:write).
    
    Args:
        slug: Wallet slug identifier
        update_data: Update data
        current_user: Current authenticated user
        db: Database instance
        
    Returns:
        Standardized response with updated wallet definition
    """
    try:
        wallet = await wallet_service.update_wallet_definition(db, slug, update_data)
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Wallet definition updated successfully",
            data=wallet.model_dump()
        )
        
    except NotFoundError as e:
        logger.error(f"Wallet not found: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Wallet not found",
            error_code="NOT_FOUND",
            error_message=str(e)
        )
    except ValidationError as e:
        logger.error(f"Validation error updating wallet: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Validation failed",
            error_code="VALIDATION_ERROR",
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating wallet definition: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to update wallet definition",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.delete(
    "/definitions/{slug}",
    status_code=status.HTTP_200_OK,
    response_description="Wallet definition deleted successfully",
    dependencies=[Depends(require_permission("wallets", "write"))]
)
async def delete_wallet_definition(
    slug: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db_for_mode(TradingMode.DEMO))
):
    """
    Delete wallet definition (soft delete - sets is_active=False).
    
    Requires admin permissions (wallets:write).
    
    Args:
        slug: Wallet slug identifier
        current_user: Current authenticated user
        db: Database instance
        
    Returns:
        Standardized success response
    """
    try:
        await wallet_service.delete_wallet_definition(db, slug)
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Wallet definition deleted successfully",
            data=None
        )
        
    except NotFoundError as e:
        logger.error(f"Wallet not found: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Wallet not found",
            error_code="NOT_FOUND",
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting wallet definition: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to delete wallet definition",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )
