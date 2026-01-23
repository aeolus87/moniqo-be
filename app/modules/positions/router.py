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
from app.integrations.market_data.binance_client import BinanceClient
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


def _coerce_entry_payload(entry: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(entry or {})
    order_id = payload.get("order_id")
    if isinstance(order_id, ObjectId):
        payload["order_id"] = str(order_id)
    payload.setdefault("leverage", 1)
    payload.setdefault("margin_used", payload.get("value", 0))
    return payload


def _coerce_exit_payload(exit: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not exit:
        return None
    payload = dict(exit)
    order_id = payload.get("order_id")
    if isinstance(order_id, ObjectId):
        payload["order_id"] = str(order_id)
    return payload


def _coerce_risk_management(risk_management: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    payload = dict(risk_management or {})
    if payload.get("current_stop_loss") is None and payload.get("stop_loss") is not None:
        payload["current_stop_loss"] = payload.get("stop_loss")
    if payload.get("current_take_profit") is None and payload.get("take_profit") is not None:
        payload["current_take_profit"] = payload.get("take_profit")
    return payload


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
        
        doc = None
        try:
            position = await Position.get(position_id)
        except Exception as beanie_error:
            # Use debug level - fallback to raw MongoDB works fine
            logger.debug(f"Beanie get failed, using raw MongoDB fallback: {beanie_error}")
            position = None
        
        if not position:
            doc = await db.positions.find_one({"_id": ObjectId(position_id), "deleted_at": None})
            if not doc:
                raise HTTPException(status_code=404, detail="Position not found")
        
        # Verify position belongs to user
        if position:
            if str(position.user_id) != str(user_id):
                raise HTTPException(status_code=403, detail="Access denied")
        else:
            if str(doc.get("user_id")) != str(user_id):
                raise HTTPException(status_code=403, detail="Access denied")
        
        if position:
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
            
            entry_payload = _coerce_entry_payload(position.entry or {})
            risk_payload = _coerce_risk_management(position.risk_management)
            exit_payload = _coerce_exit_payload(position.exit)
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
                risk_management=RiskManagementResponse(**risk_payload) if position.risk_management else RiskManagementResponse(),
                exit=ExitDataResponse(**exit_payload) if exit_payload else None,
                statistics=position.statistics,
                created_at=position.created_at,
                opened_at=position.opened_at,
                closed_at=position.closed_at,
                updated_at=position.updated_at
            )

        entry_payload = _coerce_entry_payload(doc.get("entry") or {})
        risk_payload = _coerce_risk_management(doc.get("risk_management"))
        exit_payload = _coerce_exit_payload(doc.get("exit"))
        user_wallet_id = doc.get("user_wallet_id")
        return PositionResponse(
            id=str(doc.get("_id")),
            user_id=str(doc.get("user_id")),
            user_wallet_id=str(user_wallet_id) if user_wallet_id else "",
            flow_id=str(doc.get("flow_id")) if doc.get("flow_id") else None,
            symbol=doc.get("symbol", ""),
            side=doc.get("side", ""),
            status=doc.get("status", ""),
            entry=EntryDataResponse(**entry_payload),
            current=CurrentDataResponse(**doc.get("current", {})) if doc.get("current") else None,
            risk_management=RiskManagementResponse(**risk_payload) if doc.get("risk_management") else RiskManagementResponse(),
            exit=ExitDataResponse(**exit_payload) if exit_payload else None,
            statistics=doc.get("statistics", {}),
            created_at=doc.get("created_at"),
            opened_at=doc.get("opened_at"),
            closed_at=doc.get("closed_at"),
            updated_at=doc.get("updated_at")
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
        if current_user:
            user_id = current_user["_id"]
        else:
            auth = await db["auth"].find_one({"email": "demo@moniqo.com", "is_deleted": False})
            if not auth:
                return PositionListResponse(positions=[], total=0, page=page, page_size=page_size)
            user = await db["users"].find_one({"auth_id": auth["_id"], "is_deleted": False})
            if not user:
                return PositionListResponse(positions=[], total=0, page=page, page_size=page_size)
            user_id = user["_id"]
        
        user_id_obj = ObjectId(user_id) if isinstance(user_id, str) else user_id
        
        try:
            query = Position.find(
                Position.user_id == user_id_obj,
                Position.deleted_at == None
            )
            
            if status:
                query = query.find(Position.status == status)
            if symbol:
                query = query.find(Position.symbol == symbol)
            
            total = await query.count()
            skip = (page - 1) * page_size
            positions = await query.skip(skip).limit(page_size).sort(-Position.opened_at if Position.opened_at else -Position.created_at).to_list()
        except Exception as beanie_error:
            # Use debug level - fallback to raw MongoDB works fine
            logger.debug(f"Beanie query failed, using raw MongoDB fallback: {beanie_error}")
            query_dict = {"user_id": user_id_obj, "deleted_at": None}
            if status:
                query_dict["status"] = status.value if hasattr(status, 'value') else str(status)
            if symbol:
                query_dict["symbol"] = symbol
            
            total = await db.positions.count_documents(query_dict)
            skip = (page - 1) * page_size
            cursor = db.positions.find(query_dict).skip(skip).limit(page_size).sort("opened_at", -1)
            raw_positions = await cursor.to_list(length=page_size)
            
            position_responses = []
            tracker_service = await get_position_tracker(db)
            
            for doc in raw_positions:
                try:
                    position_status = doc.get("status")
                    is_open = position_status == PositionStatus.OPEN.value
                    
                    if is_open:
                        current_data = doc.get("current", {})
                        # Always update if current is missing or doesn't have price
                        if not current_data or not current_data.get("price"):
                            needs_update = True
                        else:
                            last_updated = current_data.get("last_updated")
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
                                await tracker_service.monitor_position(str(doc.get("_id")))
                                doc = await db.positions.find_one({"_id": doc.get("_id")})
                            except Exception as e:
                                logger.warning(f"Failed to update position {doc.get('_id')} during list: {e}")
                    
                    entry_payload = _coerce_entry_payload(doc.get("entry") or {})
                    risk_payload = _coerce_risk_management(doc.get("risk_management"))
                    exit_payload = _coerce_exit_payload(doc.get("exit"))
                    user_wallet_id = doc.get("user_wallet_id")
                    
                    position_responses.append(
                        PositionResponse(
                            id=str(doc.get("_id")),
                            user_id=str(doc.get("user_id")),
                            user_wallet_id=str(user_wallet_id) if user_wallet_id else "",
                            flow_id=str(doc.get("flow_id")) if doc.get("flow_id") else None,
                            symbol=doc.get("symbol", ""),
                            side=doc.get("side", ""),
                            status=doc.get("status", ""),
                            entry=EntryDataResponse(**entry_payload),
                            current=CurrentDataResponse(**doc.get("current", {})) if doc.get("current") else None,
                            risk_management=RiskManagementResponse(**risk_payload) if doc.get("risk_management") else RiskManagementResponse(),
                            exit=ExitDataResponse(**exit_payload) if exit_payload else None,
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
        
        position_responses = []
        tracker_service = await get_position_tracker(db)
        
        for position in positions:
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
            
            entry_payload = _coerce_entry_payload(position.entry or {})
            risk_payload = _coerce_risk_management(position.risk_management)
            exit_payload = _coerce_exit_payload(position.exit)
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
                    risk_management=RiskManagementResponse(**risk_payload) if position.risk_management else RiskManagementResponse(),
                    exit=ExitDataResponse(**exit_payload) if exit_payload else None,
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
        
        entry_payload = _coerce_entry_payload(position.entry or {})
        risk_payload = _coerce_risk_management(position.risk_management)
        exit_payload = _coerce_exit_payload(position.exit)
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
            risk_management=RiskManagementResponse(**risk_payload),
            exit=ExitDataResponse(**exit_payload) if exit_payload else None,
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
        
        try:
            position = await Position.get(position_id)
            doc = None
        except Exception:
            position = None
            doc = await db.positions.find_one({"_id": ObjectId(position_id), "deleted_at": None})
            if not doc:
                raise HTTPException(status_code=404, detail="Position not found")
        
        position_user_id = str(position.user_id) if position else str(doc.get("user_id"))
        if position_user_id != str(user_id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        if position and not position.is_open():
            raise HTTPException(status_code=400, detail=f"Position cannot be closed. Current status: {position.status.value}")
        if doc and doc.get("status") != PositionStatus.OPEN.value:
            raise HTTPException(status_code=400, detail=f"Position cannot be closed. Current status: {doc.get('status')}")
        
        entry_data = position.entry if position else (doc.get("entry") or {})
        if not entry_data:
            raise HTTPException(status_code=500, detail="Position entry data missing")
        
        if "value" not in entry_data:
            entry_price = Decimal(str(entry_data.get("price")))
            entry_amount = Decimal(str(entry_data.get("amount")))
            entry_data["value"] = entry_price * entry_amount
            if position:
                position.entry = entry_data
                await position.save()
            else:
                await db.positions.update_one(
                    {"_id": ObjectId(position_id)},
                    {"$set": {"entry.value": float(entry_data["value"])}},
                )

        tracker_service = await get_position_tracker(db)
        current_price = None
        user_wallet_id = position.user_wallet_id if position else doc.get("user_wallet_id")
        
        if user_wallet_id and position:
            monitor_result = await tracker_service.monitor_position(str(position.id))
            if monitor_result["success"]:
                current_price = monitor_result.get("current_price")
        
        if current_price is None:
            current_data = position.current if position else doc.get("current")
            current_price = current_data.get("price") if current_data else entry_data.get("price")
        
        if current_price is None:
            raise HTTPException(status_code=500, detail="Current price unavailable")
        
        current_price = Decimal(str(current_price))
        reason = request.reason or "manual_close"
        
        if position:
            await position.close(
                order_id=position.id,
                price=current_price,
                reason=reason,
                fees=Decimal("0")
            )
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
            
            realized_pnl = position.exit["realized_pnl"]
            realized_pnl_percent = position.exit["realized_pnl_percent"]
        else:
            exit_data = {
                "order_id": str(position_id),
                "timestamp": datetime.now(timezone.utc),
                "price": float(current_price),
                "amount": float(entry_data.get("amount", 0)),
                "value": float(Decimal(str(entry_data.get("amount", 0))) * current_price),
                "fees": 0.0,
                "fee_currency": "USDT",
                "reason": reason,
                "realized_pnl": 0.0,
                "realized_pnl_percent": 0.0,
                "time_held_minutes": 0,
            }
            await db.positions.update_one(
                {"_id": ObjectId(position_id)},
                {
                    "$set": {
                        "status": PositionStatus.CLOSED.value,
                        "closed_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                        "exit": exit_data,
                    }
                },
            )
            realized_pnl = exit_data.get("realized_pnl", 0)
            realized_pnl_percent = exit_data.get("realized_pnl_percent", 0)
        
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
