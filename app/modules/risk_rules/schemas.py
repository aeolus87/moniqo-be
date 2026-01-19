"""
Risk Rules Schemas

Pydantic schemas for Risk Rules API.

Author: Moniqo Team
Last Updated: 2026-01-17
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class RiskRuleCreate(BaseModel):
    """Create risk rule request"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    user_id: Optional[str] = None
    wallet_id: Optional[str] = None
    limits: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class RiskRuleUpdate(BaseModel):
    """Update risk rule request"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    user_id: Optional[str] = None
    wallet_id: Optional[str] = None
    limits: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class RiskRuleResponse(BaseModel):
    """Risk rule response"""
    id: str
    name: str
    description: Optional[str] = None
    user_id: Optional[str] = None
    wallet_id: Optional[str] = None
    limits: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        populate_by_name = True


class RiskRuleListResponse(BaseModel):
    """Risk rule list response"""
    items: List[RiskRuleResponse]
    total: int
    limit: int
    offset: int
    has_more: bool
