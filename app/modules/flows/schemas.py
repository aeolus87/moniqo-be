"""
Flow Schemas

Pydantic schemas for Flow API requests and responses.

Last Updated: 2026-01-17
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from app.modules.flows.models import (
    FlowStatus,
    FlowMode,
    FlowTrigger,
    ExecutionStatus,
    StepStatus,
)


# ==================== REQUEST SCHEMAS ====================

class FlowCreate(BaseModel):
    """Create flow request"""
    name: str = Field(..., min_length=1, max_length=100, description="Flow name")
    symbol: str = Field(..., description="Trading pair (e.g., BTC/USDT)")
    mode: FlowMode = Field(default=FlowMode.SOLO, description="Execution mode")
    trigger: FlowTrigger = Field(default=FlowTrigger.MANUAL, description="Trigger type")
    agents: List[str] = Field(default=["market_analyst", "risk_manager"], description="Agents to use")
    schedule: Optional[str] = Field(None, description="Cron expression for scheduled flows")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional configuration")


class FlowUpdate(BaseModel):
    """Update flow request"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    symbol: Optional[str] = None
    mode: Optional[FlowMode] = None
    trigger: Optional[FlowTrigger] = None
    status: Optional[FlowStatus] = None
    agents: Optional[List[str]] = None
    schedule: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class TriggerFlowRequest(BaseModel):
    """Trigger flow request"""
    model_provider: str = Field(default="groq", description="AI model provider")
    model_name: Optional[str] = Field(None, description="Specific model name")


# ==================== RESPONSE SCHEMAS ====================

class ExecutionStepResponse(BaseModel):
    """Execution step response"""
    name: str
    status: StepStatus
    startedAt: Optional[datetime] = Field(None, alias="started_at")
    completedAt: Optional[datetime] = Field(None, alias="completed_at")
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    class Config:
        populate_by_name = True


class ExecutionResultResponse(BaseModel):
    """Execution result response"""
    action: str
    confidence: float
    reasoning: str
    positionId: Optional[str] = Field(None, alias="position_id")

    class Config:
        populate_by_name = True


class FlowResponse(BaseModel):
    """Flow response"""
    id: str
    name: str
    symbol: str
    mode: FlowMode
    trigger: FlowTrigger
    status: FlowStatus
    agents: List[str]
    schedule: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    totalExecutions: int = Field(0, alias="total_executions")
    successfulExecutions: int = Field(0, alias="successful_executions")
    lastRunAt: Optional[datetime] = Field(None, alias="last_run_at")
    createdAt: datetime = Field(..., alias="created_at")
    updatedAt: Optional[datetime] = Field(None, alias="updated_at")

    class Config:
        populate_by_name = True


class ExecutionResponse(BaseModel):
    """Execution response"""
    id: str
    flowId: str = Field(..., alias="flow_id")
    flowName: str = Field(..., alias="flow_name")
    status: ExecutionStatus
    startedAt: datetime = Field(..., alias="started_at")
    completedAt: Optional[datetime] = Field(None, alias="completed_at")
    duration: Optional[int] = None
    steps: List[ExecutionStepResponse] = Field(default_factory=list)
    result: Optional[ExecutionResultResponse] = None

    class Config:
        populate_by_name = True


class AgentDecisionResponse(BaseModel):
    """Agent decision response"""
    id: str
    executionId: str
    agentRole: str
    action: str
    confidence: float
    reasoning: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime


class FlowListResponse(BaseModel):
    """Flow list response"""
    items: List[FlowResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class ExecutionListResponse(BaseModel):
    """Execution list response"""
    items: List[ExecutionResponse]
    total: int
    limit: int
    offset: int
    has_more: bool
