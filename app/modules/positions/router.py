"""
Position Management Router

FastAPI endpoints for position management.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

from typing import List, Optional, Any, Dict
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


async def _get_demo_user_id(db) -> Optional[ObjectId]:
    auth = await db["auth"].find_one({"email": "demo@moniqo.com", "is_deleted": False})
    if not auth:
        return None
    user = await db["users"].find_one({"auth_id": auth["_id"], "is_deleted": False})
    if not user:
        return None
    return user["_id"]



# ==================== GET POSITION ====================

@router.get("/{position_id}", response_model=PositionResponse)
async def get_position(
    position_id: str,
    current_user: Optional[dict] = Depends(get_current_user_optional),
    db = Depends(get_database)
):
    """Get position by ID"""
    try:
        if current_user:
            user_id = current_user["_id"]
        else:
            demo_user_id = await _get_demo_user_id(db)
            if not demo_user_id:
                raise HTTPException(status_code=401, detail="Not authenticated")
            user_id = demo_user_id
        
        # Normalize user_id to ObjectId for comparison
        user_id_obj = ObjectId(user_id) if isinstance(user_id, str) else user_id
        
        position = await Position.get(position_id)
        
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
        
        # Check if position has user_id
        if not position.user_id:
            logger.error(f"Position {position_id} missing user_id")
            raise HTTPException(status_code=500, detail="Position is missing user_id. Please contact support.")
        
        # Normalize position.user_id to ObjectId for comparison
        position_user_id = ObjectId(position.user_id) if isinstance(position.user_id, str) else position.user_id
        
        # Verify position belongs to user
        if position_user_id != user_id_obj:
            logger.warning(
                f"Access denied for position {position_id}: "
                f"position.user_id={position_user_id} != user_id={user_id_obj}"
            )
            raise HTTPException(status_code=403, detail="Access denied")
        
        if position.is_open():
            # Always update if current is missing or doesn't have price
            if not position.current or not position.current.get("price"):
                needs_update = True
            else:
                last_updated = position.current.get("last_updated")
                needs_update = False
                
                if not last_updated:
                    needs_update = True
                elif isinstance(last_updated, datetime):
                    if last_updated.tzinfo is None:
                        last_updated = last_updated.replace(tzinfo=timezone.utc)
                    time_since_update = (datetime.now(timezone.utc) - last_updated).total_seconds()
                    if time_since_update > 30:
                        needs_update = True
                else:
                    needs_update = True
            
            if needs_update:
                try:
                    tracker_service = await get_position_tracker(db)
                    await tracker_service.monitor_position(str(position.id))
                    await position.reload()
                except Exception as e:
                    logger.warning(f"Failed to update position {position.id} during get: {e}")
        
        try:
            entry_data = position.entry or {}
            entry_dict = dict(entry_data)
            if "order_id" in entry_dict and isinstance(entry_dict["order_id"], ObjectId):
                entry_dict["order_id"] = str(entry_dict["order_id"])
            entry_dict.setdefault("leverage", Decimal("1"))
            entry_dict.setdefault("margin_used", entry_dict.get("value", Decimal("0")))
            
            risk_data = position.risk_management or {}
            risk_dict = dict(risk_data)
            if risk_dict.get("current_stop_loss") is None and risk_dict.get("stop_loss") is not None:
                risk_dict["current_stop_loss"] = risk_dict.get("stop_loss")
            if risk_dict.get("current_take_profit") is None and risk_dict.get("take_profit") is not None:
                risk_dict["current_take_profit"] = risk_dict.get("take_profit")
            
            exit_dict = None
            if position.exit:
                exit_dict = dict(position.exit)
                if "order_id" in exit_dict and isinstance(exit_dict["order_id"], ObjectId):
                    exit_dict["order_id"] = str(exit_dict["order_id"])
            
            return PositionResponse(
                id=str(position.id),
                user_id=str(position.user_id) if position.user_id else "",
                user_wallet_id=str(position.user_wallet_id) if position.user_wallet_id else "",
                flow_id=str(position.flow_id) if position.flow_id else None,
                symbol=position.symbol,
                side=position.side.value,
                status=position.status.value,
                entry=EntryDataResponse(**entry_dict),
                current=CurrentDataResponse(**position.current) if position.current else None,
                risk_management=RiskManagementResponse(**risk_dict),
                exit=ExitDataResponse(**exit_dict) if exit_dict else None,
                statistics=position.statistics,
                created_at=position.created_at,
                opened_at=position.opened_at,
                closed_at=position.closed_at,
                updated_at=position.updated_at
            )
        except (AttributeError, KeyError) as e:
            logger.error(f"Position {position_id} has invalid data: {e}")
            raise HTTPException(status_code=500, detail=f"Position data is corrupted: missing {e}")
    
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
        user_id = None
        if current_user and "_id" in current_user:
            user_id = current_user["_id"]
        else:
            auth = await db["auth"].find_one({"email": "demo@moniqo.com", "is_deleted": False})
            if not auth:
                return PositionListResponse(positions=[], total=0, page=page, page_size=page_size)
            user = await db["users"].find_one({"auth_id": auth["_id"], "is_deleted": False})
            if not user:
                return PositionListResponse(positions=[], total=0, page=page, page_size=page_size)
            user_id = user.get("_id")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        user_id_obj = ObjectId(user_id) if isinstance(user_id, str) else user_id
        
        # Build query filter
        query_filter = {"user_id": user_id_obj, "deleted_at": None}
        if status:
            query_filter["status"] = status.value
        if symbol:
            query_filter["symbol"] = symbol
        
        query = Position.find(query_filter)
        total = await query.count()
        skip = (page - 1) * page_size
        # Sort by created_at descending (opened_at may be None for some positions)
        positions = await query.skip(skip).limit(page_size).sort("-created_at").to_list()
        
        position_responses = []
        tracker_service = await get_position_tracker(db)
        
        for position in positions:
            try:
                if position.is_open():
                    # Always update if current is missing or doesn't have price
                    if not position.current or not position.current.get("price"):
                        needs_update = True
                    else:
                        last_updated = position.current.get("last_updated")
                        needs_update = False
                        
                        if not last_updated:
                            needs_update = True
                        else:
                            if isinstance(last_updated, datetime):
                                if last_updated.tzinfo is None:
                                    last_updated = last_updated.replace(tzinfo=timezone.utc)
                                time_since_update = (datetime.now(timezone.utc) - last_updated).total_seconds()
                                if time_since_update > 30:
                                    needs_update = True
                            else:
                                needs_update = True
                    
                    if needs_update:
                        try:
                            await tracker_service.monitor_position(str(position.id))
                            await position.reload()
                        except Exception as e:
                            logger.warning(f"Failed to update position {position.id} during list: {e}")
                
                entry_data = position.entry or {}
                entry_dict = dict(entry_data)
                if "order_id" in entry_dict and isinstance(entry_dict["order_id"], ObjectId):
                    entry_dict["order_id"] = str(entry_dict["order_id"])
                entry_dict.setdefault("leverage", Decimal("1"))
                entry_dict.setdefault("margin_used", entry_dict.get("value", Decimal("0")))
                
                risk_data = position.risk_management or {}
                risk_dict = dict(risk_data)
                if risk_dict.get("current_stop_loss") is None and risk_dict.get("stop_loss") is not None:
                    risk_dict["current_stop_loss"] = risk_dict.get("stop_loss")
                if risk_dict.get("current_take_profit") is None and risk_dict.get("take_profit") is not None:
                    risk_dict["current_take_profit"] = risk_dict.get("take_profit")
                
                exit_dict = None
                if position.exit:
                    exit_dict = dict(position.exit)
                    if "order_id" in exit_dict and isinstance(exit_dict["order_id"], ObjectId):
                        exit_dict["order_id"] = str(exit_dict["order_id"])
                
                position_responses.append(
                    PositionResponse(
                        id=str(position.id),
                        user_id=str(position.user_id) if position.user_id else "",
                        user_wallet_id=str(position.user_wallet_id) if position.user_wallet_id else "",
                        flow_id=str(position.flow_id) if position.flow_id else None,
                        symbol=position.symbol,
                        side=position.side.value,
                        status=position.status.value,
                        entry=EntryDataResponse(**entry_dict),
                        current=CurrentDataResponse(**position.current) if position.current else None,
                        risk_management=RiskManagementResponse(**risk_dict),
                        exit=ExitDataResponse(**exit_dict) if exit_dict else None,
                        statistics=position.statistics,
                        created_at=position.created_at,
                        opened_at=position.opened_at,
                        closed_at=position.closed_at,
                        updated_at=position.updated_at
                    )
                )
            except (AttributeError, KeyError) as e:
                logger.warning(f"Skipping malformed position {position.id}: {e}")
                continue
        
        return PositionListResponse(
            positions=position_responses,
            total=total,
            page=page,
            page_size=page_size
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing positions: {str(e)}", exc_info=True)
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
        
        # Normalize user_id to ObjectId for comparison
        user_id_obj = ObjectId(user_id) if isinstance(user_id, str) else user_id
        
        position = await Position.get(position_id)
        
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
        
        # Check if position has user_id
        if not position.user_id:
            logger.error(f"Position {position_id} missing user_id")
            raise HTTPException(status_code=500, detail="Position is missing user_id. Please contact support.")
        
        # Normalize position.user_id to ObjectId for comparison
        position_user_id = ObjectId(position.user_id) if isinstance(position.user_id, str) else position.user_id
        
        # Verify position belongs to user
        if position_user_id != user_id_obj:
            logger.warning(
                f"Access denied for position {position_id}: "
                f"position.user_id={position_user_id} != user_id={user_id_obj}"
            )
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
        
        entry_data = position.entry or {}
        entry_dict = dict(entry_data)
        if "order_id" in entry_dict and isinstance(entry_dict["order_id"], ObjectId):
            entry_dict["order_id"] = str(entry_dict["order_id"])
        entry_dict.setdefault("leverage", Decimal("1"))
        entry_dict.setdefault("margin_used", entry_dict.get("value", Decimal("0")))
        
        risk_data = position.risk_management or {}
        risk_dict = dict(risk_data)
        if risk_dict.get("current_stop_loss") is None and risk_dict.get("stop_loss") is not None:
            risk_dict["current_stop_loss"] = risk_dict.get("stop_loss")
        if risk_dict.get("current_take_profit") is None and risk_dict.get("take_profit") is not None:
            risk_dict["current_take_profit"] = risk_dict.get("take_profit")
        
        exit_dict = None
        if position.exit:
            exit_dict = dict(position.exit)
            if "order_id" in exit_dict and isinstance(exit_dict["order_id"], ObjectId):
                exit_dict["order_id"] = str(exit_dict["order_id"])
        
        return PositionResponse(
            id=str(position.id),
            user_id=str(position.user_id),
            user_wallet_id=str(position.user_wallet_id),
            flow_id=str(position.flow_id) if position.flow_id else None,
            symbol=position.symbol,
            side=position.side.value,
            status=position.status.value,
            entry=EntryDataResponse(**entry_dict),
            current=CurrentDataResponse(**position.current) if position.current else None,
            risk_management=RiskManagementResponse(**risk_dict),
            exit=ExitDataResponse(**exit_dict) if exit_dict else None,
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
    current_user: Optional[dict] = Depends(get_current_user_optional),
    db = Depends(get_database)
):
    """Manually close an open position"""
    try:
        if current_user:
            user_id = current_user["_id"]
        else:
            demo_user_id = await _get_demo_user_id(db)
            if not demo_user_id:
                raise HTTPException(status_code=401, detail="Not authenticated")
            user_id = demo_user_id
        
        # Normalize user_id to ObjectId for comparison
        user_id_obj = ObjectId(user_id) if isinstance(user_id, str) else user_id
        
        position = await Position.get(position_id)
        
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
        
        # Check if position has user_id
        if not position.user_id:
            logger.error(f"Position {position_id} missing user_id")
            raise HTTPException(status_code=500, detail="Position is missing user_id. Please contact support.")
        
        # Normalize position.user_id to ObjectId for comparison
        position_user_id = ObjectId(position.user_id) if isinstance(position.user_id, str) else position.user_id
        
        if position_user_id != user_id_obj:
            logger.warning(
                f"Access denied for position {position_id}: "
                f"position.user_id={position_user_id} (type: {type(position_user_id)}) != "
                f"user_id={user_id_obj} (type: {type(user_id_obj)})"
            )
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not position.is_open():
            raise HTTPException(status_code=400, detail=f"Position cannot be closed. Current status: {position.status.value}")
        
        # Check if position already has exit data (already closed)
        if position.exit:
            raise HTTPException(
                status_code=400, 
                detail="Position already has exit data and cannot be closed again"
            )
        
        entry_data = position.entry
        if not entry_data:
            raise HTTPException(status_code=500, detail="Position entry data missing")
        
        if "value" not in entry_data:
            entry_price = Decimal(str(entry_data.get("price")))
            entry_amount = Decimal(str(entry_data.get("amount")))
            entry_data["value"] = entry_price * entry_amount
            position.entry = entry_data
            await position.save()

        tracker_service = await get_position_tracker(db)
        current_price = None
        user_wallet_id = position.user_wallet_id
        
        if user_wallet_id:
            monitor_result = await tracker_service.monitor_position(str(position.id))
            if monitor_result["success"]:
                current_price = monitor_result.get("current_price")
        
        if current_price is None:
            current_data = position.current
            current_price = current_data.get("price") if current_data else entry_data.get("price")
        
        if current_price is None:
            raise HTTPException(status_code=500, detail="Current price unavailable")
        
        current_price = Decimal(str(current_price))
        reason = request.reason or "manual_close"
        
        # Check if position already has an exit transaction
        existing_exit_transaction = await db["transactions"].find_one({
            "position_id": position.id,
            "type": "sell" if position.side == PositionSide.LONG else "buy",
            "status": "filled"
        })
        
        if existing_exit_transaction:
            raise HTTPException(
                status_code=400, 
                detail="Position already has a completed exit transaction and cannot be closed again"
            )
        
        await position.close(
            order_id=position.id,
            price=current_price,
            reason=reason,
            fees=Decimal("0")
        )
        
        # Reload position to get updated exit data
        position = await Position.get(position_id)
        if not position or not position.exit:
            raise HTTPException(status_code=500, detail="Failed to close position - exit data not set")
        
        try:
            await tracker_service._record_transaction(
                position=position,
                reason=reason,
                price=current_price,
                fee=Decimal("0"),
                fee_currency="USDT",
                order_id=None,
                status="filled",
            )
        except Exception as e:
            logger.warning(f"Failed to record close transaction for position {position_id}: {e}")
        
        # Update demo wallet balance with realized P&L
        if position.user_wallet_id:
            try:
                from app.integrations.wallets.factory import get_wallet_factory
                factory = get_wallet_factory()
                wallet = await factory.create_wallet_from_db(db, str(position.user_wallet_id))
                
                # Check if it's a demo wallet
                if hasattr(wallet, 'add_balance'):
                    realized_pnl = position.exit.get("realized_pnl", Decimal("0"))
                    if realized_pnl != 0:
                        # Add realized P&L to wallet balance (positive or negative)
                        await wallet.add_balance(
                            asset="USDT",
                            amount=realized_pnl,
                            is_cash=True
                        )
                        logger.info(
                            f"Added realized P&L {realized_pnl} USDT to demo wallet "
                            f"{position.user_wallet_id} for position {position_id}"
                        )
            except Exception as e:
                logger.warning(
                    f"Failed to update demo wallet balance with P&L for position {position_id}: {e}"
                )
        
        realized_pnl = position.exit.get("realized_pnl", Decimal("0"))
        realized_pnl_percent = position.exit.get("realized_pnl_percent", Decimal("0"))
        
        logger.info(f"Position {position_id} closed by user {user_id}")
        
        return ClosePositionResponse(
            success=True,
            message="Position closed successfully",
            position_id=str(position_id),
            realized_pnl=realized_pnl,
            realized_pnl_percent=realized_pnl_percent
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error closing position")
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
        
        # Normalize user_id to ObjectId for comparison
        user_id_obj = ObjectId(user_id) if isinstance(user_id, str) else user_id
        
        position = await Position.get(position_id)
        
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
        
        # Check if position has user_id
        if not position.user_id:
            logger.error(f"Position {position_id} missing user_id")
            raise HTTPException(status_code=500, detail="Position is missing user_id. Please contact support.")
        
        # Normalize position.user_id to ObjectId for comparison
        position_user_id = ObjectId(position.user_id) if isinstance(position.user_id, str) else position.user_id
        
        # Verify position belongs to user
        if position_user_id != user_id_obj:
            logger.warning(
                f"Access denied for position {position_id}: "
                f"position.user_id={position_user_id} != user_id={user_id_obj}"
            )
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
