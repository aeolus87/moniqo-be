"""
Position Management Router

FastAPI endpoints for position management using clean architecture.
Router → Service → Repository → Database
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from decimal import Decimal

from app.core.dependencies import get_current_user
from app.domain.models.position import Position, PositionStatus, PositionSide
from app.modules.positions.service import PositionService
from app.modules.positions.repository import PositionRepository, get_position_repository
from app.modules.positions.schemas import (
    ClosePositionRequest,
    UpdatePositionRequest,
    PositionResponse,
    PositionListResponse,
    ClosePositionResponse,
    EntryDataResponse,
    CurrentDataResponse,
    RiskManagementResponse,
    ExitDataResponse,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/positions", tags=["positions"])


def _position_to_response(position: Position) -> PositionResponse:
    """
    Convert Position domain model to PositionResponse schema.
    
    Args:
        position: Position domain model
        
    Returns:
        PositionResponse schema
    """
    # Convert entry dict
    entry_dict = dict(position.entry)
    entry_dict.setdefault("leverage", Decimal("1"))
    entry_dict.setdefault("margin_used", entry_dict.get("value", Decimal("0")))
    if "order_id" in entry_dict:
        entry_dict["order_id"] = str(entry_dict["order_id"])
    
    # Convert current dict
    current_data = None
    if position.current:
        current_dict = dict(position.current)
        current_data = CurrentDataResponse(**current_dict)
    
    # Convert risk management dict
    risk_dict = dict(position.risk_management)
    if risk_dict.get("current_stop_loss") is None and risk_dict.get("stop_loss") is not None:
        risk_dict["current_stop_loss"] = risk_dict.get("stop_loss")
    if risk_dict.get("current_take_profit") is None and risk_dict.get("take_profit") is not None:
        risk_dict["current_take_profit"] = risk_dict.get("take_profit")
    
    # Convert exit dict
    exit_data = None
    if position.exit:
        exit_dict = dict(position.exit)
        if "order_id" in exit_dict:
            exit_dict["order_id"] = str(exit_dict["order_id"])
        exit_data = ExitDataResponse(**exit_dict)
    
    return PositionResponse(
        id=str(position.id) if position.id else "",
        user_id=str(position.user_id),
        user_wallet_id=str(position.user_wallet_id),
        flow_id=str(position.flow_id) if position.flow_id else None,
        symbol=position.symbol,
        side=position.side.value,
        status=position.status.value,
        entry=EntryDataResponse(**entry_dict),
        current=current_data,
        risk_management=RiskManagementResponse(**risk_dict),
        exit=exit_data,
        statistics=position.statistics,
        created_at=position.created_at,
        opened_at=position.opened_at,
        closed_at=position.closed_at,
        updated_at=position.updated_at,
    )


# ==================== GET POSITION ====================

@router.get("/{position_id}", response_model=PositionResponse)
async def get_position(
    position_id: str,
    current_user: dict = Depends(get_current_user),
    repo: PositionRepository = Depends(get_position_repository),
):
    """Get position by ID."""
    service = PositionService(repository=repo)
    
    position = await service.get_position(position_id)
    
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found"
        )
    
    # Verify position belongs to user
    if str(position.user_id) != str(current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return _position_to_response(position)


# ==================== LIST POSITIONS ====================

@router.get("/", response_model=PositionListResponse)
async def list_positions(
    current_user: dict = Depends(get_current_user),
    status: Optional[str] = Query(None, description="Filter by status"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    repo: PositionRepository = Depends(get_position_repository),
):
    """List positions for current user."""
    service = PositionService(repository=repo)
    
    positions = await service.get_user_positions(
        user_id=str(current_user["_id"]),
        status=status,
        symbol=symbol,
        skip=skip,
        limit=limit,
    )
    
    total = await repo.count_by_user(
        user_id=str(current_user["_id"]),
        status=status,
        symbol=symbol,
    )
    
    return PositionListResponse(
        positions=[_position_to_response(pos) for pos in positions],
        total=total,
        page=(skip // limit) + 1 if limit > 0 else 1,
        page_size=limit,
    )


# ==================== GET OPEN POSITIONS ====================

@router.get("/open/list", response_model=PositionListResponse)
async def get_open_positions(
    current_user: dict = Depends(get_current_user),
    repo: PositionRepository = Depends(get_position_repository),
):
    """Get all open positions for current user."""
    service = PositionService(repository=repo)
    
    positions = await service.get_open_positions(str(current_user["_id"]))
    
    return PositionListResponse(
        positions=[_position_to_response(pos) for pos in positions],
        total=len(positions),
        page=1,
        page_size=len(positions),
    )


# ==================== CLOSE POSITION ====================

@router.post("/{position_id}/close", response_model=ClosePositionResponse)
async def close_position(
    position_id: str,
    request: ClosePositionRequest,
    current_user: dict = Depends(get_current_user),
    repo: PositionRepository = Depends(get_position_repository),
):
    """Close a position."""
    service = PositionService(repository=repo)
    
    # Verify position belongs to user
    position = await service.get_position(position_id)
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found"
        )
    
    if str(position.user_id) != str(current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # For now, we need order_id and price from request
    # In a real implementation, this would create a close order first
    # For this migration, we'll use placeholder values
    # TODO: Integrate with order creation flow
    
    if not position.exit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot close position without exit order. Create exit order first."
        )
    
    exit_order_id = position.exit.get("order_id", "")
    exit_price = Decimal(str(position.exit.get("price", 0)))
    
    position = await service.close_position(
        position_id=position_id,
        order_id=exit_order_id,
        price=exit_price,
        reason=request.reason or "manual",
    )
    
    realized_pnl = Decimal("0")
    realized_pnl_percent = Decimal("0")
    if position.exit:
        realized_pnl = Decimal(str(position.exit.get("realized_pnl", 0)))
        realized_pnl_percent = Decimal(str(position.exit.get("realized_pnl_percent", 0)))
    
    return ClosePositionResponse(
        success=True,
        message="Position closed successfully",
        position_id=str(position.id),
        realized_pnl=realized_pnl,
        realized_pnl_percent=realized_pnl_percent,
    )
