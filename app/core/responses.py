"""
Standardized response models for API endpoints.

All API responses follow a consistent format for success and error cases.
"""

from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    """
    Error detail model for error responses.
    
    Attributes:
        code: Error code (e.g., "VALIDATION_ERROR", "NOT_FOUND")
        message: Detailed error message
    """
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Detailed error message")


class StandardResponse(BaseModel):
    """
    Standard API response format.
    
    All API endpoints return this format for consistency.
    
    Attributes:
        status_code: HTTP status code
        message: Human-readable message
        data: Response data (null on error)
        error: Error details (null on success)
    """
    status_code: int = Field(..., description="HTTP status code")
    message: str = Field(..., description="Human-readable message")
    data: Optional[Any] = Field(default=None, description="Response data")
    error: Optional[ErrorDetail] = Field(default=None, description="Error details")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status_code": 200,
                "message": "Operation successful",
                "data": {"id": "123", "name": "Example"},
                "error": None
            }
        }
    )


def success_response(
    status_code: int,
    message: str,
    data: Any = None
) -> dict:
    """
    Create a success response.
    
    Args:
        status_code: HTTP status code (200, 201, etc.)
        message: Success message
        data: Response data
        
    Returns:
        dict: Standardized success response
        
    Example:
        >>> success_response(201, "User created", {"id": "123", "email": "user@example.com"})
        {
            "status_code": 201,
            "message": "User created",
            "data": {"id": "123", "email": "user@example.com"},
            "error": None
        }
    """
    return {
        "status_code": status_code,
        "message": message,
        "data": data,
        "error": None
    }


def error_response(
    status_code: int,
    message: str,
    error_code: str,
    error_message: str
) -> dict:
    """
    Create an error response.
    
    Args:
        status_code: HTTP status code (400, 401, 403, 404, etc.)
        message: General error message
        error_code: Specific error code
        error_message: Detailed error message
        
    Returns:
        dict: Standardized error response
        
    Example:
        >>> error_response(400, "Validation failed", "DUPLICATE_EMAIL", "Email already exists")
        {
            "status_code": 400,
            "message": "Validation failed",
            "data": None,
            "error": {
                "code": "DUPLICATE_EMAIL",
                "message": "Email already exists"
            }
        }
    """
    return {
        "status_code": status_code,
        "message": message,
        "data": None,
        "error": {
            "code": error_code,
            "message": error_message
        }
    }


class PaginatedResponse(BaseModel):
    """
    Paginated response model.
    
    Used for list endpoints with pagination support.
    
    Attributes:
        items: List of items
        total: Total number of items
        limit: Items per page
        offset: Current offset
        has_more: Whether there are more items
    """
    items: list = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    limit: int = Field(..., description="Items per page")
    offset: int = Field(..., description="Current offset")
    has_more: bool = Field(..., description="Whether there are more items")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [{"id": "1", "name": "Item 1"}],
                "total": 150,
                "limit": 10,
                "offset": 0,
                "has_more": True
            }
        }
    )


def paginated_response(
    status_code: int,
    message: str,
    items: list,
    total: int,
    limit: int,
    offset: int
) -> dict:
    """
    Create a paginated response.
    
    Args:
        status_code: HTTP status code
        message: Success message
        items: List of items for current page
        total: Total number of items
        limit: Items per page
        offset: Current offset
        
    Returns:
        dict: Standardized paginated response
        
    Example:
        >>> paginated_response(200, "Users retrieved", [...], 150, 10, 0)
        {
            "status_code": 200,
            "message": "Users retrieved",
            "data": {
                "items": [...],
                "total": 150,
                "limit": 10,
                "offset": 0,
                "has_more": True
            },
            "error": None
        }
    """
    has_more = (offset + limit) < total
    
    return {
        "status_code": status_code,
        "message": message,
        "data": {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": has_more
        },
        "error": None
    }

