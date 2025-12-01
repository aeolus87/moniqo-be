"""
AI Decision Logging Models

Database models for tracking AI decisions and costs.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal
from pydantic import Field
from beanie import Document
from bson import ObjectId


class AIDecisionLog(Document):
    """
    AI Decision Log Model
    
    Tracks all AI agent decisions for audit and analysis.
    
    Usage:
        log = AIDecisionLog(
            user_id=user_id,
            agent_role="market_analyst",
            decision_type="market_analysis",
            input_context={...},
            ai_response={...},
            cost_usd=Decimal("0.02")
        )
        await log.insert()
    """
    
    # Identity
    user_id: ObjectId
    flow_id: Optional[ObjectId] = None
    position_id: Optional[ObjectId] = None
    order_id: Optional[ObjectId] = None
    
    # Agent Info
    agent_role: str  # "market_analyst", "risk_manager", etc.
    model_provider: str  # "gemini", "groq", etc.
    model_name: str  # "gemini-1.5-pro", etc.
    
    # Decision Info
    decision_type: str  # "market_analysis", "risk_validation", "position_monitoring", etc.
    step: str  # "market_analysis", "risk_check", "final_vote", etc.
    
    # Input/Output
    input_context: Dict[str, Any] = Field(default_factory=dict)
    ai_response: Dict[str, Any] = Field(default_factory=dict)
    prompt_used: Optional[str] = None
    system_prompt_used: Optional[str] = None
    
    # Cost Tracking
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: Decimal = Decimal("0")
    
    # Result
    success: bool = True
    error_message: Optional[str] = None
    
    # Timing
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    execution_time_ms: Optional[int] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Settings:
        name = "ai_decisions_log"
        indexes = [
            "user_id",
            "agent_role",
            "decision_type",
            "timestamp",
            ("user_id", "timestamp"),
            ("agent_role", "timestamp"),
            ("flow_id", "timestamp"),
            ("position_id", "timestamp"),
        ]
        arbitrary_types_allowed = True
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }


class AICostSummary(Document):
    """
    AI Cost Summary Model
    
    Aggregated cost tracking per user/agent/timeframe.
    
    Usage:
        summary = AICostSummary(
            user_id=user_id,
            date=datetime.now().date(),
            agent_role="market_analyst",
            total_requests=150,
            total_cost_usd=Decimal("5.25")
        )
        await summary.insert()
    """
    
    # Identity
    user_id: ObjectId
    date: datetime  # Date for aggregation
    
    # Aggregation
    agent_role: Optional[str] = None  # None = all agents
    model_provider: Optional[str] = None  # None = all providers
    
    # Totals
    total_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: Decimal = Decimal("0")
    
    # Averages
    average_cost_per_request: Decimal = Decimal("0")
    average_tokens_per_request: int = 0
    
    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        name = "ai_cost_summary"
        indexes = [
            "user_id",
            "date",
            "agent_role",
            ("user_id", "date"),
            ("user_id", "agent_role", "date"),
        ]
        arbitrary_types_allowed = True


