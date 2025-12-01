"""
Wallet Models - Database Schema Definitions

This module defines the MongoDB schema for wallet-related collections:
- wallets: Wallet provider definitions (Binance, Coinbase, Demo, etc.)
- user_wallets: User-specific wallet connections
- wallet_sync_log: Balance sync history
- demo_wallet_state: Demo wallet simulation data

These models work with Motor (async MongoDB driver).

Author: Moniqo Team
Last Updated: 2025-11-22
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum
from bson import ObjectId
from pydantic import BaseModel, Field


class IntegrationType(str, Enum):
    """Wallet integration types"""
    CEX = "cex"           # Centralized Exchange (Binance, Coinbase)
    DEX = "dex"           # Decentralized Exchange (Uniswap, PancakeSwap)
    SIMULATION = "simulation"  # Demo/Paper trading


class WalletStatus(str, Enum):
    """Wallet status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    DEPRECATED = "deprecated"


class UserWalletStatus(str, Enum):
    """User wallet connection status"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    TESTING = "testing"


class SyncStatus(str, Enum):
    """Balance sync status"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


# ==================== WALLET DEFINITION ====================

class WalletDefinition(BaseModel):
    """
    Wallet Provider Definition
    
    Defines a wallet provider's capabilities and configuration.
    This is the "template" - users create instances via user_wallets.
    
    Example:
        {
            "name": "Binance",
            "slug": "binance-v1",
            "integration_type": "cex",
            "is_demo": false,
            "required_credentials": ["api_key", "api_secret"],
            "supported_symbols": ["BTC/USDT", "ETH/USDT"]
        }
    """
    
    # Identity
    name: str = Field(..., description="Display name (e.g., 'Binance', 'Coinbase')")
    slug: str = Field(..., description="Unique identifier (e.g., 'binance-v1')")
    description: Optional[str] = Field(None, description="Provider description")
    logo_url: Optional[str] = Field(None, description="Logo image URL")
    
    # Configuration
    integration_type: IntegrationType = Field(..., description="Type of integration")
    is_demo: bool = Field(default=False, description="Is this a demo/paper trading wallet?")
    is_active: bool = Field(default=True, description="Is provider available?")
    
    # Credentials
    required_credentials: List[str] = Field(
        default_factory=list,
        description="Required credential field names (e.g., ['api_key', 'api_secret'])"
    )
    
    # Capabilities
    supported_symbols: List[str] = Field(
        default_factory=list,
        description="Supported trading pairs (e.g., ['BTC/USDT'])"
    )
    supported_order_types: List[str] = Field(
        default=["market", "limit"],
        description="Supported order types"
    )
    supports_margin: bool = Field(default=False, description="Supports margin trading?")
    supports_futures: bool = Field(default=False, description="Supports futures trading?")
    
    # Limits
    min_trade_amount: Optional[Dict[str, float]] = Field(
        None,
        description="Minimum trade amounts by symbol"
    )
    max_leverage: Optional[int] = Field(None, description="Maximum leverage allowed")
    
    # Metadata
    docs_url: Optional[str] = Field(None, description="API documentation URL")
    api_version: Optional[str] = Field(None, description="API version")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = Field(None, description="Soft delete timestamp")
    
    class Config:
        use_enum_values = True


# ==================== USER WALLET ====================

class UserWallet(BaseModel):
    """
    User Wallet Instance
    
    Represents a user's connection to a specific wallet provider.
    Contains encrypted credentials and wallet-specific settings.
    
    Example:
        {
            "user_id": "507f1f77bcf86cd799439011",
            "wallet_provider_id": "507f1f77bcf86cd799439012",
            "custom_name": "My Binance Main",
            "credentials": {
                "api_key": "encrypted_value_xxx",
                "api_secret": "encrypted_value_yyy"
            },
            "balance": {
                "USDT": 1000.00,
                "BTC": 0.5
            }
        }
    """
    
    # Ownership
    user_id: str = Field(..., description="User ID (FK to users)")
    wallet_provider_id: str = Field(..., description="Wallet definition ID (FK to wallets)")
    
    # Customization
    custom_name: str = Field(..., description="User's custom name for this wallet")
    is_active: bool = Field(default=True, description="Is this wallet active?")
    
    # Connection
    credentials: Dict[str, str] = Field(
        default_factory=dict,
        description="ENCRYPTED credentials {field_name: encrypted_value}"
    )
    connection_status: UserWalletStatus = Field(
        default=UserWalletStatus.DISCONNECTED,
        description="Current connection status"
    )
    last_connection_test: Optional[datetime] = Field(
        None,
        description="Last successful connection test"
    )
    last_connection_error: Optional[str] = Field(
        None,
        description="Last connection error message"
    )
    
    # Balance (cached)
    balance: Dict[str, float] = Field(
        default_factory=dict,
        description="Cached balances {asset: amount}"
    )
    balance_last_synced: Optional[datetime] = Field(
        None,
        description="Last balance sync time"
    )
    
    # Risk Management
    risk_limits: Dict[str, Any] = Field(
        default_factory=lambda: {
            "max_position_size_usd": 1000.00,
            "daily_loss_limit": 100.00,
            "stop_loss_default_percent": 0.02
        },
        description="Risk limits for this wallet"
    )
    
    # Statistics
    total_trades: int = Field(default=0, description="Total trades executed")
    total_pnl: float = Field(default=0.0, description="Total realized P&L")
    last_trade_at: Optional[datetime] = Field(None, description="Last trade timestamp")
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = Field(None, description="Soft delete timestamp")
    
    class Config:
        use_enum_values = True


# ==================== WALLET SYNC LOG ====================

class WalletSyncLog(BaseModel):
    """
    Wallet Balance Sync Log
    
    Tracks balance synchronization attempts for audit and debugging.
    
    Example:
        {
            "user_wallet_id": "507f1f77bcf86cd799439011",
            "status": "success",
            "balance_snapshot": {"USDT": 1000, "BTC": 0.5},
            "sync_duration_ms": 234
        }
    """
    
    user_wallet_id: str = Field(..., description="User wallet ID (FK)")
    status: SyncStatus = Field(..., description="Sync result status")
    
    # Results
    balance_snapshot: Optional[Dict[str, float]] = Field(
        None,
        description="Balance at time of sync"
    )
    balance_changes: Optional[Dict[str, float]] = Field(
        None,
        description="Changes since last sync"
    )
    
    # Performance
    sync_duration_ms: Optional[int] = Field(None, description="Sync duration in milliseconds")
    
    # Error Handling
    error_message: Optional[str] = Field(None, description="Error message if failed")
    error_code: Optional[str] = Field(None, description="Error code if failed")
    retry_count: int = Field(default=0, description="Number of retries")
    
    # Metadata
    synced_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    triggered_by: str = Field(default="manual", description="What triggered this sync")
    
    class Config:
        use_enum_values = True


# ==================== DEMO WALLET STATE ====================

class DemoWalletState(BaseModel):
    """
    Demo Wallet Simulation State
    
    Stores the current state of a demo wallet for paper trading.
    Includes simulated balances, open orders, and positions.
    
    Example:
        {
            "user_wallet_id": "507f1f77bcf86cd799439011",
            "cash_balances": {"USDT": 10000.00},
            "asset_balances": {"BTC": 0.5, "ETH": 2.0},
            "open_orders": [...],
            "transaction_history": [...]
        }
    """
    
    user_wallet_id: str = Field(..., description="User wallet ID (FK)")
    
    # Balances
    cash_balances: Dict[str, float] = Field(
        default_factory=lambda: {"USDT": 10000.00},
        description="Quote currency balances"
    )
    asset_balances: Dict[str, float] = Field(
        default_factory=dict,
        description="Asset balances {symbol: amount}"
    )
    locked_balances: Dict[str, float] = Field(
        default_factory=dict,
        description="Balances locked in open orders"
    )
    
    # Open Orders (Demo)
    open_orders: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Currently open demo orders"
    )
    
    # Transaction History
    transaction_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Past transactions for audit"
    )
    
    # Statistics
    starting_balance: float = Field(default=10000.00, description="Initial balance")
    total_realized_pnl: float = Field(default=0.0, description="Total realized P&L")
    total_fees_paid: float = Field(default=0.0, description="Total fees (simulated)")
    total_trades: int = Field(default=0, description="Number of trades executed")
    
    # Configuration
    fee_rate: float = Field(default=0.001, description="Simulated fee rate (0.1%)")
    slippage_rate: float = Field(default=0.0001, description="Simulated slippage (0.01%)")
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        use_enum_values = True


# ==================== DATABASE INDEXES ====================

WALLET_INDEXES = [
    {
        "keys": [("slug", 1)],
        "unique": True,
        "name": "slug_unique_idx"
    },
    {
        "keys": [("is_active", 1), ("integration_type", 1)],
        "name": "active_integration_idx"
    },
    {
        "keys": [("deleted_at", 1)],
        "name": "soft_delete_idx"
    }
]

USER_WALLET_INDEXES = [
    {
        "keys": [("user_id", 1), ("is_active", 1)],
        "name": "user_active_idx"
    },
    {
        "keys": [("wallet_provider_id", 1)],
        "name": "provider_idx"
    },
    {
        "keys": [("user_id", 1), ("custom_name", 1)],
        "unique": True,
        "partialFilterExpression": {"deleted_at": None},
        "name": "user_wallet_name_unique_idx"
    },
    {
        "keys": [("deleted_at", 1)],
        "name": "soft_delete_idx"
    }
]

SYNC_LOG_INDEXES = [
    {
        "keys": [("user_wallet_id", 1), ("synced_at", -1)],
        "name": "wallet_sync_time_idx"
    },
    {
        "keys": [("status", 1), ("synced_at", -1)],
        "name": "status_time_idx"
    },
    {
        "keys": [("synced_at", 1)],
        "expireAfterSeconds": 2592000,  # 30 days TTL
        "name": "ttl_idx"
    }
]

DEMO_WALLET_INDEXES = [
    {
        "keys": [("user_wallet_id", 1)],
        "unique": True,
        "name": "user_wallet_unique_idx"
    }
]
