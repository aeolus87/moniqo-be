"""
Order Management Schemas

Pydantic schemas for order API requests and responses.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field, validator
from bson import ObjectId


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


class OrderStatus(str, Enum):
    """Order status"""
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


# ==================== REQUEST SCHEMAS ====================

class CreateOrderRequest(BaseModel):
    """Create order request"""
    user_wallet_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal = Field(..., gt=0, description="Order quantity")
    price: Optional[Decimal] = Field(None, gt=0, description="Limit price (required for limit orders)")
    stop_price: Optional[Decimal] = Field(None, gt=0, description="Stop price (for stop orders)")
    time_in_force: TimeInForce = TimeInForce.GTC
    flow_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator("price")
    def validate_limit_price(cls, v, values):
        """Validate price for limit orders"""
        if values.get("order_type") in [OrderType.LIMIT, OrderType.STOP_LOSS, OrderType.TAKE_PROFIT]:
            if v is None:
                raise ValueError("Price is required for limit/stop orders")
        return v
    
    @validator("stop_price")
    def validate_stop_price(cls, v, values):
        """Validate stop price for stop orders"""
        if values.get("order_type") in [OrderType.STOP_LOSS, OrderType.TAKE_PROFIT]:
            if v is None:
                raise ValueError("Stop price is required for stop orders")
        return v


class UpdateOrderRequest(BaseModel):
    """Update order request"""
    metadata: Optional[Dict[str, Any]] = None


class CancelOrderRequest(BaseModel):
    """Cancel order request"""
    reason: Optional[str] = None


# ==================== RESPONSE SCHEMAS ====================

class OrderFillResponse(BaseModel):
    """Order fill response"""
    fill_id: str
    amount: Decimal
    price: Decimal
    fee: Decimal
    fee_currency: str
    timestamp: datetime
    trade_id: Optional[str] = None


class OrderStatusHistoryResponse(BaseModel):
    """Order status history entry"""
    status: str
    timestamp: datetime
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class OrderResponse(BaseModel):
    """Order response"""
    id: str
    user_id: str
    user_wallet_id: str
    position_id: Optional[str] = None
    flow_id: Optional[str] = None
    symbol: str
    side: str
    order_type: str
    time_in_force: str
    status: str
    requested_amount: Decimal
    filled_amount: Decimal
    remaining_amount: Decimal
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    average_fill_price: Optional[Decimal] = None
    total_fees: Decimal
    total_fees_usd: Decimal
    external_order_id: Optional[str] = None
    fills: List[OrderFillResponse]
    status_history: List[OrderStatusHistoryResponse]
    created_at: datetime
    submitted_at: Optional[datetime] = None
    first_fill_at: Optional[datetime] = None
    last_fill_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    metadata: Dict[str, Any]
    
    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    """Order list response"""
    orders: List[OrderResponse]
    total: int
    limit: int
    offset: int


class OrderCreateResponse(BaseModel):
    """Order create response"""
    success: bool
    order: OrderResponse
    message: str = "Order created successfully"


class OrderCancelResponse(BaseModel):
    """Order cancel response"""
    success: bool
    message: str
    order_id: str
    status: str


