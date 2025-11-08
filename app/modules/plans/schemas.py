"""
Plans Pydantic schemas.

DTOs for API request/response validation.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime


class PlanFeature(BaseModel):
    """Plan feature schema."""
    
    resource: str = Field(..., min_length=1, max_length=100, description="Feature resource")
    title: str = Field(..., min_length=1, max_length=200, description="Feature title")
    description: str = Field(..., min_length=1, max_length=500, description="Feature description")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "resource": "api_calls",
                "title": "Unlimited API Calls",
                "description": "No limits on API requests"
            }
        }
    }


class PlanLimit(BaseModel):
    """Plan limit schema."""
    
    resource: str = Field(..., min_length=1, max_length=100, description="Limit resource")
    title: str = Field(..., min_length=1, max_length=200, description="Limit title")
    description: str = Field(..., min_length=1, max_length=500, description="Limit description")
    value: int = Field(..., ge=0, description="Limit value")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "resource": "trades_per_day",
                "title": "Daily Trades",
                "description": "Maximum trades per day",
                "value": 100
            }
        }
    }


class PlanCreate(BaseModel):
    """Schema for creating a new plan."""
    
    name: str = Field(..., min_length=1, max_length=100, description="Plan name")
    description: str = Field(..., min_length=1, max_length=1000, description="Plan description")
    price: float = Field(..., ge=0, description="Monthly price (0 for free)")
    features: List[PlanFeature] = Field(default_factory=list, description="Plan features")
    limits: List[PlanLimit] = Field(default_factory=list, description="Plan limits")
    
    @field_validator("price", mode="before")
    @classmethod
    def validate_price(cls, v):
        """Ensure price is non-negative."""
        if v < 0:
            raise ValueError("Price must be non-negative")
        return round(float(v), 2)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Pro Plan",
                "description": "Professional tier with advanced features",
                "price": 29.99,
                "features": [
                    {
                        "resource": "api_calls",
                        "title": "Unlimited API Calls",
                        "description": "No limits on API requests"
                    }
                ],
                "limits": [
                    {
                        "resource": "trades_per_day",
                        "title": "Daily Trades",
                        "description": "Maximum trades per day",
                        "value": 100
                    }
                ]
            }
        }
    }


class PlanUpdate(BaseModel):
    """Schema for updating a plan."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Plan name")
    description: Optional[str] = Field(None, min_length=1, max_length=1000, description="Plan description")
    price: Optional[float] = Field(None, ge=0, description="Monthly price")
    features: Optional[List[PlanFeature]] = Field(None, description="Plan features")
    limits: Optional[List[PlanLimit]] = Field(None, description="Plan limits")
    
    @field_validator("price", mode="before")
    @classmethod
    def validate_price(cls, v):
        """Ensure price is non-negative."""
        if v is not None and v < 0:
            raise ValueError("Price must be non-negative")
        return round(float(v), 2) if v is not None else v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "price": 34.99,
                "description": "Updated professional tier description"
            }
        }
    }


class PlanResponse(BaseModel):
    """Schema for plan response."""
    
    id: str = Field(..., alias="_id", description="Plan ID")
    name: str = Field(..., description="Plan name")
    description: str = Field(..., description="Plan description")
    price: float = Field(..., description="Monthly price")
    features: List[PlanFeature] = Field(..., description="Plan features")
    limits: List[PlanLimit] = Field(..., description="Plan limits")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "name": "Pro Plan",
                "description": "Professional tier",
                "price": 29.99,
                "features": [],
                "limits": [],
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        }
    }

