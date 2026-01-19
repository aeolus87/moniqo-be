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

from app.core.dependencies import get_current_user, get_current_user_optional
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
        entry_payload = dict(position.entry or {})
        entry_payload.setdefault("leverage", 1)
        entry_payload.setdefault("margin_used", entry_payload.get("value", 0))
        return PositionResponse(
            id=str(position.id),
            user_id=str(position.user_id),
            user_wallet_id=str(position.user_wallet_id),
            flow_id=str(position.flow_id) if position.flow_id else None,
            symbol=position.symbol,
            side=position.side.value,
            status=position.status.value,
            entry=EntryDataResponse(**entry_payload),
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

@router.get("", response_model=PositionListResponse)
async def list_positions(
    status: Optional[PositionStatus] = Query(None, description="Filter by status"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size"),
    current_user: Optional[dict] = Depends(get_current_user_optional),
    db = Depends(get_database)
):
    """List positions for current user (or demo user if not authenticated)"""
    try:
        # If authenticated, use authenticated user_id
        # Otherwise, use demo user for demo mode
        if current_user:
            user_id = current_user["_id"]
        else:
            # Get demo user for unauthenticated requests (demo mode)
            auth = await db["auth"].find_one({"email": "demo@moniqo.com", "is_deleted": False})
            if not auth:
                # Return empty list if no demo user exists
                return PositionListResponse(
                    positions=[],
                    total=0,
                    page=page,
                    page_size=page_size
                )
            user = await db["users"].find_one({"auth_id": auth["_id"], "is_deleted": False})
            if not user:
                return PositionListResponse(
                    positions=[],
                    total=0,
                    page=page,
                    page_size=page_size
                )
            user_id = user["_id"]
        
        user_id_obj = ObjectId(user_id) if isinstance(user_id, str) else user_id
        
        # Build query - try Beanie first, fallback to raw MongoDB if needed
        try:
            # Beanie query - filter by user_id and deleted_at
            query = Position.find(
                Position.user_id == user_id_obj,
                Position.deleted_at == None
            )
            
            if status:
                query = query.find(Position.status == status)
            
            if symbol:
                query = query.find(Position.symbol == symbol)
            
            # Get total count
            total = await query.count()
            
            # Paginate
            skip = (page - 1) * page_size
            positions = await query.skip(skip).limit(page_size).sort(-Position.opened_at if Position.opened_at else -Position.created_at).to_list()
        except Exception as beanie_error:
            # Fallback to raw MongoDB query if Beanie fails
            logger.warning(f"Beanie query failed, using raw MongoDB: {beanie_error}")
            query_dict = {"user_id": user_id_obj, "deleted_at": None}
            if status:
                query_dict["status"] = status.value if hasattr(status, 'value') else str(status)
            if symbol:
                query_dict["symbol"] = symbol
            
            total = await db.positions.count_documents(query_dict)
            skip = (page - 1) * page_size
            cursor = db.positions.find(query_dict).skip(skip).limit(page_size).sort("opened_at", -1)
            raw_positions = await cursor.to_list(length=page_size)
            
            # Build response directly from raw docs (handles None values for user_wallet_id)
            position_responses = []
            for doc in raw_positions:
                try:
                    entry_payload = dict(doc.get("entry") or {})
                    entry_payload.setdefault("leverage", 1)
                    entry_payload.setdefault("margin_used", entry_payload.get("value", 0))
                    
                    # Handle user_wallet_id - can be None for simulated positions
                    user_wallet_id = doc.get("user_wallet_id")
                    if user_wallet_id is None:
                        # Use a placeholder or empty string for simulated positions
                        user_wallet_id_str = ""
                    else:
                        user_wallet_id_str = str(user_wallet_id)
                    
                    position_responses.append(
                        PositionResponse(
                            id=str(doc.get("_id")),
                            user_id=str(doc.get("user_id")),
                            user_wallet_id=user_wallet_id_str,
                            flow_id=str(doc.get("flow_id")) if doc.get("flow_id") else None,
                            symbol=doc.get("symbol", ""),
                            side=doc.get("side", ""),
                            status=doc.get("status", ""),
                            entry=EntryDataResponse(**entry_payload),
                            current=CurrentDataResponse(**doc.get("current", {})) if doc.get("current") else None,
                            risk_management=RiskManagementResponse(**doc.get("risk_management", {})) if doc.get("risk_management") else RiskManagementResponse(),
                            exit=ExitDataResponse(**doc.get("exit", {})) if doc.get("exit") else None,
                            statistics=doc.get("statistics", {}),
                            created_at=doc.get("created_at"),   
                            opened_at=doc.get("opened_at"),
                            closed_at=doc.get("closed_at"),
                            updated_at=doc.get("updated_at")
                        )
                    )
                except Exception as e:
                    logger.warning(f"Failed to convert position doc {doc.get('_id')}: {e}")
                    continue
            
            return PositionListResponse(
                positions=position_responses,
                total=total,
                page=page,
                page_size=page_size
            )
        
        # Convert to response (Beanie path)
        position_responses = []
        for position in positions:
            entry_payload = dict(position.entry or {})
            entry_payload.setdefault("leverage", 1)
            entry_payload.setdefault("margin_used", entry_payload.get("value", 0))
            position_responses.append(
                PositionResponse(
                    id=str(position.id),
                    user_id=str(position.user_id),
                    user_wallet_id=str(position.user_wallet_id) if position.user_wallet_id else "",
                    flow_id=str(position.flow_id) if position.flow_id else None,
                    symbol=position.symbol,
                    side=position.side.value if hasattr(position.side, 'value') else str(position.side),
                    status=position.status.value if hasattr(position.status, 'value') else str(position.status),
                    entry=EntryDataResponse(**entry_payload),
                    current=CurrentDataResponse(**position.current) if position.current else None,
                    risk_management=RiskManagementResponse(**position.risk_management) if position.risk_management else RiskManagementResponse(),
                    exit=ExitDataResponse(**position.exit) if position.exit else None,
                    statistics=position.statistics,
                    created_at=position.created_at,
                    opened_at=position.opened_at,
                    closed_at=position.closed_at,
                    updated_at=position.updated_at
                )
            )
        
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

        await tracker_service._record_transaction(
            position=position,
            reason=reason,
            price=current_price,
            fee=Decimal("0"),
            fee_currency="USDT",
            order_id=None,
            status="filled",
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
