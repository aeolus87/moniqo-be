"""
Permissions module schemas.

Pydantic models for request/response validation.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class PermissionCreate(BaseModel):
    """Schema for creating a permission."""
    
    resource: str = Field(..., min_length=1, max_length=50, description="Resource name (e.g., 'users', 'plans')")
    action: str = Field(..., min_length=1, max_length=50, description="Action name (e.g., 'read', 'write', 'delete')")
    description: str = Field(..., min_length=1, max_length=500, description="Permission description")
    
    @field_validator("resource", "action")
    @classmethod
    def validate_lowercase_alphanumeric(cls, v: str) -> str:
        """Validate that resource and action are lowercase alphanumeric with underscores."""
        if not v.replace("_", "").isalnum():
            raise ValueError("Must contain only alphanumeric characters and underscores")
        return v.lower()
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "resource": "agents",
                "action": "read",
                "description": "Permission to read agent data"
            }
        }
    }


class PermissionUpdate(BaseModel):
    """Schema for updating a permission."""
    
    description: Optional[str] = Field(None, min_length=1, max_length=500, description="Permission description")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "description": "Updated permission description"
            }
        }
    }


class PermissionResponse(BaseModel):
    """Schema for permission response."""
    
    id: str = Field(..., alias="_id", description="Permission ID")
    resource: str = Field(..., description="Resource name")
    action: str = Field(..., description="Action name")
    description: str = Field(..., description="Permission description")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "resource": "agents",
                "action": "read",
                "description": "Permission to read agent data",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        }
    }

