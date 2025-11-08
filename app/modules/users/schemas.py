"""
Users module schemas.

Pydantic models for request/response validation.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator
from app.utils.validators import (
    validate_phone_number,
    validate_birthday,
    validate_non_empty_string
)


class PhoneNumber(BaseModel):
    """Phone number model."""
    country_code: Optional[str] = Field(None, description="Country code (e.g., +63)")
    mobile_number: Optional[str] = Field(None, description="Mobile number")


class Birthday(BaseModel):
    """Birthday model."""
    day: int = Field(..., ge=1, le=31, description="Day of birth (1-31)")
    month: int = Field(..., ge=1, le=12, description="Month of birth (1-12)")
    year: int = Field(..., description="Year of birth")


class UserUpdate(BaseModel):
    """User update request."""
    first_name: Optional[str] = Field(None, min_length=1, description="First name")
    last_name: Optional[str] = Field(None, min_length=1, description="Last name")
    birthday: Optional[Birthday] = Field(None, description="Date of birth")
    phone_number: Optional[PhoneNumber] = Field(None, description="Phone number")
    
    @field_validator("first_name", "last_name")
    @classmethod
    def validate_names(cls, v: Optional[str]) -> Optional[str]:
        """Validate name is not empty or whitespace."""
        if v is not None:
            return validate_non_empty_string(v, "Name")
        return v
    
    @field_validator("birthday")
    @classmethod
    def check_birthday(cls, v: Optional[Birthday]) -> Optional[Birthday]:
        """Validate birthday."""
        if v is not None:
            birthday_dict = {
                "day": v.day,
                "month": v.month,
                "year": v.year
            }
            validate_birthday(birthday_dict)
        return v
    
    @field_validator("phone_number")
    @classmethod
    def check_phone_number(cls, v: Optional[PhoneNumber]) -> Optional[PhoneNumber]:
        """Validate phone number."""
        if v is not None:
            phone_dict = {
                "country_code": v.country_code,
                "mobile_number": v.mobile_number
            }
            validate_phone_number(phone_dict)
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "first_name": "John",
                "last_name": "Doe",
                "birthday": {
                    "day": 15,
                    "month": 6,
                    "year": 1990
                },
                "phone_number": {
                    "country_code": "+63",
                    "mobile_number": "9171234567"
                }
            }
        }
    }


class UserResponse(BaseModel):
    """User response model."""
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    birthday: Birthday = Field(..., description="Date of birth")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    phone_number: Optional[PhoneNumber] = Field(None, description="Phone number")
    user_role: Optional[str] = Field(None, description="User role ID")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "email": "user@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "birthday": {
                    "day": 15,
                    "month": 6,
                    "year": 1990
                },
                "avatar_url": "https://example.com/avatar.jpg",
                "phone_number": {
                    "country_code": "+63",
                    "mobile_number": "9171234567"
                },
                "user_role": "507f1f77bcf86cd799439012",
                "created_at": "2025-11-02T10:30:00Z",
                "updated_at": "2025-11-02T10:30:00Z"
            }
        }
    }


class UserListResponse(BaseModel):
    """User list response (minimal info)."""
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    created_at: str = Field(..., description="Creation timestamp")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "email": "user@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "avatar_url": "https://example.com/avatar.jpg",
                "created_at": "2025-11-02T10:30:00Z"
            }
        }
    }

