"""
Flow and Execution Models

MongoDB document models for trading flows and their executions.

Author: Moniqo Team
Last Updated: 2026-01-17
"""

from typing import List, Optional, Dict, Any, TYPE_CHECKING
from enum import Enum
from datetime import datetime, timezone
from decimal import Decimal
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    pass


class FlowStatus(str, Enum):
    """Flow status"""
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


class FlowMode(str, Enum):
    """Flow execution mode"""
    SOLO = "solo"       # Single agent
    SWARM = "swarm"     # Multiple agents


class FlowTrigger(str, Enum):
    """Flow trigger type"""
    MANUAL = "manual"       # Manual trigger
    SCHEDULE = "schedule"   # Scheduled execution
    SIGNAL = "signal"       # Signal-based


class ExecutionStatus(str, Enum):
    """Execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Execution step status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepName(str, Enum):
    """Standard execution step names"""
    DATA_FETCH = "data_fetch"           # Step 0: Fetch market data + indicators
    MARKET_ANALYSIS = "market_analysis" # Step 1: AI market analyst
    RISK_VALIDATION = "risk_validation" # Step 2: AI risk manager
    DECISION = "decision"               # Step 3: Final action decision


class ExecutionStep(BaseModel):
    """Single execution step"""
    name: str
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# Standard steps factory
def create_standard_steps() -> List["ExecutionStep"]:
    """Create the standard execution steps for a flow."""
    return [
        ExecutionStep(name=StepName.DATA_FETCH.value),
        ExecutionStep(name=StepName.MARKET_ANALYSIS.value),
        ExecutionStep(name=StepName.RISK_VALIDATION.value),
        ExecutionStep(name=StepName.DECISION.value),
    ]


class ExecutionResult(BaseModel):
    """Execution result"""
    action: str  # "buy", "sell", "hold"
    confidence: float
    reasoning: str
    position_id: Optional[str] = None


class Flow(BaseModel):
    """Trading flow document"""
    id: Optional[str] = Field(None, alias="_id")
    name: str
    symbol: str  # Trading pair, e.g., "BTC/USDT"
    mode: FlowMode = FlowMode.SOLO
    trigger: FlowTrigger = FlowTrigger.MANUAL
    status: FlowStatus = FlowStatus.PAUSED
    agents: List[str] = Field(default_factory=list)  # Agent IDs/types
    
    # Configuration
    schedule: Optional[str] = None  # Cron expression for scheduled flows
    config: Dict[str, Any] = Field(default_factory=dict)
    
    # Statistics
    total_executions: int = 0
    successful_executions: int = 0
    last_run_at: Optional[datetime] = None
    total_pnl_usd: Decimal = Decimal("0")
    total_pnl_percent: Decimal = Decimal("0")
    winning_trades: int = 0  # Count of profitable trades (PnL > 0)
    win_rate: float = 0.0  # Percentage of profitable trades (0.0 to 100.0)
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class Execution(BaseModel):
    """Flow execution document"""
    id: Optional[str] = Field(None, alias="_id")
    flow_id: str
    flow_name: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    
    # Timeline
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    duration: Optional[int] = None  # Duration in milliseconds
    
    # Execution steps
    steps: List[ExecutionStep] = Field(default_factory=list)
    
    # Result
    result: Optional[ExecutionResult] = None
    
    # Context
    market_data: Optional[Dict[str, Any]] = None
    indicators: Optional[Dict[str, Any]] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class AgentDecision(BaseModel):
    """Agent decision log"""
    id: Optional[str] = Field(None, alias="_id")
    execution_id: str
    agent_role: str  # "market_analyst", "risk_manager", etc.
    action: str      # "buy", "sell", "hold", "approve", "reject"
    confidence: float
    reasoning: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}
