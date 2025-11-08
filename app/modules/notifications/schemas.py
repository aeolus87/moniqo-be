"""
Notifications Pydantic schemas.

DTOs for API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class NotificationType(str, Enum):
    """Notification type enumeration."""
    info = "info"
    success = "success"
    warning = "warning"
    error = "error"


class NotificationCreate(BaseModel):
    """Schema for creating a notification."""
    type: NotificationType = Field(..., description="Notification type")
    title: str = Field(..., min_length=1, max_length=200, description="Notification title")
    message: str = Field(..., min_length=1, max_length=1000, description="Notification message")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "type": "info",
                "title": "Welcome!",
                "message": "Welcome to the platform!",
                "metadata": {
                    "source": "onboarding",
                    "action_url": "/dashboard"
                }
            }
        }
    }


class NotificationResponse(BaseModel):
    """Schema for notification response."""
    id: str = Field(..., alias="_id", description="Notification ID")
    user_id: str = Field(..., description="User ID")
    type: NotificationType = Field(..., description="Notification type")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    is_read: bool = Field(..., description="Read status")
    read_at: Optional[datetime] = Field(None, description="Read timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "user_id": "507f1f77bcf86cd799439012",
                "type": "info",
                "title": "Welcome!",
                "message": "Welcome to the platform!",
                "metadata": {"source": "onboarding"},
                "is_read": False,
                "read_at": None,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        }
    }


class UnreadCountResponse(BaseModel):
    """Schema for unread count response."""
    unread_count: int = Field(..., description="Number of unread notifications")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "unread_count": 5
            }
        }
    }


class MarkAllReadResponse(BaseModel):
    """Schema for mark all as read response."""
    marked_count: int = Field(..., description="Number of notifications marked as read")
    message: str = Field(..., description="Success message")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "marked_count": 10,
                "message": "All notifications marked as read"
            }
        }
    }

