"""
Wallets module schemas.

Pydantic models for request/response validation.
"""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field


# Enums
WalletType = Literal["cex", "dex", "perpetuals"]
FieldType = Literal["string", "password", "file"]


class AuthFieldSchema(BaseModel):
    """Auth field schema for wallet credential requirements."""
    key: str = Field(..., description="Field key (e.g., 'api_key', 'api_secret')")
    label: str = Field(..., description="Display label for UI")
    type: FieldType = Field(..., description="Field type")
    required: bool = Field(..., description="Whether field is required")
    encrypted: bool = Field(..., description="Whether field should be encrypted")
    placeholder: str = Field(..., description="Placeholder text for UI")
    help_text: str = Field(..., description="Help text for users")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "key": "api_key",
                "label": "API Key",
                "type": "string",
                "required": True,
                "encrypted": False,
                "placeholder": "Enter your API key",
                "help_text": "Find this in your account settings"
            }
        }
    }


class LeverageSchema(BaseModel):
    """Leverage configuration."""
    min: int = Field(..., ge=1, description="Minimum leverage")
    max: int = Field(..., ge=1, description="Maximum leverage")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "min": 1,
                "max": 125
            }
        }
    }


class FeaturesSchema(BaseModel):
    """Wallet features configuration."""
    spot: bool = Field(..., description="Supports spot trading")
    futures: bool = Field(..., description="Supports futures trading")
    perpetuals: bool = Field(..., description="Supports perpetuals trading")
    leverage: LeverageSchema = Field(..., description="Leverage limits")
    supported_assets: List[str] = Field(..., description="List of supported assets")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "spot": True,
                "futures": True,
                "perpetuals": True,
                "leverage": {"min": 1, "max": 125},
                "supported_assets": ["BTC", "ETH", "USDT"]
            }
        }
    }


class ApiConfigSchema(BaseModel):
    """API configuration for wallet."""
    base_url: str = Field(..., description="Base API URL")
    testnet_url: str = Field(..., description="Testnet API URL")
    websocket_url: str = Field(..., description="WebSocket URL")
    rate_limit: int = Field(..., ge=1, description="Rate limit (requests per minute)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "base_url": "https://api.binance.com",
                "testnet_url": "https://testnet.binance.vision",
                "websocket_url": "wss://stream.binance.com:9443",
                "rate_limit": 1200
            }
        }
    }


class CreateWalletDefinitionRequest(BaseModel):
    """Request schema for creating wallet definition."""
    name: str = Field(..., min_length=1, description="Wallet name")
    slug: str = Field(..., min_length=1, description="Unique slug identifier")
    type: WalletType = Field(..., description="Wallet type")
    description: str = Field(..., min_length=1, description="Wallet description")
    logo: Optional[str] = Field(None, description="Logo URL")
    auth_fields: List[AuthFieldSchema] = Field(default_factory=list, description="Required auth fields")
    features: FeaturesSchema = Field(..., description="Wallet features")
    api_config: ApiConfigSchema = Field(..., description="API configuration")
    is_active: bool = Field(default=True, description="Whether wallet is active")
    order: int = Field(..., ge=0, description="Display order")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Binance",
                "slug": "binance",
                "type": "cex",
                "description": "Leading cryptocurrency exchange",
                "auth_fields": [
                    {
                        "key": "api_key",
                        "label": "API Key",
                        "type": "string",
                        "required": True,
                        "encrypted": False,
                        "placeholder": "Enter your API key",
                        "help_text": "Find this in your account settings"
                    }
                ],
                "features": {
                    "spot": True,
                    "futures": True,
                    "perpetuals": True,
                    "leverage": {"min": 1, "max": 125},
                    "supported_assets": ["BTC", "ETH", "USDT"]
                },
                "api_config": {
                    "base_url": "https://api.binance.com",
                    "testnet_url": "https://testnet.binance.vision",
                    "websocket_url": "wss://stream.binance.com:9443",
                    "rate_limit": 1200
                },
                "is_active": True,
                "order": 1
            }
        }
    }


class UpdateWalletDefinitionRequest(BaseModel):
    """Request schema for updating wallet definition."""
    name: Optional[str] = Field(None, min_length=1, description="Wallet name")
    description: Optional[str] = Field(None, min_length=1, description="Wallet description")
    logo: Optional[str] = Field(None, description="Logo URL")
    auth_fields: Optional[List[AuthFieldSchema]] = Field(None, description="Required auth fields")
    features: Optional[FeaturesSchema] = Field(None, description="Wallet features")
    api_config: Optional[ApiConfigSchema] = Field(None, description="API configuration")
    is_active: Optional[bool] = Field(None, description="Whether wallet is active")
    order: Optional[int] = Field(None, ge=0, description="Display order")


class WalletDefinitionResponse(BaseModel):
    """Response schema for wallet definition."""
    id: str = Field(..., description="Wallet ID")
    name: str = Field(..., description="Wallet name")
    slug: str = Field(..., description="Unique slug")
    type: WalletType = Field(..., description="Wallet type")
    description: str = Field(..., description="Wallet description")
    logo: Optional[str] = Field(None, description="Logo URL")
    auth_fields: List[AuthFieldSchema] = Field(..., description="Required auth fields")
    features: FeaturesSchema = Field(..., description="Wallet features")
    api_config: ApiConfigSchema = Field(..., description="API configuration")
    is_active: bool = Field(..., description="Whether wallet is active")
    order: int = Field(..., description="Display order")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "name": "Binance",
                "slug": "binance",
                "type": "cex",
                "description": "Leading cryptocurrency exchange",
                "logo": None,
                "auth_fields": [],
                "features": {
                    "spot": True,
                    "futures": True,
                    "perpetuals": True,
                    "leverage": {"min": 1, "max": 125},
                    "supported_assets": ["BTC", "ETH", "USDT"]
                },
                "api_config": {
                    "base_url": "https://api.binance.com",
                    "testnet_url": "https://testnet.binance.vision",
                    "websocket_url": "wss://stream.binance.com:9443",
                    "rate_limit": 1200
                },
                "is_active": True,
                "order": 1,
                "created_at": "2025-01-08T10:30:00Z",
                "updated_at": "2025-01-08T10:30:00Z"
            }
        }
    }
