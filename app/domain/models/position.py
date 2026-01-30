"""
Position Domain Model

Pure Pydantic domain model for positions.
No database dependencies - business logic only.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from pydantic import Field

from app.shared.models import DomainModel, PyObjectId


# ==================== ENUMS ====================

class PositionStatus(str, Enum):
    """Position status lifecycle"""
    OPENING = "opening"
    OPEN = "open"
    CLOSING = "closing"
    CLOSED = "closed"
    LIQUIDATED = "liquidated"


class PositionSide(str, Enum):
    """Position side"""
    LONG = "long"
    SHORT = "short"


# ==================== MAIN POSITION MODEL ====================

class Position(DomainModel):
    """
    Position Domain Model
    
    Pure Pydantic model representing a trading position in the domain.
    No database methods - use PositionRepository for persistence.
    
    Usage:
        # Create position
        position = Position(
            user_id=user_id,
            user_wallet_id=wallet_id,
            symbol="BTC/USDT",
            side=PositionSide.LONG,
            entry={"price": Decimal("50000"), ...}
        )
        
        # Update price (domain logic only - doesn't save)
        position.update_price(Decimal("51000"))
        
        # Close position (domain logic only - doesn't save)
        position.close(
            order_id=exit_order_id,
            price=Decimal("51500"),
            reason="take_profit"
        )
        
        # Save via repository
        position = await repository.save(position)
    """
    
    # Identity
    id: Optional[PyObjectId] = Field(None, alias="_id")
    user_id: PyObjectId
    user_wallet_id: PyObjectId
    flow_id: Optional[PyObjectId] = None
    
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
    
    def update_price(self, current_price: Decimal) -> None:
        """
        Update current price and recalculate P&L.
        
        Domain logic only - does not persist to database.
        Call repository.save() after calling this method.
        
        Args:
            current_price: Current market price
        """
        if self.status != PositionStatus.OPEN:
            return
        
        # Ensure current_price is Decimal
        if not isinstance(current_price, Decimal):
            current_price = Decimal(str(current_price))
        
        entry_price = Decimal(str(self.entry["price"]))
        entry_amount = Decimal(str(self.entry["amount"]))
        entry_fees = Decimal(str(self.entry.get("fees", 0)))
        
        # Calculate current value
        current_value = entry_amount * current_price
        
        # Get leverage from entry (default 1x for spot trading)
        leverage = int(self.entry.get("leverage", 1))
        
        # Calculate unrealized P&L (accounting for leverage)
        if self.side == PositionSide.LONG:
            unrealized_pnl = (current_price - entry_price) * entry_amount * leverage
        else:  # SHORT
            unrealized_pnl = (entry_price - current_price) * entry_amount * leverage
        
        # Subtract fees
        unrealized_pnl -= entry_fees
        
        # Calculate percentage
        entry_value = Decimal(str(self.entry["value"]))
        unrealized_pnl_percent = (unrealized_pnl / entry_value * 100) if entry_value > 0 else Decimal("0")
        
        # Update current state
        if not self.current:
            self.current = {}
        
        self.current["price"] = float(current_price)
        self.current["value"] = float(current_value)
        self.current["unrealized_pnl"] = float(unrealized_pnl)
        self.current["unrealized_pnl_percent"] = float(unrealized_pnl_percent)
        self.current["last_updated"] = datetime.now(timezone.utc)
        
        # Update high/low water marks
        if "high_water_mark" not in self.current:
            self.current["high_water_mark"] = float(current_price)
        if "low_water_mark" not in self.current:
            self.current["low_water_mark"] = float(current_price)
        
        self.current["high_water_mark"] = max(
            self.current["high_water_mark"],
            float(current_price)
        )
        self.current["low_water_mark"] = min(
            self.current["low_water_mark"],
            float(current_price)
        )
        
        # Calculate max drawdown
        high = Decimal(str(self.current["high_water_mark"]))
        low = Decimal(str(self.current["low_water_mark"]))
        if high > 0:
            self.current["max_drawdown_percent"] = float(((high - low) / high * 100))
        
        # Calculate time held
        if self.opened_at:
            # Ensure opened_at is timezone-aware and in UTC
            opened_at_utc = self.opened_at
            if opened_at_utc.tzinfo is None:
                opened_at_utc = opened_at_utc.replace(tzinfo=timezone.utc)
            else:
                opened_at_utc = opened_at_utc.astimezone(timezone.utc)
            time_diff = datetime.now(timezone.utc) - opened_at_utc
            self.current["time_held_minutes"] = int(time_diff.total_seconds() / 60)
        
        # Update risk level
        self.current["risk_level"] = self._calculate_risk_level(unrealized_pnl_percent)
        
        self.updated_at = datetime.now(timezone.utc)
    
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
    
    def close(
        self,
        order_id: str,
        price: Decimal,
        reason: str,
        fees: Decimal = Decimal("0"),
        fee_currency: str = "USDT"
    ) -> None:
        """
        Close position.
        
        Domain logic only - does not persist to database.
        Call repository.save() after calling this method.
        
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
        leverage = int(self.entry.get("leverage", 1))
        
        # Calculate exit value
        exit_value = entry_amount * price
        
        # Calculate realized P&L (accounting for leverage)
        if self.side == PositionSide.LONG:
            realized_pnl = (price - entry_price) * entry_amount * leverage
        else:  # SHORT
            realized_pnl = (entry_price - price) * entry_amount * leverage
        
        # Subtract all fees
        realized_pnl -= entry_fees + fees
        
        # Calculate percentage
        realized_pnl_percent = (realized_pnl / entry_value * 100) if entry_value > 0 else Decimal("0")
        
        # Calculate time held
        time_held_minutes = 0
        if self.opened_at:
            opened_at_utc = self.opened_at
            if opened_at_utc.tzinfo is None:
                opened_at_utc = opened_at_utc.replace(tzinfo=timezone.utc)
            else:
                opened_at_utc = opened_at_utc.astimezone(timezone.utc)
            time_diff = datetime.now(timezone.utc) - opened_at_utc
            time_held_minutes = int(time_diff.total_seconds() / 60)
        
        # Create exit data
        self.exit = {
            "order_id": order_id,
            "timestamp": datetime.now(timezone.utc),
            "price": float(price),
            "amount": float(entry_amount),
            "value": float(exit_value),
            "fees": float(fees),
            "fee_currency": fee_currency,
            "reason": reason,
            "realized_pnl": float(realized_pnl),
            "realized_pnl_percent": float(realized_pnl_percent),
            "time_held_minutes": time_held_minutes
        }
        
        # Update statistics
        if "total_fees" not in self.statistics:
            self.statistics["total_fees"] = float(entry_fees)
        else:
            self.statistics["total_fees"] = float(Decimal(str(self.statistics["total_fees"])) + entry_fees + fees)
        
        # Update status
        self.status = PositionStatus.CLOSED
        self.closed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def is_open(self) -> bool:
        """Check if position is open"""
        return self.status == PositionStatus.OPEN
    
    def is_closed(self) -> bool:
        """Check if position is closed"""
        return self.status in [PositionStatus.CLOSED, PositionStatus.LIQUIDATED]
