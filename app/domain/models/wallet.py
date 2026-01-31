"""
Wallet Domain Models

Pure Pydantic domain models for wallet definitions and user wallets.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
from pydantic import Field

from app.shared.models import DomainModel, PyObjectId


# ==================== ENUMS ====================

class IntegrationType(str, Enum):
    """Wallet integration types"""
    CEX = "cex"
    DEX = "dex"
    SIMULATION = "simulation"


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


# ==================== WALLET DEFINITION ====================

class WalletDefinition(DomainModel):
    """
    Wallet Provider Definition
    
    Defines a wallet provider's capabilities and configuration.
    This is the "template" - users create instances via user_wallets.
    
    Note: Wallet definitions are shared between real/demo databases.
    Use db_provider.get_db_for_mode(DEMO) to access the shared collection.
    """
    
    # Identity
    id: Optional[PyObjectId] = Field(None, alias="_id")
    name: str
    slug: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    
    # Configuration
    integration_type: IntegrationType
    is_demo: bool = False
    is_active: bool = True
    
    # Credentials
    required_credentials: List[str] = Field(default_factory=list)
    
    # Capabilities
    supported_symbols: List[str] = Field(default_factory=list)
    supported_order_types: List[str] = Field(default_factory=lambda: ["market", "limit"])
    supports_margin: bool = False
    supports_futures: bool = False
    
    # Limits
    min_trade_amount: Optional[Dict[str, float]] = None
    max_leverage: Optional[int] = None
    
    # Metadata
    docs_url: Optional[str] = None
    api_version: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = None
