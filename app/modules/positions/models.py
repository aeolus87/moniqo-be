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


# ==================== EMBEDDED MODELS ====================

class EntryData(Document):
    """Position entry data"""
    order_id: ObjectId
    timestamp: datetime
    price: Decimal
    amount: Decimal
    value: Decimal  # Notional value
    leverage: Decimal = Decimal("1")
    margin_used: Decimal
    fees: Decimal
    fee_currency: str
    market_conditions: Optional[Dict[str, Any]] = None
    ai_reasoning: Optional[str] = None
    ai_confidence: Optional[int] = None
    ai_agent: Optional[str] = None
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    class Settings:
        arbitrary_types_allowed = True


class CurrentData(Document):
    """Current position state (updated in real-time)"""
    price: Decimal
    value: Decimal  # Current notional value
    unrealized_pnl: Decimal
    unrealized_pnl_percent: Decimal
    risk_level: str = "medium"  # "low", "medium", "high", "critical"
    time_held_minutes: int = 0
    high_water_mark: Decimal
    low_water_mark: Decimal
    max_drawdown_percent: Decimal
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    class Settings:
        arbitrary_types_allowed = True


class RiskManagement(Document):
    """Risk management settings"""
    initial_stop_loss: Optional[Decimal] = None
    initial_take_profit: Optional[Decimal] = None
    current_stop_loss: Optional[Decimal] = None
    current_take_profit: Optional[Decimal] = None
    stop_loss_order_id: Optional[ObjectId] = None
    take_profit_order_id: Optional[ObjectId] = None
    trailing_stop: Optional[Dict[str, Any]] = None
    break_even: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    class Settings:
        arbitrary_types_allowed = True


class ExitData(Document):
    """Position exit data"""
    order_id: ObjectId
    timestamp: datetime
    price: Decimal
    amount: Decimal
    value: Decimal
    fees: Decimal
    fee_currency: str
    reason: str  # "take_profit", "stop_loss", "manual", "ai_signal", "risk_breach"
    realized_pnl: Decimal
    realized_pnl_percent: Decimal
    time_held_minutes: int
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    class Settings:
        arbitrary_types_allowed = True


# ==================== MAIN POSITION MODEL ====================

class Position(Document):
    """
    Position Model
    
    Tracks complete trading positions from entry to exit.
    Includes P&L calculation, stop loss/take profit, and real-time monitoring.
    
    Usage:
        # Create position
        position = Position(
            user_id=user_id,
            user_wallet_id=wallet_id,
            symbol="BTC/USDT",
            side=PositionSide.LONG,
            entry_data={
                "order_id": entry_order_id,
                "price": Decimal("50000"),
                "amount": Decimal("0.5"),
                "value": Decimal("25000"),
                ...
            }
        )
        await position.insert()
        
        # Update current price
        await position.update_price(Decimal("51000"))
        
        # Close position
        await position.close(
            order_id=exit_order_id,
            price=Decimal("51500"),
            reason="take_profit"
        )
    """
    
    # Identity
    user_id: ObjectId
    user_wallet_id: ObjectId
    flow_id: Optional[ObjectId] = None
    
    # Position Basics
    symbol: str
    side: PositionSide
    status: PositionStatus = PositionStatus.OPENING
    
    # Entry
    entry: Dict[str, Any]
    
    # Current State (Updated in Real-Time)
    current: Optional[Dict[str, Any]] = None
    
    # Risk Management
    risk_management: Dict[str, Any] = Field(default_factory=dict)
    
    # AI Monitoring
    ai_monitoring: Dict[str, Any] = Field(default_factory=dict)
    
    # Exit (null if still open)
    exit: Optional[Dict[str, Any]] = None
    
    # Statistics
    statistics: Dict[str, Any] = Field(default_factory=dict)
    
    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Soft Delete
    deleted_at: Optional[datetime] = None
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    class Settings:
        name = "positions"
        indexes = [
            "user_id",
            "status",
            "opened_at",
            ("user_id", "status", "opened_at"),
            ("user_wallet_id", "status"),
            ("status", "symbol"),  # For monitoring
            "flow_id",
            ("symbol", "opened_at"),
        ]
        arbitrary_types_allowed = True
    
    async def update_price(self, current_price: Decimal):
        """
        Update current price and recalculate P&L.
        
        Args:
            current_price: Current market price
        """
        if self.status != PositionStatus.OPEN:
            return
        
        entry_price = Decimal(str(self.entry["price"]))
        entry_amount = Decimal(str(self.entry["amount"]))
        entry_fees = Decimal(str(self.entry.get("fees", 0)))
        
        # Calculate current value
        current_value = entry_amount * current_price
        
        # Calculate unrealized P&L
        if self.side == PositionSide.LONG:
            unrealized_pnl = (current_price - entry_price) * entry_amount
        else:  # SHORT
            unrealized_pnl = (entry_price - current_price) * entry_amount
        
        # Subtract fees
        unrealized_pnl -= entry_fees
        
        # Calculate percentage
        entry_value = Decimal(str(self.entry["value"]))
        unrealized_pnl_percent = (unrealized_pnl / entry_value * 100) if entry_value > 0 else Decimal("0")
        
        # Update current state
        if not self.current:
            self.current = {}
        
        self.current["price"] = current_price
        self.current["value"] = current_value
        self.current["unrealized_pnl"] = unrealized_pnl
        self.current["unrealized_pnl_percent"] = unrealized_pnl_percent
        self.current["last_updated"] = datetime.now(timezone.utc)
        
        # Update high/low water marks
        if "high_water_mark" not in self.current:
            self.current["high_water_mark"] = current_price
        if "low_water_mark" not in self.current:
            self.current["low_water_mark"] = current_price
        
        self.current["high_water_mark"] = max(
            self.current["high_water_mark"],
            current_price
        )
        self.current["low_water_mark"] = min(
            self.current["low_water_mark"],
            current_price
        )
        
        # Calculate max drawdown
        high = self.current["high_water_mark"]
        low = self.current["low_water_mark"]
        if high > 0:
            self.current["max_drawdown_percent"] = ((high - low) / high * 100)
        
        # Calculate time held
        if self.opened_at:
            time_diff = datetime.now(timezone.utc) - self.opened_at
            self.current["time_held_minutes"] = int(time_diff.total_seconds() / 60)
        
        # Update risk level
        self.current["risk_level"] = self._calculate_risk_level(unrealized_pnl_percent)
        
        self.updated_at = datetime.now(timezone.utc)
        await self.save()
    
    def _calculate_risk_level(self, pnl_percent: Decimal) -> str:
        """Calculate risk level based on P&L"""
        if pnl_percent < Decimal("-10"):
            return "critical"
        elif pnl_percent < Decimal("-5"):
            return "high"
        elif pnl_percent < Decimal("-2"):
            return "medium"
        elif pnl_percent < Decimal("0"):
            return "low"
        elif pnl_percent < Decimal("5"):
            return "low"
        else:
            return "low"
    
    async def close(
        self,
        order_id: ObjectId,
        price: Decimal,
        reason: str,
        fees: Decimal = Decimal("0"),
        fee_currency: str = "USDT"
    ):
        """
        Close position.
        
        Args:
            order_id: Exit order ID
            price: Exit price
            reason: Close reason ("take_profit", "stop_loss", "manual", etc.)
            fees: Exit fees
            fee_currency: Fee currency
        """
        if self.status in [PositionStatus.CLOSED, PositionStatus.LIQUIDATED]:
            return
        
        entry_price = Decimal(str(self.entry["price"]))
        entry_amount = Decimal(str(self.entry["amount"]))
        entry_fees = Decimal(str(self.entry.get("fees", 0)))
        entry_value = Decimal(str(self.entry["value"]))
        
        # Calculate exit value
        exit_value = entry_amount * price
        
        # Calculate realized P&L
        if self.side == PositionSide.LONG:
            realized_pnl = (price - entry_price) * entry_amount
        else:  # SHORT
            realized_pnl = (entry_price - price) * entry_amount
        
        # Subtract all fees
        realized_pnl -= entry_fees + fees
        
        # Calculate percentage
        realized_pnl_percent = (realized_pnl / entry_value * 100) if entry_value > 0 else Decimal("0")
        
        # Calculate time held
        time_held_minutes = 0
        if self.opened_at:
            time_diff = datetime.now(timezone.utc) - self.opened_at
            time_held_minutes = int(time_diff.total_seconds() / 60)
        
        # Create exit data
        self.exit = {
            "order_id": order_id,
            "timestamp": datetime.now(timezone.utc),
            "price": price,
            "amount": entry_amount,
            "value": exit_value,
            "fees": fees,
            "fee_currency": fee_currency,
            "reason": reason,
            "realized_pnl": realized_pnl,
            "realized_pnl_percent": realized_pnl_percent,
            "time_held_minutes": time_held_minutes
        }
        
        # Update statistics
        if "total_fees" not in self.statistics:
            self.statistics["total_fees"] = Decimal("0")
        self.statistics["total_fees"] += entry_fees + fees
        
        # Update status
        self.status = PositionStatus.CLOSED
        self.closed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        
        await self.save()
    
    def is_open(self) -> bool:
        """Check if position is open"""
        return self.status == PositionStatus.OPEN
    
    def is_closed(self) -> bool:
        """Check if position is closed"""
        return self.status in [PositionStatus.CLOSED, PositionStatus.LIQUIDATED]


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
            ("position_id", "timestamp"),
            ("timestamp", 1, {"expireAfterSeconds": 604800}),  # 7 days TTL
        ]
        arbitrary_types_allowed = True


