"""
User Wallets - Pydantic Schemas

API request/response models for wallet endpoints.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator
from decimal import Decimal


# ==================== WALLET DEFINITION SCHEMAS ====================

class WalletDefinitionResponse(BaseModel):
    """Wallet provider definition response"""
    id: str = Field(..., description="Wallet definition ID")
    name: str = Field(..., description="Display name")
    slug: str = Field(..., description="Unique slug")
    description: Optional[str] = Field(None, description="Description")
    logo_url: Optional[str] = Field(None, description="Logo URL")
    integration_type: str = Field(..., description="Integration type")
    is_demo: bool = Field(..., description="Is demo wallet?")
    is_active: bool = Field(..., description="Is active?")
    required_credentials: List[str] = Field(default_factory=list, description="Required credential fields")
    supported_symbols: List[str] = Field(default_factory=list, description="Supported symbols")
    supported_order_types: List[str] = Field(default_factory=list, description="Supported order types")
    supports_margin: bool = Field(default=False, description="Supports margin?")
    supports_futures: bool = Field(default=False, description="Supports futures?")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Update timestamp")
    
    class Config:
        from_attributes = True


class WalletDefinitionListResponse(BaseModel):
    """List of wallet definitions"""
    wallets: List[WalletDefinitionResponse]
    total: int


# ==================== USER WALLET SCHEMAS ====================

class CreateUserWalletRequest(BaseModel):
    """Request to create user wallet"""
    wallet_provider_id: str = Field(..., description="Wallet provider ID")
    custom_name: str = Field(..., min_length=1, max_length=100, description="Custom name")
    credentials: Dict[str, str] = Field(..., description="Wallet credentials (will be encrypted)")
    risk_limits: Optional[Dict[str, float]] = Field(
        None,
        description="Risk limits (optional)"
    )
    
    @validator("custom_name")
    def validate_custom_name(cls, v):
        """Validate custom name"""
        if not v.strip():
            raise ValueError("Custom name cannot be empty")
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "wallet_provider_id": "507f1f77bcf86cd799439011",
                "custom_name": "My Binance Main",
                "credentials": {
                    "api_key": "your_api_key_here",
                    "api_secret": "your_api_secret_here"
                },
                "risk_limits": {
                    "max_position_size_usd": 1000.0,
                    "daily_loss_limit": 100.0,
                    "stop_loss_default_percent": 0.02
                }
            }
        }


class UpdateUserWalletRequest(BaseModel):
    """Request to update user wallet"""
    custom_name: Optional[str] = Field(None, min_length=1, max_length=100)
    credentials: Optional[Dict[str, str]] = Field(None, description="Updated credentials")
    is_active: Optional[bool] = Field(None)
    risk_limits: Optional[Dict[str, float]] = Field(None)


class UserWalletResponse(BaseModel):
    """User wallet response"""
    id: str = Field(..., description="User wallet ID")
    user_id: str
    wallet_provider_id: str
    wallet_provider_name: Optional[str] = Field(None, description="Provider name (populated)")
    custom_name: str
    is_active: bool
    connection_status: str
    last_connection_test: Optional[datetime]
    last_connection_error: Optional[str]
    balance: Dict[str, float] = Field(..., description="Current balances")
    balance_last_synced: Optional[datetime]
    risk_limits: Dict[str, Any]
    total_trades: int
    total_pnl: float
    last_trade_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    # Note: credentials are NEVER returned in responses
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "user_id": "507f1f77bcf86cd799439012",
                "wallet_provider_id": "507f1f77bcf86cd799439013",
                "wallet_provider_name": "Binance",
                "custom_name": "My Binance Main",
                "is_active": True,
                "connection_status": "connected",
                "last_connection_test": "2025-11-22T10:30:00Z",
                "last_connection_error": None,
                "balance": {
                    "USDT": 1000.00,
                    "BTC": 0.5
                },
                "balance_last_synced": "2025-11-22T10:30:00Z",
                "risk_limits": {
                    "max_position_size_usd": 1000.00,
                    "daily_loss_limit": 100.00,
                    "stop_loss_default_percent": 0.02
                },
                "total_trades": 42,
                "total_pnl": 125.50,
                "last_trade_at": "2025-11-22T09:15:00Z",
                "created_at": "2025-11-20T08:00:00Z",
                "updated_at": "2025-11-22T10:30:00Z"
            }
        }


class UserWalletListResponse(BaseModel):
    """List of user wallets"""
    wallets: List[UserWalletResponse]
    total: int


# ==================== WALLET OPERATIONS ====================

class ConnectionTestRequest(BaseModel):
    """Request to test wallet connection"""
    # No body needed - uses existing credentials


class ConnectionTestResponse(BaseModel):
    """Connection test result"""
    success: bool
    latency_ms: int
    server_time: datetime
    message: str
    error: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "latency_ms": 234,
                "server_time": "2025-11-22T10:30:00Z",
                "message": "Connection successful",
                "error": None
            }
        }


class SyncBalanceRequest(BaseModel):
    """Request to sync wallet balance"""
    # No body needed - syncs from exchange


class SyncBalanceResponse(BaseModel):
    """Balance sync result"""
    success: bool
    balances: Dict[str, float]
    sync_duration_ms: int
    synced_at: datetime
    changes: Optional[Dict[str, float]] = Field(
        None,
        description="Balance changes since last sync"
    )
    error: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "balances": {
                    "USDT": 1000.00,
                    "BTC": 0.5,
                    "ETH": 2.0
                },
                "sync_duration_ms": 456,
                "synced_at": "2025-11-22T10:30:00Z",
                "changes": {
                    "BTC": 0.1,
                    "ETH": -0.5
                },
                "error": None
            }
        }


# ==================== TRADING OPERATIONS (Wallet-level) ====================

class PlaceOrderRequest(BaseModel):
    """Request to place order through wallet"""
    symbol: str = Field(..., description="Trading pair (e.g., BTC/USDT)")
    side: str = Field(..., description="buy or sell")
    order_type: str = Field(..., description="market, limit, stop_loss, take_profit")
    quantity: float = Field(..., gt=0, description="Order quantity")
    price: Optional[float] = Field(None, description="Limit price (required for limit orders)")
    stop_price: Optional[float] = Field(None, description="Stop price (for stop orders)")
    time_in_force: str = Field(default="GTC", description="GTC, IOC, FOK")
    
    @validator("side")
    def validate_side(cls, v):
        """Validate order side"""
        if v.lower() not in ["buy", "sell"]:
            raise ValueError("Side must be 'buy' or 'sell'")
        return v.lower()
    
    @validator("order_type")
    def validate_order_type(cls, v):
        """Validate order type"""
        valid_types = ["market", "limit", "stop_loss", "take_profit"]
        if v.lower() not in valid_types:
            raise ValueError(f"Order type must be one of: {valid_types}")
        return v.lower()
    
    @validator("time_in_force")
    def validate_tif(cls, v):
        """Validate time in force"""
        valid_tif = ["GTC", "IOC", "FOK", "GTD"]
        if v.upper() not in valid_tif:
            raise ValueError(f"Time in force must be one of: {valid_tif}")
        return v.upper()
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "BTC/USDT",
                "side": "buy",
                "order_type": "market",
                "quantity": 0.1,
                "price": None,
                "stop_price": None,
                "time_in_force": "GTC"
            }
        }


class PlaceOrderResponse(BaseModel):
    """Order placement result"""
    success: bool
    order_id: str
    client_order_id: str
    status: str
    filled_quantity: float
    average_price: Optional[float]
    fee: Optional[float]
    fee_currency: Optional[str]
    timestamp: datetime
    error: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "order_id": "binance_12345678",
                "client_order_id": "client_abc123",
                "status": "filled",
                "filled_quantity": 0.1,
                "average_price": 50000.00,
                "fee": 5.00,
                "fee_currency": "USDT",
                "timestamp": "2025-11-22T10:30:00Z",
                "error": None
            }
        }


class CancelOrderRequest(BaseModel):
    """Request to cancel order"""
    order_id: str = Field(..., description="Exchange order ID")
    symbol: str = Field(..., description="Trading pair")


class CancelOrderResponse(BaseModel):
    """Order cancellation result"""
    success: bool
    order_id: str
    status: str
    message: str
    error: Optional[str] = None


class GetOrderStatusRequest(BaseModel):
    """Request to get order status"""
    order_id: str
    symbol: str


class OrderStatusResponse(BaseModel):
    """Order status result"""
    order_id: str
    status: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    filled_quantity: float
    remaining_quantity: float
    average_price: Optional[float]
    created_at: datetime
    updated_at: datetime


class GetBalanceRequest(BaseModel):
    """Request to get specific balance"""
    asset: str = Field(..., description="Asset symbol (e.g., USDT, BTC)")


class GetBalanceResponse(BaseModel):
    """Balance response"""
    asset: str
    balance: float
    locked: Optional[float] = Field(None, description="Locked balance (in orders)")
    available: float


class GetMarketPriceRequest(BaseModel):
    """Request to get market price"""
    symbol: str = Field(..., description="Trading pair")


class GetMarketPriceResponse(BaseModel):
    """Market price response"""
    symbol: str
    price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    timestamp: datetime


# ==================== WALLET SYNC LOG ====================

class WalletSyncLogResponse(BaseModel):
    """Wallet sync log entry"""
    id: str
    user_wallet_id: str
    status: str
    balance_snapshot: Optional[Dict[str, float]]
    balance_changes: Optional[Dict[str, float]]
    sync_duration_ms: Optional[int]
    error_message: Optional[str]
    error_code: Optional[str]
    retry_count: int
    synced_at: datetime
    triggered_by: str
    
    class Config:
        from_attributes = True


class WalletSyncLogListResponse(BaseModel):
    """List of sync log entries"""
    logs: List[WalletSyncLogResponse]
    total: int


# ==================== ERROR RESPONSES ====================

class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = False
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "Insufficient funds",
                "error_code": "INSUFFICIENT_FUNDS",
                "details": {
                    "required": 1000.00,
                    "available": 500.00
                }
            }
        }


# ==================== DEMO WALLET SPECIFIC ====================

class DemoWalletStateResponse(BaseModel):
    """Demo wallet state response"""
    user_wallet_id: str
    cash_balances: Dict[str, float]
    asset_balances: Dict[str, float]
    locked_balances: Dict[str, float]
    open_orders_count: int
    transaction_count: int
    starting_balance: float
    total_realized_pnl: float
    total_fees_paid: float
    total_trades: int
    fee_rate: float
    slippage_rate: float
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ResetDemoWalletRequest(BaseModel):
    """Request to reset demo wallet"""
    initial_balance: Optional[Dict[str, float]] = Field(
        None,
        description="Reset to this balance (default: {\"USDT\": 10000})"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "initial_balance": {
                    "USDT": 10000.00
                }
            }
        }


class ResetDemoWalletResponse(BaseModel):
    """Demo wallet reset result"""
    success: bool
    message: str


class AddBalanceRequest(BaseModel):
    """Request to add balance to demo wallet"""
    asset: str = Field(..., description="Asset symbol (e.g., 'USDT', 'BTC')")
    amount: float = Field(..., gt=0, description="Amount to add")
    is_cash: bool = Field(True, description="Is this a cash currency (USDT, USD) or asset (BTC, ETH)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "asset": "USDT",
                "amount": 1000.0,
                "is_cash": True
            }
        }


class AddBalanceResponse(BaseModel):
    """Add balance result"""
    success: bool
    asset: str
    amount_added: float
    new_balance: float
    previous_balance: float
