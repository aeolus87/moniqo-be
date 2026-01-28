"""
Credentials module router.

API endpoints for credential operations.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.config.database import get_database
from app.core.dependencies import get_current_user, validate_object_id
from app.core.responses import success_response, error_response, paginated_response
from app.core.exceptions import ValidationError, NotFoundError
from app.modules.credentials import service as credential_service
from app.modules.credentials.schemas import (
    CreateCredentialsRequest,
    UpdateCredentialsRequest,
    CredentialsResponse,
    ConnectionTestResponse
)
from app.utils.pagination import get_pagination_params
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/wallets/credentials", tags=["Credentials"])


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
    "/",
    status_code=status.HTTP_201_CREATED,
    response_description="Credentials created successfully"
)
async def create_credentials(
    credentials_data: CreateCredentialsRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create new wallet credentials.
    
    Requires authentication. Credentials are encrypted based on wallet auth_fields.
    
    Args:
        credentials_data: Credentials creation data
        current_user: Current authenticated user
        db: Database instance
        
    Returns:
        Standardized response with created credentials (without secrets)
    """
    try:
        from bson import ObjectId
        credentials = await credential_service.create_user_credentials(
            db,
            ObjectId(str(current_user["_id"])),
            credentials_data
        )
        
        return success_response(
            status_code=status.HTTP_201_CREATED,
            message="Credentials created successfully",
            data=credentials.model_dump()
        )
        
    except NotFoundError as e:
        logger.error(f"Not found error creating credentials: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Resource not found",
            error_code="NOT_FOUND",
            error_message=str(e)
        )
    except ValidationError as e:
        logger.error(f"Validation error creating credentials: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Validation failed",
            error_code="VALIDATION_ERROR",
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating credentials: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to create credentials",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_description="Credentials retrieved successfully"
)
async def list_credentials(
    wallet_id: Optional[str] = Query(None, description="Filter by wallet ID"),
    is_active: Optional[str] = Query(None, description="Filter by active status"),
    limit: int = Query(100, ge=1, le=5000, description="Number of items per page"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    List user's credentials.
    
    Requires authentication. Returns only current user's credentials.
    
    Args:
        wallet_id: Optional filter by wallet ID
        is_active: Optional filter by active status
        limit: Number of items per page
        offset: Number of items to skip
        current_user: Current authenticated user
        db: Database instance
        
    Returns:
        Standardized paginated response with credentials (without secrets)
    """
    try:
        from bson import ObjectId
        filters = {}
        if wallet_id:
            filters["wallet_id"] = wallet_id
        if is_active is not None:
            filters["is_active"] = is_active
        
        credentials, total = await credential_service.list_user_credentials(
            db,
            ObjectId(str(current_user["_id"])),
            filters,
            limit=limit,
            offset=offset
        )
        
        credential_dicts = [cred.model_dump() for cred in credentials]
        
        return paginated_response(
            status_code=status.HTTP_200_OK,
            message="Credentials retrieved successfully",
            items=credential_dicts,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error(f"Error listing credentials: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to retrieve credentials",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.get(
    "/{credentials_id}",
    status_code=status.HTTP_200_OK,
    response_description="Credential retrieved successfully"
)
async def get_credentials(
    credentials_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get credential details by ID.
    
    Requires authentication. Users can only access their own credentials.
    
    Args:
        credentials_id: Credentials ID (validated as ObjectId)
        current_user: Current authenticated user
        db: Database instance
        
    Returns:
        Standardized response with credential data (without secrets)
    """
    validate_object_id(credentials_id)
    try:
        from bson import ObjectId
        
        credentials = await credential_service.get_user_credentials(
            db,
            ObjectId(str(current_user["_id"])),
            credentials_id
        )
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Credential retrieved successfully",
            data=credentials.model_dump()
        )
        
    except NotFoundError as e:
        logger.error(f"Credential not found: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Credential not found",
            error_code="NOT_FOUND",
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting credential: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to retrieve credential",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.patch(
    "/{credentials_id}",
    status_code=status.HTTP_200_OK,
    response_description="Credential updated successfully"
)
async def update_credentials(
    credentials_id: str,
    update_data: UpdateCredentialsRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update credentials.
    
    Requires authentication. Users can only update their own credentials.
    If credentials are updated, they are re-encrypted.
    
    Args:
        credentials_id: Credentials ID (validated as ObjectId)
        update_data: Update data
        current_user: Current authenticated user
        db: Database instance
        
    Returns:
        Standardized response with updated credential (without secrets)
    """
    validate_object_id(credentials_id)
    try:
        from bson import ObjectId
        
        credentials = await credential_service.update_user_credentials(
            db,
            ObjectId(str(current_user["_id"])),
            credentials_id,
            update_data
        )
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Credential updated successfully",
            data=credentials.model_dump()
        )
        
    except NotFoundError as e:
        logger.error(f"Credential not found: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Credential not found",
            error_code="NOT_FOUND",
            error_message=str(e)
        )
    except ValidationError as e:
        logger.error(f"Validation error updating credential: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Validation failed",
            error_code="VALIDATION_ERROR",
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating credential: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to update credential",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.delete(
    "/{credentials_id}",
    status_code=status.HTTP_200_OK,
    response_description="Credential deleted successfully"
)
async def delete_credentials(
    credentials_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete credentials (soft delete).
    
    Requires authentication. Users can only delete their own credentials.
    
    Args:
        credentials_id: Credentials ID (validated as ObjectId)
        current_user: Current authenticated user
        db: Database instance
        
    Returns:
        Standardized success response
    """
    validate_object_id(credentials_id)
    try:
        from bson import ObjectId
        
        await credential_service.delete_user_credentials(
            db,
            ObjectId(str(current_user["_id"])),
            credentials_id
        )
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Credential deleted successfully",
            data=None
        )
        
    except NotFoundError as e:
        logger.error(f"Credential not found: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Credential not found",
            error_code="NOT_FOUND",
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting credential: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to delete credential",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.post(
    "/{credentials_id}/test",
    status_code=status.HTTP_200_OK,
    response_description="Connection test completed"
)
async def test_connection(
    credentials_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Test connection with credentials.
    
    Requires authentication. Users can only test their own credentials.
    Decrypts credentials and attempts to connect to exchange API.
    
    Args:
        credentials_id: Credentials ID (validated as ObjectId)
        current_user: Current authenticated user
        db: Database instance
        
    Returns:
        Standardized response with connection test result
    """
    validate_object_id(credentials_id)
    try:
        from bson import ObjectId
        
        test_result = await credential_service.test_connection(
            db,
            ObjectId(str(current_user["_id"])),
            credentials_id
        )
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Connection test completed",
            data=test_result.model_dump()
        )
        
    except NotFoundError as e:
        logger.error(f"Credential not found: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Credential not found",
            error_code="NOT_FOUND",
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Error testing connection: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to test connection",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )
