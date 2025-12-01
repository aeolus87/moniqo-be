"""
Credentials module schemas.

Pydantic models for request/response validation.
"""

from typing import Optional, List, Literal, Dict
from pydantic import BaseModel, Field
from datetime import datetime


Environment = Literal["mainnet", "testnet"]


class CreateCredentialsRequest(BaseModel):
    """Request schema for creating credentials."""
    wallet_id: str = Field(..., description="Wallet definition ID")
    name: str = Field(..., min_length=1, description="User-friendly name for credentials")
    credentials: Dict[str, str] = Field(..., description="Credential values (keys match wallet auth_fields)")
    environment: Environment = Field(..., description="Environment (mainnet or testnet)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "wallet_id": "507f1f77bcf86cd799439011",
                "name": "My Main Binance",
                "credentials": {
                    "api_key": "your_api_key_here",
                    "api_secret": "your_api_secret_here"
                },
                "environment": "testnet"
            }
        }
    }


class UpdateCredentialsRequest(BaseModel):
    """Request schema for updating credentials."""
    name: Optional[str] = Field(None, min_length=1, description="User-friendly name")
    credentials: Optional[Dict[str, str]] = Field(None, description="Updated credential values")
    environment: Optional[Environment] = Field(None, description="Environment")
    is_active: Optional[bool] = Field(None, description="Active status")


class CredentialsResponse(BaseModel):
    """Response schema for credentials (without secrets)."""
    id: str = Field(..., description="Credentials ID")
    wallet_id: str = Field(..., description="Wallet definition ID")
    name: str = Field(..., description="User-friendly name")
    is_connected: bool = Field(..., description="Connection status")
    last_verified_at: Optional[str] = Field(None, description="Last successful connection timestamp")
    connection_error: Optional[str] = Field(None, description="Latest connection error")
    environment: Environment = Field(..., description="Environment")
    is_active: bool = Field(..., description="Active status")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "wallet_id": "507f1f77bcf86cd799439012",
                "name": "My Main Binance",
                "is_connected": True,
                "last_verified_at": "2025-01-08T10:30:00Z",
                "connection_error": None,
                "environment": "testnet",
                "is_active": True,
                "created_at": "2025-01-08T10:30:00Z",
                "updated_at": "2025-01-08T10:30:00Z"
            }
        }
    }


class ConnectionTestResponse(BaseModel):
    """Response schema for connection test."""
    success: bool = Field(..., description="Whether connection test succeeded")
    message: str = Field(..., description="Test result message")
    is_connected: bool = Field(..., description="Updated connection status")
    last_verified_at: Optional[str] = Field(None, description="Verification timestamp")
    connection_error: Optional[str] = Field(None, description="Error message if failed")
