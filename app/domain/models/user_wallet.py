"""
User Wallet Domain Model

Pure Pydantic domain model for user wallet instances.
Mode-specific - needs repository routing.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import Field

from app.shared.models import DomainModel, PyObjectId
from app.domain.models.wallet import UserWalletStatus


class UserWallet(DomainModel):
    """
    User Wallet Domain Model
    
    Represents a user's connection to a specific wallet provider.
    Contains encrypted credentials and wallet-specific settings.
    
    Mode-specific: Each user wallet instance exists in either real or demo database.
    """
    
    # Identity
    id: Optional[PyObjectId] = Field(None, alias="_id")
    user_id: PyObjectId
    wallet_provider_id: PyObjectId
    
    # Customization
    custom_name: str
    is_active: bool = True
    use_testnet: bool = False
    
    # Connection
    credentials: Dict[str, str] = Field(default_factory=dict)  # ENCRYPTED
    connection_status: UserWalletStatus = UserWalletStatus.DISCONNECTED
    last_connection_test: Optional[datetime] = None
    last_connection_error: Optional[str] = None
    
    # Balance (cached)
    balance: Dict[str, float] = Field(default_factory=dict)
    balance_last_synced: Optional[datetime] = None
    
    # Risk Management
    risk_limits: Dict[str, Any] = Field(
        default_factory=lambda: {
            "max_position_size_usd": 1000.00,
            "daily_loss_limit": 100.00,
            "stop_loss_default_percent": 0.02
        }
    )
    
    # Statistics
    total_trades: int = 0
    total_pnl: float = 0.0
    last_trade_at: Optional[datetime] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = None
