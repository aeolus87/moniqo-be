"""
Risk Rules Router

API endpoints for risk rule management.
No authentication required for demo.

Author: Moniqo Team
Last Updated: 2026-01-17
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import db_provider
from app.modules.risk_rules.schemas import (
    RiskRuleCreate,
    RiskRuleUpdate,
    RiskRuleResponse,
    RiskRuleListResponse,
)
from app.modules.risk_rules import service as risk_rule_service
from app.modules.risk_rules.risk_evaluator import evaluate_risk_limits
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/risk-rules", tags=["Risk Rules"])


def rule_to_response(rule) -> RiskRuleResponse:
    """Convert RiskRule model to response"""
    return RiskRuleResponse(
        id=str(rule.id),
        name=rule.name,
        description=rule.description,
        user_id=rule.user_id,
        wallet_id=rule.wallet_id,
        limits=rule.limits,
        is_active=rule.is_active,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.post(
    "",
    response_model=RiskRuleResponse,
    status_code=201,
    summary="Create risk rule",
    description="Create a new risk rule",
)
async def create_risk_rule(
    data: RiskRuleCreate,
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db()),
):
    """Create a new risk rule"""
    try:
        rule = await risk_rule_service.create_risk_rule(db, data)
        return rule_to_response(rule)
    except Exception as e:
        logger.error(f"Failed to create risk rule: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create risk rule: {str(e)}")


@router.get(
    "",
    response_model=RiskRuleListResponse,
    summary="List risk rules",
    description="List risk rules with pagination",
)
async def list_risk_rules(
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    user_id: Optional[str] = Query(None, description="Filter by user id"),
    wallet_id: Optional[str] = Query(None, description="Filter by wallet id"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db()),
):
    """List risk rules"""
    try:
        rules, total = await risk_rule_service.get_risk_rules(
            db,
            limit=limit,
            offset=offset,
            user_id=user_id,
            wallet_id=wallet_id,
            is_active=is_active,
        )
        return RiskRuleListResponse(
            items=[rule_to_response(r) for r in rules],
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + len(rules) < total,
        )
    except Exception as e:
        logger.error(f"Failed to list risk rules: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list risk rules: {str(e)}")


@router.get(
    "/{rule_id}",
    response_model=RiskRuleResponse,
    summary="Get risk rule",
    description="Get a risk rule by ID",
)
async def get_risk_rule(
    rule_id: str,
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db()),
):
    """Get risk rule"""
    rule = await risk_rule_service.get_risk_rule_by_id(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Risk rule not found: {rule_id}")
    return rule_to_response(rule)


@router.get(
    "/validate",
    summary="Validate risk rules",
    description="Validate a proposed trade against risk limits",
)
async def validate_risk_rules(
    symbol: str,
    action: str,
    size_usd: float,
    price: float,
    rule_id: Optional[str] = None,
    user_id: Optional[str] = None,
    wallet_id: Optional[str] = None,
    portfolio_value_usd: float = 10000.0,
    open_positions: int = 0,
    daily_loss_usd: float = 0.0,
    portfolio_utilization_percent: float = 0.0,
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db()),
):
    """Validate a proposed trade against risk limits"""
    try:
        risk_rule = None
        if rule_id:
            risk_rule = await risk_rule_service.get_risk_rule_by_id(db, rule_id)
            if not risk_rule:
                raise HTTPException(status_code=404, detail=f"Risk rule not found: {rule_id}")
        elif user_id:
            rules, _ = await risk_rule_service.get_risk_rules(
                db,
                limit=1,
                offset=0,
                user_id=user_id,
                wallet_id=wallet_id,
                is_active=True,
            )
            risk_rule = rules[0] if rules else None

        risk_limits = risk_rule.limits if risk_rule else {}

        order_request = {
            "symbol": symbol,
            "action": action,
            "size_usd": size_usd,
            "price": price,
        }
        portfolio_state = {
            "portfolio_value_usd": portfolio_value_usd,
            "open_positions": open_positions,
            "daily_loss_usd": daily_loss_usd,
            "portfolio_utilization_percent": portfolio_utilization_percent,
        }

        result = evaluate_risk_limits(order_request, risk_limits, portfolio_state)
        return {
            "approved": result["approved"],
            "violations": result["violations"],
            "summary": result["summary"],
            "rule_id": str(risk_rule.id) if risk_rule else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate risk rules: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to validate risk rules: {str(e)}")


@router.patch(
    "/{rule_id}",
    response_model=RiskRuleResponse,
    summary="Update risk rule",
    description="Update a risk rule",
)
async def update_risk_rule(
    rule_id: str,
    updates: RiskRuleUpdate,
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db()),
):
    """Update risk rule"""
    existing = await risk_rule_service.get_risk_rule_by_id(db, rule_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Risk rule not found: {rule_id}")
    try:
        rule = await risk_rule_service.update_risk_rule(db, rule_id, updates)
        if not rule:
            raise HTTPException(status_code=500, detail="Failed to update risk rule")
        return rule_to_response(rule)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update risk rule: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update risk rule: {str(e)}")


@router.delete(
    "/{rule_id}",
    status_code=204,
    summary="Delete risk rule",
    description="Delete a risk rule",
)
async def delete_risk_rule(
    rule_id: str,
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db()),
):
    """Delete risk rule"""
    existing = await risk_rule_service.get_risk_rule_by_id(db, rule_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Risk rule not found: {rule_id}")
    success = await risk_rule_service.delete_risk_rule(db, rule_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete risk rule")
