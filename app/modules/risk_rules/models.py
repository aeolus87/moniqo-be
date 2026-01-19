"""
Risk Rules Models

Defines risk rule documents for trade validation.

Author: Moniqo Team
Last Updated: 2026-01-17
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class RiskRule(BaseModel):
    """Risk rule document"""
    id: Optional[str] = Field(None, alias="_id")
    name: str
    description: Optional[str] = None
    user_id: Optional[str] = None
    wallet_id: Optional[str] = None
    limits: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}
