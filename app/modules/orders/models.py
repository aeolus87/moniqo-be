"""
Order Management Models

Database models for order tracking and lifecycle management.

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

class OrderStatus(str, Enum):
    """Order status lifecycle"""
    PENDING = "pending"                    # Created, not yet submitted
    SUBMITTED = "submitted"                # Sent to exchange, awaiting confirmation
    OPEN = "open"                          # Confirmed open on exchange
    PARTIALLY_FILLED = "partially_filled"  # Some fills, still open
    FILLED = "filled"                      # Completely filled
    CANCELLING = "cancelling"              # Cancel requested
    CANCELLED = "cancelled"                # Successfully cancelled
    REJECTED = "rejected"                  # Exchange rejected
    EXPIRED = "expired"                    # Time expired (GTD orders)
    FAILED = "failed"                      # Error occurred


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
    GTC = "GTC"  # Good Till Cancel
    IOC = "IOC"  # Immediate Or Cancel
    FOK = "FOK"  # Fill Or Kill
    GTD = "GTD"  # Good Till Date


# ==================== EMBEDDED MODELS ====================

class OrderStatusHistory(Document):
    """Order status history entry"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    status: OrderStatus
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    class Settings:
        arbitrary_types_allowed = True


class OrderFill(Document):
    """Order fill (partial execution)"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    fill_id: str
    amount: Decimal
    price: Decimal
    fee: Decimal
    fee_currency: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trade_id: Optional[str] = None  # Exchange trade ID
    metadata: Optional[Dict[str, Any]] = None
    
    class Settings:
        arbitrary_types_allowed = True


# ==================== MAIN ORDER MODEL ====================

class Order(Document):
    """
    Order Model
    
    Tracks all orders from creation to completion.
    Includes partial fills, status history, and lifecycle management.
    
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
        await order.insert()
        
        # Update status
        await order.update_status(OrderStatus.OPEN, "Order accepted by exchange")
        
        # Add fill
        fill = OrderFill(
            fill_id="fill_001",
            amount=Decimal("0.3"),
            price=Decimal("50000.00"),
            fee=Decimal("0.0003"),
            fee_currency="BTC"
        )
        await order.add_fill(fill)
    """
    
    # Identity
    user_id: ObjectId
    user_wallet_id: ObjectId
    position_id: Optional[ObjectId] = None  # FK to positions (null for new position)
    flow_id: Optional[ObjectId] = None      # FK to flows (which AI flow created this)
    execution_id: Optional[ObjectId] = None # FK to executions (which execution)
    
    # Order Details
    symbol: str
    side: OrderSide
    order_type: OrderType
    time_in_force: TimeInForce = TimeInForce.GTC
    
    # Quantities & Prices
    requested_amount: Decimal
    filled_amount: Decimal = Decimal("0")
    remaining_amount: Decimal  # Calculated: requested_amount - filled_amount
    limit_price: Optional[Decimal] = None    # Limit price (null for market)
    stop_price: Optional[Decimal] = None     # Stop trigger price
    average_fill_price: Optional[Decimal] = None  # Weighted average fill price
    
    # Status
    status: OrderStatus = OrderStatus.PENDING
    status_history: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Exchange Info
    exchange: str = "binance"  # Exchange name
    external_order_id: Optional[str] = None  # Exchange's order ID
    exchange_response: Optional[Dict[str, Any]] = None  # Raw exchange response
    
    # Fills (Executions)
    fills: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Fees
    total_fees: Decimal = Decimal("0")
    total_fees_usd: Decimal = Decimal("0")
    
    # AI Context
    ai_reasoning: Optional[str] = None
    ai_confidence: Optional[int] = None  # 0-100
    ai_agent_id: Optional[ObjectId] = None
    
    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    submitted_at: Optional[datetime] = None  # When sent to exchange
    first_fill_at: Optional[datetime] = None
    last_fill_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Soft Delete
    deleted_at: Optional[datetime] = None
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    class Settings:
        name = "orders"
        indexes = [
            "user_id",
            "status",
            "created_at",
            [("user_id", 1), ("status", 1), ("created_at", -1)],
            [("user_wallet_id", 1), ("status", 1)],
            "position_id",
            "external_order_id",
            [("status", 1), ("order_type", 1)],
            [("symbol", 1), ("created_at", -1)],
        ]
        arbitrary_types_allowed = True
    
    @validator("remaining_amount", always=True)
    def calculate_remaining_amount(cls, v, values):
        """Calculate remaining amount from requested and filled"""
        if "requested_amount" in values and "filled_amount" in values:
            return values["requested_amount"] - values.get("filled_amount", Decimal("0"))
        return v
    
    async def update_status(
        self,
        new_status: OrderStatus,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Update order status and add to history.
        
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
        
        await self.save()
    
    async def add_fill(
        self,
        fill: Dict[str, Any]
    ):
        """
        Add a fill to the order.
        
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
        # TODO: Calculate total_fees_usd based on fee currency
        
        # Update timestamps
        now = datetime.now(timezone.utc)
        if not self.first_fill_at:
            self.first_fill_at = now
        self.last_fill_at = now
        
        # Update status
        if self.remaining_amount <= Decimal("0"):
            await self.update_status(OrderStatus.FILLED, "Order completely filled")
        else:
            await self.update_status(OrderStatus.PARTIALLY_FILLED, f"Partial fill: {fill_amount} {self.symbol.split('/')[0]}")
        
        await self.save()
    
    def is_open(self) -> bool:
        """Check if order is still open (not filled/cancelled/rejected)"""
        return self.status in [
            OrderStatus.OPEN,
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.PENDING,
            OrderStatus.SUBMITTED
        ]
    
    def is_complete(self) -> bool:
        """Check if order is complete (filled/cancelled/rejected/expired)"""
        return self.status in [
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED
        ]


