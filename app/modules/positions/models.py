"""
Position Management Models

Database models for position tracking and P&L calculation.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from pydantic import Field, validator, ConfigDict
from beanie import Document
from bson import ObjectId


# ==================== ENUMS ====================

class PositionStatus(str, Enum):
    """Position status lifecycle"""
    OPENING = "opening"        # Entry order pending
    OPEN = "open"              # Position active
    CLOSING = "closing"        # Exit order pending
    CLOSED = "closed"          # Position closed
    LIQUIDATED = "liquidated"  # Margin call


class PositionSide(str, Enum):
    """Position side"""
    LONG = "long"
    SHORT = "short"


# ==================== MAIN POSITION MODEL ====================
# NOTE: Beanie Position model REMOVED - using Pydantic domain model from app.domain.models.position
# The Position domain model is managed via PositionRepository
# Import Position domain model: from app.domain.models.position import Position


# ==================== POSITION UPDATES MODEL ====================

class PositionUpdate(Document):
    """
    Position Update Model
    
    Tracks every price update for positions (for analysis/debugging).
    Auto-deleted after 7 days (TTL index).
    
    Usage:
        update = PositionUpdate(
            position_id=position_id,
            price=Decimal("51000"),
            unrealized_pnl=Decimal("475"),
            unrealized_pnl_percent=Decimal("1.9")
        )
        await update.insert()
    """
    
    position_id: ObjectId
    price: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_percent: Decimal
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actions_triggered: List[Dict[str, Any]] = Field(default_factory=list)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    class Settings:
        name = "position_updates"
        indexes = [
            [("position_id", 1), ("timestamp", -1)],
        ]
        arbitrary_types_allowed = True
