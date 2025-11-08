"""
Roles module schemas.

Pydantic models for request/response validation.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class RoleCreate(BaseModel):
    """Schema for creating a role."""
    
    name: str = Field(..., min_length=1, max_length=100, description="Role name (e.g., 'Admin', 'User')")
    description: str = Field(..., min_length=1, max_length=500, description="Role description")
    permissions: List[str] = Field(default=[], description="List of permission IDs")
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that role name is properly formatted."""
        v = v.strip()
        if not v:
            raise ValueError("Role name cannot be empty")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Content Manager",
                "description": "Can manage all content",
                "permissions": ["507f1f77bcf86cd799439011", "507f1f77bcf86cd799439012"]
            }
        }
    }


class RoleUpdate(BaseModel):
    """Schema for updating a role."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Role name")
    description: Optional[str] = Field(None, min_length=1, max_length=500, description="Role description")
    permissions: Optional[List[str]] = Field(None, description="List of permission IDs")
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate that role name is properly formatted."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Role name cannot be empty")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "description": "Updated role description",
                "permissions": ["507f1f77bcf86cd799439011"]
            }
        }
    }


class RoleResponse(BaseModel):
    """Schema for role response."""
    
    id: str = Field(..., alias="_id", description="Role ID")
    name: str = Field(..., description="Role name")
    description: str = Field(..., description="Role description")
    permissions: List[str] = Field(..., description="List of permission IDs")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "name": "Admin",
                "description": "Full system access",
                "permissions": ["507f1f77bcf86cd799439012", "507f1f77bcf86cd799439013"],
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        }
    }

