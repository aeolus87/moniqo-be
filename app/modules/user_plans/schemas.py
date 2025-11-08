"""
User_Plans Pydantic schemas.

DTOs for API request/response validation.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict
from datetime import datetime
from enum import Enum


class BillingCycle(str, Enum):
    """Billing cycle enumeration."""
    monthly = "monthly"
    yearly = "yearly"


class SubscriptionStatus(str, Enum):
    """Subscription status enumeration."""
    active = "active"
    expired = "expired"
    cancelled = "cancelled"
    trial = "trial"


class PaymentMethod(BaseModel):
    """Payment method schema."""
    type: str = Field(..., description="Payment type (e.g., 'card')")
    last4: str = Field(..., min_length=4, max_length=4, description="Last 4 digits of card")
    brand: str = Field(..., description="Card brand (e.g., 'visa', 'mastercard')")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "type": "card",
                "last4": "4242",
                "brand": "visa"
            }
        }
    }


class UserPlanCreate(BaseModel):
    """Schema for creating a user subscription."""
    plan_id: str = Field(..., description="Plan ID")
    billing_cycle: BillingCycle = Field(default=BillingCycle.monthly, description="Billing cycle")
    auto_renew: bool = Field(default=True, description="Auto-renew flag")
    payment_method: Optional[PaymentMethod] = Field(None, description="Payment method")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "plan_id": "507f1f77bcf86cd799439011",
                "billing_cycle": "monthly",
                "auto_renew": True,
                "payment_method": {
                    "type": "card",
                    "last4": "4242",
                    "brand": "visa"
                }
            }
        }
    }


class UserPlanUpdate(BaseModel):
    """Schema for updating a user subscription."""
    auto_renew: Optional[bool] = Field(None, description="Auto-renew flag")
    payment_method: Optional[PaymentMethod] = Field(None, description="Payment method")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "auto_renew": False,
                "payment_method": {
                    "type": "card",
                    "last4": "5555",
                    "brand": "mastercard"
                }
            }
        }
    }


class UserPlanResponse(BaseModel):
    """Schema for user subscription response."""
    id: str = Field(..., alias="_id", description="Subscription ID")
    user_id: str = Field(..., description="User ID")
    plan_id: str = Field(..., description="Plan ID")
    status: SubscriptionStatus = Field(..., description="Subscription status")
    start_date: datetime = Field(..., description="Start date")
    end_date: datetime = Field(..., description="End date")
    auto_renew: bool = Field(..., description="Auto-renew flag")
    billing_cycle: BillingCycle = Field(..., description="Billing cycle")
    payment_method: Optional[Dict] = Field(None, description="Payment method")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "user_id": "507f1f77bcf86cd799439012",
                "plan_id": "507f1f77bcf86cd799439013",
                "status": "active",
                "start_date": "2024-01-01T00:00:00",
                "end_date": "2024-02-01T00:00:00",
                "auto_renew": True,
                "billing_cycle": "monthly",
                "payment_method": {
                    "type": "card",
                    "last4": "4242",
                    "brand": "visa"
                },
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        }
    }

