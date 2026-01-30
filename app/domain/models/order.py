"""
Order Domain Model

Pure Pydantic domain model for orders.
No database dependencies - business logic only.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from pydantic import Field, field_validator

from app.shared.models import DomainModel, PyObjectId


# ==================== ENUMS ====================

class OrderStatus(str, Enum):
    """Order status lifecycle"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    FAILED = "failed"


class OrderSide(str, Enum):
    """Order side"""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class TimeInForce(str, Enum):
    """Time in force"""
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"
    GTD = "GTD"


# ==================== MAIN ORDER MODEL ====================

class Order(DomainModel):
    """
    Order Domain Model
    
    Pure Pydantic model representing an order in the domain.
    No database methods - use OrderRepository for persistence.
    
    Usage:
        # Create order
        order = Order(
            user_id=user_id,
            user_wallet_id=wallet_id,
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            requested_amount=Decimal("0.5")
        )
        
        # Update status (domain logic only - doesn't save)
        order.update_status(OrderStatus.OPEN, "Order accepted by exchange")
        
        # Add fill (domain logic only - doesn't save)
        order.add_fill({
            "fill_id": "fill_001",
            "amount": Decimal("0.3"),
            "price": Decimal("50000.00"),
            "fee": Decimal("0.0003"),
            "fee_currency": "BTC"
        })
        
        # Save via repository
        order = await repository.save(order)
    """
    
    # Identity
    id: Optional[PyObjectId] = Field(None, alias="_id")
    user_id: PyObjectId
    user_wallet_id: PyObjectId
    position_id: Optional[PyObjectId] = None
    flow_id: Optional[PyObjectId] = None
    execution_id: Optional[PyObjectId] = None
    
    # Order Details
    symbol: str
    side: OrderSide
    order_type: OrderType
    time_in_force: TimeInForce = TimeInForce.GTC
    
    # Quantities & Prices
    requested_amount: Decimal
    filled_amount: Decimal = Decimal("0")
    remaining_amount: Decimal = Field(default=Decimal("0"))
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    average_fill_price: Optional[Decimal] = None
    
    # Status
    status: OrderStatus = OrderStatus.PENDING
    status_history: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Exchange Info
    exchange: str = "binance"
    external_order_id: Optional[str] = None
    exchange_response: Optional[Dict[str, Any]] = None
    
    # Fills
    fills: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Fees
    total_fees: Decimal = Decimal("0")
    total_fees_usd: Decimal = Decimal("0")
    
    # AI Context
    ai_reasoning: Optional[str] = None
    ai_confidence: Optional[int] = None
    ai_agent_id: Optional[PyObjectId] = None
    
    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    submitted_at: Optional[datetime] = None
    first_fill_at: Optional[datetime] = None
    last_fill_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Soft Delete
    deleted_at: Optional[datetime] = None
    
    @field_validator("remaining_amount", mode="before")
    @classmethod
    def calculate_remaining_amount(cls, v, info):
        """Calculate remaining amount from requested and filled"""
        if info.data.get("requested_amount") and info.data.get("filled_amount") is not None:
            return info.data["requested_amount"] - info.data.get("filled_amount", Decimal("0"))
        return v or Decimal("0")
    
    def update_status(
        self,
        new_status: OrderStatus,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update order status and add to history.
        
        Domain logic only - does not persist to database.
        Call repository.save() after calling this method.
        
        Args:
            new_status: New order status
            reason: Reason for status change
            metadata: Additional metadata
        """
        old_status = self.status
        self.status = new_status
        
        # Add to history
        self.status_history.append({
            "status": new_status.value,
            "timestamp": datetime.now(timezone.utc),
            "reason": reason or f"Status changed from {old_status.value} to {new_status.value}",
            "metadata": metadata or {}
        })
        
        # Set timestamps based on status
        now = datetime.now(timezone.utc)
        if new_status == OrderStatus.SUBMITTED:
            self.submitted_at = now
        elif new_status == OrderStatus.CANCELLED:
            self.cancelled_at = now
        elif new_status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            self.closed_at = now
        
        # Recalculate remaining amount
        self.remaining_amount = self.requested_amount - self.filled_amount
    
    def add_fill(self, fill: Dict[str, Any]) -> None:
        """
        Add a fill to the order.
        
        Domain logic only - does not persist to database.
        Call repository.save() after calling this method.
        
        Args:
            fill: Fill dictionary with amount, price, fee, etc.
        """
        fill_amount = Decimal(str(fill["amount"]))
        fill_price = Decimal(str(fill["price"]))
        fill_fee = Decimal(str(fill.get("fee", 0)))
        
        # Add to fills list
        self.fills.append({
            **fill,
            "timestamp": datetime.now(timezone.utc)
        })
        
        # Update filled amount
        self.filled_amount += fill_amount
        self.remaining_amount = self.requested_amount - self.filled_amount
        
        # Update average fill price (weighted)
        if self.fills:
            total_value = Decimal("0")
            total_amount = Decimal("0")
            for f in self.fills:
                amount = Decimal(str(f["amount"]))
                price = Decimal(str(f["price"]))
                total_value += amount * price
                total_amount += amount
            
            if total_amount > 0:
                self.average_fill_price = total_value / total_amount
        
        # Update fees
        self.total_fees += fill_fee
        
        # Update timestamps
        now = datetime.now(timezone.utc)
        if not self.first_fill_at:
            self.first_fill_at = now
        self.last_fill_at = now
        
        # Update status
        if self.remaining_amount <= Decimal("0"):
            self.update_status(OrderStatus.FILLED, "Order completely filled")
        else:
            self.update_status(
                OrderStatus.PARTIALLY_FILLED,
                f"Partial fill: {fill_amount}"
            )
    
    def is_open(self) -> bool:
        """Check if order is still open"""
        return self.status in [
            OrderStatus.OPEN,
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.PENDING,
            OrderStatus.SUBMITTED
        ]
    
    def is_complete(self) -> bool:
        """Check if order is complete"""
        return self.status in [
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED
        ]
