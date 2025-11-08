"""
Auth module schemas.

Pydantic models for request/response validation.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.utils.validators import (
    validate_password_strength,
    validate_email_lowercase,
    validate_phone_number,
    validate_birthday
)


class PhoneNumber(BaseModel):
    """Phone number model."""
    country_code: Optional[str] = Field(None, description="Country code (e.g., +63)")
    mobile_number: Optional[str] = Field(None, description="Mobile number")
    
    @field_validator("country_code", "mobile_number")
    @classmethod
    def validate_phone(cls, v, info):
        """Validate phone number fields together."""
        # This will be validated at the model level
        return v


class Birthday(BaseModel):
    """Birthday model."""
    day: int = Field(..., ge=1, le=31, description="Day of birth (1-31)")
    month: int = Field(..., ge=1, le=12, description="Month of birth (1-12)")
    year: int = Field(..., description="Year of birth")
    
    @field_validator("*", mode="after")
    @classmethod
    def validate_birthday_data(cls, v, info):
        """Validate birthday as a complete date."""
        return v


class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    first_name: str = Field(..., min_length=1, description="First name")
    last_name: str = Field(..., min_length=1, description="Last name")
    birthday: Birthday = Field(..., description="Date of birth")
    phone_number: Optional[PhoneNumber] = Field(None, description="Phone number")
    
    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Convert email to lowercase."""
        return validate_email_lowercase(v)
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        return validate_password_strength(v)
    
    @field_validator("birthday")
    @classmethod
    def check_birthday(cls, v: Birthday) -> Birthday:
        """Validate birthday."""
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
                "email": "user@example.com",
                "password": "SecurePassword123!",
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


class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")
    
    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Convert email to lowercase."""
        return validate_email_lowercase(v)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "password": "SecurePassword123!"
            }
        }
    }


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIs...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
                "token_type": "bearer"
            }
        }
    }


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str = Field(..., description="JWT refresh token")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
            }
        }
    }


class ForgotPasswordRequest(BaseModel):
    """Forgot password request."""
    email: EmailStr = Field(..., description="User email address")
    
    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Convert email to lowercase."""
        return validate_email_lowercase(v)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com"
            }
        }
    }


class ResetPasswordRequest(BaseModel):
    """Reset password request."""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password")
    
    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        return validate_password_strength(v)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIs...",
                "new_password": "NewSecurePassword123!"
            }
        }
    }


class UserResponse(BaseModel):
    """User response model (used after registration)."""
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    is_verified: bool = Field(..., description="Email verification status")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "email": "user@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "is_verified": False
            }
        }
    }

