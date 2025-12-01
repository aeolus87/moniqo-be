"""
Position Management Schemas

Pydantic schemas for position API requests and responses.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field


class PositionStatus(str, Enum):
    """Position status"""
    OPENING = "opening"
    OPEN = "open"
    CLOSING = "closing"
    CLOSED = "closed"
    LIQUIDATED = "liquidated"


class PositionSide(str, Enum):
    """Position side"""
    LONG = "long"
    SHORT = "short"


# ==================== REQUEST SCHEMAS ====================

class ClosePositionRequest(BaseModel):
    """Close position request"""
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class UpdatePositionRequest(BaseModel):
    """Update position request (for manual updates)"""
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    metadata: Optional[Dict[str, Any]] = None


# ==================== RESPONSE SCHEMAS ====================

class EntryDataResponse(BaseModel):
    """Position entry data"""
    order_id: str
    timestamp: datetime
    price: Decimal
    amount: Decimal
    value: Decimal
    leverage: Decimal
    margin_used: Decimal
    fees: Decimal
    fee_currency: str
    market_conditions: Optional[Dict[str, Any]] = None
    ai_reasoning: Optional[str] = None
    ai_confidence: Optional[int] = None
    ai_agent: Optional[str] = None


class CurrentDataResponse(BaseModel):
    """Current position state"""
    price: Decimal
    value: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_percent: Decimal
    risk_level: str
    time_held_minutes: int
    high_water_mark: Decimal
    low_water_mark: Decimal
    max_drawdown_percent: Decimal
    last_updated: datetime


class RiskManagementResponse(BaseModel):
    """Risk management settings"""
    initial_stop_loss: Optional[Decimal] = None
    initial_take_profit: Optional[Decimal] = None
    current_stop_loss: Optional[Decimal] = None
    current_take_profit: Optional[Decimal] = None
    stop_loss_order_id: Optional[str] = None
    take_profit_order_id: Optional[str] = None
    trailing_stop: Optional[Dict[str, Any]] = None
    break_even: Optional[Dict[str, Any]] = None


class ExitDataResponse(BaseModel):
    """Position exit data"""
    order_id: str
    timestamp: datetime
    price: Decimal
    amount: Decimal
    value: Decimal
    fees: Decimal
    fee_currency: str
    reason: str
    realized_pnl: Decimal
    realized_pnl_percent: Decimal
    time_held_minutes: int


class PositionResponse(BaseModel):
    """Position response"""
    id: str
    user_id: str
    user_wallet_id: str
    flow_id: Optional[str] = None
    symbol: str
    side: str
    status: str
    entry: EntryDataResponse
    current: Optional[CurrentDataResponse] = None
    risk_management: RiskManagementResponse
    exit: Optional[ExitDataResponse] = None
    statistics: Dict[str, Any]
    created_at: datetime
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PositionListResponse(BaseModel):
    """Position list response"""
    positions: List[PositionResponse]
    total: int
    page: int = 1
    page_size: int = 50


class ClosePositionResponse(BaseModel):
    """Close position response"""
    success: bool
    message: str
    position_id: str
    realized_pnl: Decimal
    realized_pnl_percent: Decimal


