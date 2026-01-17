"""
Position Management Router

FastAPI endpoints for position management.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timezone
from decimal import Decimal
from bson import ObjectId

from app.core.dependencies import get_current_user
from app.config.database import get_database
from app.modules.positions.models import Position, PositionStatus, PositionSide
from app.modules.positions.schemas import (
    ClosePositionRequest,
    UpdatePositionRequest,
    PositionResponse,
    PositionListResponse,
    ClosePositionResponse,
    EntryDataResponse,
    CurrentDataResponse,
    RiskManagementResponse,
    ExitDataResponse
)
from app.services.position_tracker import get_position_tracker
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/positions", tags=["positions"])


# ==================== GET POSITION ====================

@router.get("/{position_id}", response_model=PositionResponse)
async def get_position(
    position_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get position by ID"""
    try:
        user_id = current_user["_id"]
        
        position = await Position.get(position_id)
        
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
        
        # Verify position belongs to user
        if str(position.user_id) != str(user_id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Convert to response
        return PositionResponse(
            id=str(position.id),
            user_id=str(position.user_id),
            user_wallet_id=str(position.user_wallet_id),
            flow_id=str(position.flow_id) if position.flow_id else None,
            symbol=position.symbol,
            side=position.side.value,
            status=position.status.value,
            entry=EntryDataResponse(**position.entry),
            current=CurrentDataResponse(**position.current) if position.current else None,
            risk_management=RiskManagementResponse(**position.risk_management) if position.risk_management else RiskManagementResponse(),
            exit=ExitDataResponse(**position.exit) if position.exit else None,
            statistics=position.statistics,
            created_at=position.created_at,
            opened_at=position.opened_at,
            closed_at=position.closed_at,
            updated_at=position.updated_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting position: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== LIST POSITIONS ====================

@router.get("/", response_model=PositionListResponse)
async def list_positions(
    status: Optional[PositionStatus] = Query(None, description="Filter by status"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size"),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """List positions for current user"""
    try:
        user_id = current_user["_id"]
        
        # Build query
        query = Position.find(Position.user_id == ObjectId(user_id) if isinstance(user_id, str) else user_id)
        
        if status:
            query = query.find(Position.status == status)
        
        if symbol:
            query = query.find(Position.symbol == symbol)
        
        # Get total count
        total = await query.count()
        
        # Paginate
        skip = (page - 1) * page_size
        positions = await query.skip(skip).limit(page_size).sort(-Position.opened_at if Position.opened_at else -Position.created_at).to_list()
        
        # Convert to response
        position_responses = [
            PositionResponse(
                id=str(position.id),
                user_id=str(position.user_id),
                user_wallet_id=str(position.user_wallet_id),
                flow_id=str(position.flow_id) if position.flow_id else None,
                symbol=position.symbol,
                side=position.side.value,
                status=position.status.value,
                entry=EntryDataResponse(**position.entry),
                current=CurrentDataResponse(**position.current) if position.current else None,
                risk_management=RiskManagementResponse(**position.risk_management) if position.risk_management else RiskManagementResponse(),
                exit=ExitDataResponse(**position.exit) if position.exit else None,
                statistics=position.statistics,
                created_at=position.created_at,
                opened_at=position.opened_at,
                closed_at=position.closed_at,
                updated_at=position.updated_at
            )
            for position in positions
        ]
        
        return PositionListResponse(
            positions=position_responses,
            total=total,
            page=page,
            page_size=page_size
        )
    
    except Exception as e:
        logger.error(f"Error listing positions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== UPDATE POSITION ====================

@router.patch("/{position_id}", response_model=PositionResponse)
async def update_position(
    position_id: str,
    request: UpdatePositionRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Update position (stop loss, take profit, etc.)"""
    try:
        user_id = current_user["_id"]
        
        position = await Position.get(position_id)
        
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
        
        # Verify position belongs to user
        if str(position.user_id) != str(user_id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check if position is open
        if not position.is_open():
            raise HTTPException(
                status_code=400,
                detail=f"Position cannot be updated. Current status: {position.status.value}"
            )
        
        # Initialize risk_management if not exists
        if not position.risk_management:
            position.risk_management = {}
        
        # Update stop loss
        if request.stop_loss is not None:
            position.risk_management["current_stop_loss"] = float(request.stop_loss)
            
            # Also set initial if not set
            if "initial_stop_loss" not in position.risk_management:
                position.risk_management["initial_stop_loss"] = float(request.stop_loss)
        
        # Update take profit
        if request.take_profit is not None:
            position.risk_management["current_take_profit"] = float(request.take_profit)
            
            # Also set initial if not set
            if "initial_take_profit" not in position.risk_management:
                position.risk_management["initial_take_profit"] = float(request.take_profit)
        
        # Update metadata
        if request.metadata:
            if "metadata" not in position.metadata:
                position.metadata = {}
            position.metadata.update(request.metadata)
        
        position.updated_at = datetime.now(timezone.utc)
        await position.save()
        
        logger.info(f"Position {position_id} updated by user {user_id}")
        
        # Return updated position
        return PositionResponse(
            id=str(position.id),
            user_id=str(position.user_id),
            user_wallet_id=str(position.user_wallet_id),
            flow_id=str(position.flow_id) if position.flow_id else None,
            symbol=position.symbol,
            side=position.side.value,
            status=position.status.value,
            entry=EntryDataResponse(**position.entry),
            current=CurrentDataResponse(**position.current) if position.current else None,
            risk_management=RiskManagementResponse(**position.risk_management),
            exit=ExitDataResponse(**position.exit) if position.exit else None,
            statistics=position.statistics,
            created_at=position.created_at,
            opened_at=position.opened_at,
            closed_at=position.closed_at,
            updated_at=position.updated_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating position: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CLOSE POSITION ====================

@router.post("/{position_id}/close", response_model=ClosePositionResponse)
async def close_position(
    position_id: str,
    request: ClosePositionRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Manually close an open position"""
    try:
        user_id = current_user["_id"]
        
        position = await Position.get(position_id)
        
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
        
        # Verify position belongs to user
        if str(position.user_id) != str(user_id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check if position is open
        if not position.is_open():
            raise HTTPException(
                status_code=400,
                detail=f"Position cannot be closed. Current status: {position.status.value}"
            )
        
        # Get current price
        tracker_service = await get_position_tracker(db)
        
        # Monitor position to get latest price
        monitor_result = await tracker_service.monitor_position(str(position.id))
        
        if not monitor_result["success"]:
            raise HTTPException(status_code=500, detail="Failed to get current price")
        
        current_price = Decimal(str(monitor_result.get("current_price", position.entry["price"])))
        
        # Close position
        reason = request.reason or "manual_close"
        await position.close(
            order_id=position.id,  # TODO: Use actual exit order ID
            price=current_price,
            reason=reason,
            fees=Decimal("0")  # TODO: Calculate actual fees
        )
        
        logger.info(f"Position {position_id} closed by user {user_id}")
        
        return ClosePositionResponse(
            success=True,
            message="Position closed successfully",
            position_id=str(position.id),
            realized_pnl=position.exit["realized_pnl"],
            realized_pnl_percent=position.exit["realized_pnl_percent"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing position: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== MONITOR POSITION ====================

@router.post("/{position_id}/monitor")
async def monitor_position(
    position_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Manually trigger position monitoring"""
    try:
        user_id = current_user["_id"]
        
        position = await Position.get(position_id)
        
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
        
        # Verify position belongs to user
        if str(position.user_id) != str(user_id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Monitor position
        tracker_service = await get_position_tracker(db)
        result = await tracker_service.monitor_position(position_id)
        
        return {
            "success": result["success"],
            "message": result.get("message", "Position monitored"),
            "current_price": result.get("current_price"),
            "unrealized_pnl": result.get("unrealized_pnl"),
            "unrealized_pnl_percent": result.get("unrealized_pnl_percent"),
            "risk_level": result.get("risk_level")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error monitoring position: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


