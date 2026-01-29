"""
Position Tracking Service

Monitors open positions, updates P&L in real-time, and manages risk.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.modules.positions.models import Position, PositionStatus, PositionSide, PositionUpdate
from app.modules.flows.models import FlowStatus
from app.integrations.wallets.base import OrderSide, OrderType, TimeInForce
from app.integrations.wallets.factory import create_wallet_from_db
from app.modules.ai_agents.monitor_agent import MonitorAgent
from app.services.signal_aggregator import get_signal_aggregator
from app.integrations.market_data.binance_client import BinanceClient
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PositionTrackerService:
    """
    Position Tracking Service
    
    Monitors open positions, updates P&L in real-time,
    manages stop loss/take profit, and tracks risk metrics.
    
    Features:
    - Real-time price updates
    - P&L calculation (unrealized & realized)
    - Stop loss/take profit monitoring
    - Risk level tracking
    - Position update logging
    
    Usage:
        tracker = PositionTrackerService(db)
        
        # Update position price
        await tracker.update_position_price(position_id, current_price)
        
        # Monitor all open positions
        await tracker.monitor_all_positions()
        
        # Check stop loss/take profit
        await tracker.check_stop_loss_take_profit(position)
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize position tracker service.
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.signal_aggregator = get_signal_aggregator()
        
        logger.info("Position tracker service initialized")
    
    async def _is_flow_active(self, position: Position) -> bool:
        """Check if the position's associated flow is active."""
        if not position.flow_id:
            # Positions without flow_id should still be monitored (legacy/orphaned)
            return True
        
        try:
            from app.modules.flows import service as flow_service
            flow = await flow_service.get_flow_by_id(self.db, str(position.flow_id))
            if not flow:
                # Flow not found - allow monitoring (orphaned position)
                return True
            return flow.status == FlowStatus.ACTIVE
        except Exception as e:
            logger.warning(f"Failed to check flow status for position {position.id}: {e}")
            # On error, allow monitoring (fail open)
            return True
    
    async def update_position_price(
        self,
        position_id: str,
        current_price: Decimal
    ) -> Dict[str, Any]:
        """
        Update position with current market price.
        
        Args:
            position_id: Position ID
            current_price: Current market price
            
        Returns:
            Dict with update result
        """
        try:
            # Get position
            position = await Position.get(position_id)
            
            if not position:
                return {
                    "success": False,
                    "error": "Position not found"
                }
            
            if not position.is_open():
                return {
                    "success": False,
                    "error": "Position is not open"
                }
            
            # Check if flow is active before updating
            if position.flow_id:
                if not await self._is_flow_active(position):
                    logger.debug(f"Skipping price update for position {position_id} - flow is inactive")
                    return {
                        "success": True,
                        "message": "Flow is inactive - price update skipped",
                        "skipped": True
                    }
            
            # Update price
            await position.update_price(current_price)
            
            # Create position update log
            update = PositionUpdate(
                position_id=position.id,
                price=current_price,
                unrealized_pnl=position.current["unrealized_pnl"],
                unrealized_pnl_percent=position.current["unrealized_pnl_percent"]
            )
            await update.insert()
            
            # Check stop loss/take profit
            await self.check_stop_loss_take_profit(position)
            
            # Emit Socket.IO update (only if position has user_id)
            if position.user_id:
                try:
                    # Import here to avoid circular import
                    import sys
                    if 'app.main' in sys.modules:
                        from app.main import sio
                        entry = position.entry or {}
                        risk = position.risk_management or {}
                        await sio.emit('position_update', {
                            'id': str(position.id),
                            'symbol': position.symbol,
                            'side': position.side.value,
                            'entry_price': float(entry.get("price", 0)),
                            'current_price': float(current_price),
                            'quantity': float(entry.get("amount", 0)),
                            'unrealized_pnl': float(position.current["unrealized_pnl"]),
                            'realized_pnl': 0,
                            'status': position.status.value,
                            'stop_loss': float(risk.get("current_stop_loss") or risk.get("stop_loss") or 0) or None,
                            'take_profit': float(risk.get("current_take_profit") or risk.get("take_profit") or 0) or None,
                            'updated_at': position.current["last_updated"].isoformat() if isinstance(position.current.get("last_updated"), datetime) else datetime.now(timezone.utc).isoformat()
                        }, room=f'positions:{position.user_id}')
                except Exception as e:
                    logger.warning(f"Failed to emit position update via Socket.IO: {e}")
            
            return {
                "success": True,
                "position_id": str(position.id),
                "current_price": float(current_price),
                "unrealized_pnl": float(position.current["unrealized_pnl"]),
                "unrealized_pnl_percent": float(position.current["unrealized_pnl_percent"]),
                "risk_level": position.current["risk_level"]
            }
        
        except Exception as e:
            logger.error(f"Error updating position price: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def monitor_position(self, position_id: str) -> Dict[str, Any]:
        """
        Monitor a single position (get current price and update).
        
        Args:
            position_id: Position ID
            
        Returns:
            Dict with monitoring result
        """
        try:
            try:
                position = await Position.get(position_id)
            except Exception as e:
                error_str = str(e).lower()
                # Don't log warnings for expected errors:
                # - "not found" / "does not exist" - positions get deleted regularly
                # - Schema validation errors (e.g., missing user_id) - handled via raw MongoDB fallback
                if "not found" not in error_str and "does not exist" not in error_str:
                    # Check if position exists but has schema mismatch (e.g., None user_id)
                    doc_check = await self.db["positions"].find_one({"_id": ObjectId(position_id)})
                    if doc_check:
                        # Position exists but Beanie can't load it - schema mismatch, use debug level
                        logger.debug(f"Beanie schema mismatch for position {position_id}, using raw MongoDB fallback")
                    else:
                        # Position truly doesn't exist
                        logger.debug(f"Position {position_id} not found in database")
                position = None

            if not position:
                doc = await self.db["positions"].find_one({"_id": ObjectId(position_id), "deleted_at": None})
                if not doc:
                    # Don't log warnings for missing positions - this is normal
                    return {
                        "success": False,
                        "error": "Position not found"
                    }

                status = doc.get("status")
                if status not in {PositionStatus.OPEN.value, PositionStatus.OPENING.value}:
                    return {
                        "success": True,
                        "message": "Position is not open",
                        "status": status
                    }

                # Check if flow is active before monitoring (raw MongoDB path)
                flow_id = doc.get("flow_id")
                if flow_id:
                    try:
                        from app.modules.flows import service as flow_service
                        flow = await flow_service.get_flow_by_id(self.db, str(flow_id))
                        if flow and flow.status != FlowStatus.ACTIVE:
                            logger.debug(f"Skipping monitoring for position {position_id} - flow is inactive")
                            return {
                                "success": True,
                                "message": "Flow is inactive - monitoring skipped",
                                "skipped": True
                            }
                    except Exception as e:
                        logger.warning(f"Failed to check flow status for position {position_id}: {e}")
                        # On error, continue monitoring (fail open)

                symbol = doc.get("symbol")
                current_price = None

                user_wallet_id = doc.get("user_wallet_id")
                if user_wallet_id:
                    try:
                        wallet_instance = await create_wallet_from_db(self.db, str(user_wallet_id))
                        current_price = await wallet_instance.get_market_price(symbol)
                    except Exception as e:
                        logger.warning(f"Failed to get price from wallet for position {position_id}: {e}")

                if current_price is None:
                    async with BinanceClient() as binance_client:
                        current_price = await binance_client.get_price(symbol)
                        if current_price is None:
                            return {
                                "success": False,
                                "error": "Failed to get market price"
                            }

                entry = doc.get("entry", {})
                entry_price = Decimal(str(entry.get("price", 0)))
                entry_amount = Decimal(str(entry.get("amount", 0)))
                entry_value = Decimal(str(entry.get("value", 0)))
                entry_fees = Decimal(str(entry.get("fees", 0)))

                current_price = Decimal(str(current_price))
                current_value = entry_amount * current_price
                if doc.get("side") == PositionSide.LONG.value:
                    unrealized_pnl = (current_price - entry_price) * entry_amount
                else:
                    unrealized_pnl = (entry_price - current_price) * entry_amount
                unrealized_pnl -= entry_fees
                unrealized_pnl_percent = (unrealized_pnl / entry_value * 100) if entry_value > 0 else Decimal("0")

                current = doc.get("current") or {}
                high_water_mark = Decimal(str(current.get("high_water_mark", current_price)))
                low_water_mark = Decimal(str(current.get("low_water_mark", current_price)))
                high_water_mark = max(high_water_mark, current_price)
                low_water_mark = min(low_water_mark, current_price)
                max_drawdown_percent = Decimal("0")
                if high_water_mark > 0:
                    max_drawdown_percent = (high_water_mark - low_water_mark) / high_water_mark * Decimal("100")

                def _risk_level(pnl_percent: Decimal) -> str:
                    if pnl_percent < Decimal("-10"):
                        return "critical"
                    if pnl_percent < Decimal("-5"):
                        return "high"
                    if pnl_percent < Decimal("-2"):
                        return "medium"
                    if pnl_percent < Decimal("0"):
                        return "low"
                    return "low"

                now = datetime.now(timezone.utc)
                opened_at = doc.get("opened_at")
                time_held_minutes = current.get("time_held_minutes", 0)
                if isinstance(opened_at, datetime):
                    # Ensure opened_at is timezone-aware and in UTC
                    if opened_at.tzinfo is None:
                        # Naive datetime - assume UTC
                        opened_at = opened_at.replace(tzinfo=timezone.utc)
                    else:
                        # Timezone-aware datetime - convert to UTC
                        opened_at = opened_at.astimezone(timezone.utc)
                    # Now both are UTC-aware, safe to subtract
                    time_held_minutes = int((now - opened_at).total_seconds() / 60)
                current_update = {
                    "price": float(current_price),
                    "value": float(current_value),
                    "unrealized_pnl": float(unrealized_pnl),
                    "unrealized_pnl_percent": float(unrealized_pnl_percent),
                    "risk_level": _risk_level(unrealized_pnl_percent),
                    "time_held_minutes": time_held_minutes,
                    "high_water_mark": float(high_water_mark),
                    "low_water_mark": float(low_water_mark),
                    "max_drawdown_percent": float(max_drawdown_percent),
                    "last_updated": now,
                }

                await self.db["positions"].update_one(
                    {"_id": doc.get("_id")},
                    {
                        "$set": {
                            "current": current_update,
                            "updated_at": now,
                        }
                    },
                )

                try:
                    import sys
                    if "app.main" in sys.modules:
                        from app.main import sio
                        # Fix: Get user_id from position, or fallback to flow's user_id, or use 'system'
                        user_id = doc.get("user_id")

                        # If position doesn't have user_id, try to get it from the flow
                        # and also fix the position document for future queries
                        if not user_id:
                            flow_id = doc.get("flow_id")
                            if flow_id:
                                try:
                                    flow_doc = await self.db["flows"].find_one({"_id": ObjectId(flow_id)})
                                    if flow_doc:
                                        user_id = flow_doc.get("config", {}).get("user_id") or flow_doc.get("user_id")
                                        if user_id:
                                            logger.debug(f"Retrieved user_id {user_id} from flow {flow_id} for position {doc.get('_id')}")
                                            # Fix the position document for future queries
                                            try:
                                                await self.db["positions"].update_one(
                                                    {"_id": doc.get("_id")},
                                                    {"$set": {"user_id": ObjectId(str(user_id))}}
                                                )
                                                logger.info(f"Fixed missing user_id for position {doc.get('_id')}")
                                            except Exception as fix_error:
                                                logger.debug(f"Could not fix user_id for position {doc.get('_id')}: {fix_error}")
                                except Exception as e:
                                    logger.debug(f"Failed to get user_id from flow {flow_id}: {e}")

                        # Skip socket emission if no user_id - use debug level since migration script will fix these
                        if not user_id:
                            logger.debug(f"Position {doc.get('_id')} has no user_id - skipping socket emission (run migration script to fix)")
                        else:
                            user_id_str = str(user_id)
                            room = f"positions:{user_id_str}"
                            entry = doc.get("entry", {})
                            risk = doc.get("risk_management", {})

                            update_data = {
                                "id": str(doc.get("_id")),
                                "symbol": symbol,
                                "side": doc.get("side"),
                                "entry_price": float(entry.get("price", 0)),
                                "current_price": float(current_price),
                                "quantity": float(entry.get("amount", 0)),
                                "unrealized_pnl": float(unrealized_pnl),
                                "realized_pnl": 0,
                                "status": doc.get("status", "open"),
                                "stop_loss": float(risk.get("current_stop_loss") or risk.get("stop_loss") or 0) or None,
                                "take_profit": float(risk.get("current_take_profit") or risk.get("take_profit") or 0) or None,
                                "updated_at": now.isoformat(),
                            }
                            logger.info(f"Emitting position_update to room {room} for position {doc.get('_id')}")
                            await sio.emit("position_update", update_data, room=room)
                            logger.debug(f"Position update emitted: {update_data}")
                except Exception as e:
                    logger.error(f"Failed to emit position update via Socket.IO: {e}", exc_info=True)

                return {
                    "success": True,
                    "position_id": str(doc.get("_id")),
                    "current_price": float(current_price),
                    "unrealized_pnl": float(unrealized_pnl),
                    "unrealized_pnl_percent": float(unrealized_pnl_percent),
                    "risk_level": current_update["risk_level"],
                }
            
            if not position.is_open():
                return {
                    "success": True,
                    "message": "Position is not open",
                    "status": position.status.value
                }
            
            # Check if flow is active before monitoring (Beanie path)
            if position.flow_id:
                if not await self._is_flow_active(position):
                    logger.debug(f"Skipping monitoring for position {position_id} - flow is inactive")
                    return {
                        "success": True,
                        "message": "Flow is inactive - monitoring skipped",
                        "skipped": True
                    }
            
            current_price = None
            
            if position.user_wallet_id:
                try:
                    wallet_instance = await create_wallet_from_db(self.db, str(position.user_wallet_id))
                    current_price = await wallet_instance.get_market_price(position.symbol)
                except Exception as e:
                    logger.warning(f"Failed to get price from wallet for position {position_id}: {e}")
            
            if current_price is None:
                async with BinanceClient() as binance_client:
                    current_price = await binance_client.get_price(position.symbol)
                    if current_price is None:
                        return {
                            "success": False,
                            "error": "Failed to get market price"
                        }
            
            # Update position
            result = await self.update_position_price(str(position.id), current_price)
            
            # Skip AI monitoring if flow is inactive
            if result.get("skipped"):
                return result

            try:
                base_symbol = position.symbol.split("/")[0] if "/" in position.symbol else position.symbol
                signal_data = (await self.signal_aggregator.get_signal(base_symbol.upper())).to_dict()

                monitor_agent = MonitorAgent(
                    model_provider=position.ai_monitoring.get("model_provider", "groq")
                    if position.ai_monitoring else "groq"
                )
                monitor_result = await monitor_agent.process({
                    "positions": [
                        {
                            "id": str(position.id),
                            "symbol": position.symbol,
                            "side": position.side.value,
                            "entry_price": position.entry.get("price"),
                            "current_price": float(current_price),
                            "unrealized_pnl": float(position.current.get("unrealized_pnl", 0)),
                            "unrealized_pnl_percent": float(position.current.get("unrealized_pnl_percent", 0)),
                            "risk_level": position.current.get("risk_level"),
                            "stop_loss": position.risk_management.get("current_stop_loss"),
                            "take_profit": position.risk_management.get("current_take_profit"),
                        }
                    ],
                    "market_data": {
                        "summary": signal_data.get("classification"),
                        "signal": signal_data,
                    },
                })

                position.ai_monitoring = position.ai_monitoring or {}
                position.ai_monitoring["last_signal"] = signal_data
                position.ai_monitoring["last_ai_review"] = {
                    "timestamp": datetime.now(timezone.utc),
                    "result": monitor_result,
                }
                await position.save()

                await self._apply_ai_recommendations(position, monitor_result)

                for rec in monitor_result.get("recommendations", []):
                    if rec.get("position_id") == str(position.id) and rec.get("action") in ["close", "exit"]:
                        # Refresh position from database to avoid race conditions
                        refreshed_position = await Position.get(str(position.id))
                        if not refreshed_position or not refreshed_position.is_open():
                            logger.debug(f"Position {position.id} is no longer open, skipping AI close recommendation")
                            break
                        
                        if refreshed_position.user_wallet_id:
                            try:
                                wallet_instance = await create_wallet_from_db(self.db, str(refreshed_position.user_wallet_id))
                                await self._close_position_with_order(
                                    position=refreshed_position,
                                    wallet=wallet_instance,
                                    reason=rec.get("reason", "ai_signal"),
                                )
                            except Exception as e:
                                logger.warning(f"Failed to close position via wallet: {e}")
                        break
            except Exception as e:
                logger.error(f"AI monitoring failed for position {position_id}: {str(e)}")
            
            return result
        
        except Exception as e:
            logger.error(f"Error monitoring position {position_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def monitor_all_positions(self) -> Dict[str, Any]:
        """
        Monitor all open positions in the system.
        
        Returns:
            Dict with monitoring results
        """
        try:
            position_ids: List[str] = []
            try:
                positions = await Position.find(
                    Position.status == PositionStatus.OPEN,
                    Position.deleted_at == None
                ).to_list()
                position_ids = [str(position.id) for position in positions]
            except Exception as e:
                # Use debug level - fallback to raw MongoDB works fine
                logger.debug(f"Beanie query failed, using raw MongoDB fallback: {e}")
                cursor = self.db["positions"].find({
                    "status": PositionStatus.OPEN.value,
                    "deleted_at": None,
                })
                docs = await cursor.to_list(length=None)
                position_ids = [str(doc.get("_id")) for doc in docs if doc.get("_id")]
            
            results = {
                "success": True,
                "total_positions": len(position_ids),
                "updated": 0,
                "errors": 0,
                "not_found": 0,
                "closed": 0,
                "details": []
            }

            # Monitor each position
            for position_id in position_ids:
                try:
                    result = await self.monitor_position(position_id)

                    if result["success"]:
                        results["updated"] += 1
                    else:
                        error_msg = result.get("error", "")
                        if error_msg == "Position not found":
                            results["not_found"] += 1
                            logger.info(f"Position {position_id} not found in DB - removing from monitoring")
                        elif result.get("message") == "Position is not open":
                            results["closed"] += 1
                            logger.debug(f"Position {position_id} is closed - skipping")
                        else:
                            results["errors"] += 1

                    results["details"].append({
                        "position_id": position_id,
                        "result": result
                    })

                except Exception as e:
                    results["errors"] += 1
                    results["details"].append({
                        "position_id": position_id,
                        "error": str(e)
                    })
            
            return results
        
        except Exception as e:
            logger.error(f"Error monitoring all positions: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def check_stop_loss_take_profit(self, position: Position) -> Dict[str, Any]:
        """
        Check if stop loss or take profit should be triggered.
        
        Args:
            position: Position instance
            
        Returns:
            Dict with check result
        """
        try:
            if not position.is_open():
                return {
                    "success": False,
                    "error": "Position is not open"
                }
            
            # Check if flow is active before checking stop loss/take profit
            if position.flow_id:
                if not await self._is_flow_active(position):
                    logger.debug(f"Skipping SL/TP check for position {position.id} - flow is inactive")
                    return {
                        "success": True,
                        "triggered": None,
                        "skipped": True,
                        "reason": "Flow is inactive"
                    }
            
            if not position.current:
                return {
                    "success": False,
                    "error": "Position has no current data"
                }
            
            current_price = position.current["price"]
            risk_mgmt = position.risk_management or {}
            
            # Check stop loss
            current_stop_loss = risk_mgmt.get("current_stop_loss")
            if current_stop_loss:
                stop_loss_price = Decimal(str(current_stop_loss))
                
                if position.side == PositionSide.LONG:
                    # Long: trigger if price drops below stop loss
                    if current_price <= stop_loss_price:
                        await self._trigger_stop_loss(position, current_price)
                        return {
                            "success": True,
                            "triggered": "stop_loss",
                            "price": float(current_price),
                            "stop_loss_price": float(stop_loss_price)
                        }
                else:  # SHORT
                    # Short: trigger if price rises above stop loss
                    if current_price >= stop_loss_price:
                        await self._trigger_stop_loss(position, current_price)
                        return {
                            "success": True,
                            "triggered": "stop_loss",
                            "price": float(current_price),
                            "stop_loss_price": float(stop_loss_price)
                        }
            
            # Check take profit
            current_take_profit = risk_mgmt.get("current_take_profit")
            if current_take_profit:
                take_profit_price = Decimal(str(current_take_profit))
                
                if position.side == PositionSide.LONG:
                    # Long: trigger if price rises above take profit
                    if current_price >= take_profit_price:
                        await self._trigger_take_profit(position, current_price)
                        return {
                            "success": True,
                            "triggered": "take_profit",
                            "price": float(current_price),
                            "take_profit_price": float(take_profit_price)
                        }
                else:  # SHORT
                    # Short: trigger if price drops below take profit
                    if current_price <= take_profit_price:
                        await self._trigger_take_profit(position, current_price)
                        return {
                            "success": True,
                            "triggered": "take_profit",
                            "price": float(current_price),
                            "take_profit_price": float(take_profit_price)
                        }
            
            # Check trailing stop
            trailing_stop = risk_mgmt.get("trailing_stop")
            if trailing_stop and trailing_stop.get("enabled"):
                await self._update_trailing_stop(position, current_price, trailing_stop)
            
            # Check break-even
            break_even = risk_mgmt.get("break_even")
            if break_even and break_even.get("enabled"):
                await self._check_break_even(position, current_price, break_even)
            
            return {
                "success": True,
                "triggered": None
            }
        
        except Exception as e:
            logger.error(f"Error checking stop loss/take profit: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _trigger_stop_loss(self, position: Position, current_price: Decimal):
        """Trigger stop loss for position"""
        try:
            # Refresh position from database to avoid race conditions
            refreshed_position = await Position.get(str(position.id))
            if not refreshed_position or not refreshed_position.is_open():
                logger.debug(f"Position {position.id} is no longer open, skipping stop loss trigger")
                return
            
            if not refreshed_position.user_wallet_id:
                logger.error(f"Cannot trigger stop loss: position {position.id} has no user_wallet_id")
                return
            
            wallet_instance = await create_wallet_from_db(self.db, str(refreshed_position.user_wallet_id))
            
            # Use centralized close method which handles order placement, fees, PnL recording, and flow statistics
            await self._close_position_with_order(
                position=refreshed_position,
                wallet=wallet_instance,
                reason="Stop Loss Triggered"
            )
            
            logger.info(f"Stop loss triggered for position {position.id}")
        
        except Exception as e:
            logger.error(f"Error triggering stop loss: {str(e)}")
    
    async def _trigger_take_profit(self, position: Position, current_price: Decimal):
        """Trigger take profit for position"""
        try:
            # Refresh position from database to avoid race conditions
            refreshed_position = await Position.get(str(position.id))
            if not refreshed_position or not refreshed_position.is_open():
                logger.debug(f"Position {position.id} is no longer open, skipping take profit trigger")
                return
            
            if not refreshed_position.user_wallet_id:
                logger.error(f"Cannot trigger take profit: position {position.id} has no user_wallet_id")
                return
            
            wallet_instance = await create_wallet_from_db(self.db, str(refreshed_position.user_wallet_id))
            
            # Use centralized close method which handles order placement, fees, PnL recording, and flow statistics
            await self._close_position_with_order(
                position=refreshed_position,
                wallet=wallet_instance,
                reason="Take Profit Triggered"
            )
            
            logger.info(f"Take profit triggered for position {position.id}")
        
        except Exception as e:
            logger.error(f"Error triggering take profit: {str(e)}")
    
    async def _update_trailing_stop(
        self,
        position: Position,
        current_price: Decimal,
        trailing_stop_config: Dict[str, Any]
    ):
        """Update trailing stop based on current price"""
        try:
            entry_price = Decimal(str(position.entry["price"]))
            distance_percent = Decimal(str(trailing_stop_config.get("distance_percent", 2.0)))
            activation_price = Decimal(str(trailing_stop_config.get("activation_price", entry_price)))
            
            # Check if trailing stop should activate
            if position.side == PositionSide.LONG:
                if current_price >= activation_price:
                    # Calculate new trailing stop
                    new_stop = current_price * (Decimal("1") - distance_percent / Decimal("100"))
                    current_stop = Decimal(str(position.risk_management.get("current_stop_loss", 0)))
                    
                    # Only move stop up (for long positions)
                    if new_stop > current_stop:
                        position.risk_management["current_stop_loss"] = float(new_stop)
                        
                        # Update trailing stop config
                        if not position.risk_management.get("trailing_stop"):
                            position.risk_management["trailing_stop"] = {}
                        
                        position.risk_management["trailing_stop"]["current_trigger"] = float(new_stop)
                        position.risk_management["trailing_stop"]["adjusted_count"] = (
                            position.risk_management["trailing_stop"].get("adjusted_count", 0) + 1
                        )
                        position.risk_management["trailing_stop"]["last_adjusted"] = datetime.now(timezone.utc)
                        
                        await position.save()
            
            else:  # SHORT
                if current_price <= activation_price:
                    # Calculate new trailing stop (above current price for short)
                    new_stop = current_price * (Decimal("1") + distance_percent / Decimal("100"))
                    current_stop = Decimal(str(position.risk_management.get("current_stop_loss", float("inf"))))
                    
                    # Only move stop down (for short positions)
                    if new_stop < current_stop or current_stop == 0:
                        position.risk_management["current_stop_loss"] = float(new_stop)
                        
                        if not position.risk_management.get("trailing_stop"):
                            position.risk_management["trailing_stop"] = {}
                        
                        position.risk_management["trailing_stop"]["current_trigger"] = float(new_stop)
                        position.risk_management["trailing_stop"]["adjusted_count"] = (
                            position.risk_management["trailing_stop"].get("adjusted_count", 0) + 1
                        )
                        position.risk_management["trailing_stop"]["last_adjusted"] = datetime.now(timezone.utc)
                        
                        await position.save()
        
        except Exception as e:
            logger.error(f"Error updating trailing stop: {str(e)}")
    
    async def _check_break_even(
        self,
        position: Position,
        current_price: Decimal,
        break_even_config: Dict[str, Any]
    ):
        """Check and update break-even stop loss"""
        try:
            if break_even_config.get("activated"):
                return  # Already activated
            
            entry_price = Decimal(str(position.entry["price"]))
            activation_profit_percent = Decimal(str(break_even_config.get("activation_profit_percent", 1.0)))
            
            # Calculate profit percentage
            if position.side == PositionSide.LONG:
                profit_percent = ((current_price - entry_price) / entry_price) * Decimal("100")
            else:  # SHORT
                profit_percent = ((entry_price - current_price) / entry_price) * Decimal("100")
            
            # Check if activation threshold reached
            if profit_percent >= activation_profit_percent:
                # Move stop loss to break-even (entry price)
                position.risk_management["current_stop_loss"] = float(entry_price)
                position.risk_management["break_even"]["activated"] = True
                position.risk_management["break_even"]["activated_at"] = datetime.now(timezone.utc)
                
                await position.save()
                
                logger.info(f"Break-even stop loss activated for position {position.id}")
        
        except Exception as e:
            logger.error(f"Error checking break-even: {str(e)}")

    async def _close_position_with_order(
        self,
        position: Position,
        wallet,
        reason: str,
    ) -> None:
        """
        Place a market order to close the position and persist exit data.
        
        Implements "Dust Fix" to handle fee-reduced balances:
        1. Fetches real available balance from exchange API
        2. Applies lot-size/step-size rounding
        3. Checks minimum notional value ($10)
        4. Handles dust amounts below minimum by closing position without order
        """
        if not position.is_open():
            return

        close_side = OrderSide.SELL if position.side == PositionSide.LONG else OrderSide.BUY
        
        # Extract base symbol (e.g., "BTC/USDT" → "BTC")
        base_symbol = position.symbol.split("/")[0] if "/" in position.symbol else position.symbol
        
        # Fetch real available balance from exchange (Dust Fix Step 1)
        try:
            available_balance = await wallet.get_balance(base_symbol)
            logger.info(f"Fetched real balance for {base_symbol}: {available_balance}")
        except Exception as e:
            logger.error(f"Failed to fetch balance for {base_symbol}: {e}")
            # Fallback to database amount if balance fetch fails
            available_balance = Decimal(str(position.entry.get("amount", 0)))
        
        if available_balance <= 0:
            logger.warning(f"No available balance for {base_symbol}, position may already be closed")
            return
        
        # Round quantity to exchange lot-size/step-size (Dust Fix Step 2)
        if hasattr(wallet, 'format_quantity'):
            rounded_quantity = wallet.format_quantity(position.symbol, available_balance)
        else:
            # Fallback: round down to 8 decimal places (crypto standard)
            rounded_quantity = available_balance.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
        
        if rounded_quantity <= 0:
            logger.warning(f"Rounded quantity is 0 for {base_symbol}, skipping order")
            return
        
        # Get current price for minimum notional check (Dust Fix Step 3)
        try:
            current_price = await wallet.get_market_price(position.symbol)
        except Exception as e:
            logger.error(f"Failed to fetch price for {position.symbol}: {e}")
            # Use position's current price as fallback
            current_price = Decimal(str(position.current.get("price", 0)))
        
        if current_price <= 0:
            logger.error(f"Cannot determine current price for {position.symbol}")
            return
        
        # Calculate notional value and check minimum (Dust Fix Step 4)
        minimum_notional = Decimal("10.00")  # Default $10 minimum (exchange standard)
        notional_value = rounded_quantity * current_price
        
        # Check if dust (below minimum notional) (Dust Fix Step 5)
        if notional_value < minimum_notional:
            logger.info(
                f"Position closed; remaining dust {rounded_quantity} {base_symbol} "
                f"(${float(notional_value):.2f}) is below exchange minimum ${minimum_notional}"
            )
            
            # Close position without placing order - dust amount too small to trade
            await position.close(
                order_id=position.id,
                price=current_price,
                reason=f"{reason} (dust below minimum)",
                fees=Decimal("0"),
            )
            
            await self._record_transaction(
                position=position,
                reason=f"{reason} (dust)",
                price=current_price,
                fee=Decimal("0"),
                fee_currency="USDT",
                order_id=None,
                status="closed_dust",
            )
            
            # RecordLearning - happens before EndCycle
            await self._record_learning_outcome(position, f"{reason} (dust)")
            
            # Update flow statistics with realized P&L (UpdateFlowStats step)
            # Note: increment_executions=False because execution was already counted when it completed
            if position.flow_id:
                try:
                    from app.modules.flows import service as flow_service
                    await flow_service._update_flow_statistics(
                        db=self.db,
                        flow_id=str(position.flow_id),
                        position_id=str(position.id),
                        execution_completed=True,
                        completed_at=datetime.now(timezone.utc),
                        increment_executions=False,  # Don't double-count executions
                    )
                except Exception as e:
                    logger.error(f"Failed to update flow statistics after dust close: {e}")
            
            # Trigger flow continuation - EndCycle --> WaitTrigger
            await self._trigger_flow_continuation(str(position.flow_id))
            return
        
        # Use real rounded quantity for order (Dust Fix Step 6)
        quantity = rounded_quantity
        logger.info(f"Placing close order: {quantity} {base_symbol} (notional: ${float(notional_value):.2f})")

        order_result = await wallet.place_order(
            symbol=position.symbol,
            side=close_side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            time_in_force=TimeInForce.GTC,
        )

        exit_price = order_result.get("average_price") or order_result.get("price")
        exit_price = Decimal(str(exit_price)) if exit_price else Decimal(str(position.current.get("price", 0)))
        fee = Decimal(str(order_result.get("fee", 0))) if order_result.get("fee") else Decimal("0")
        fee_currency = order_result.get("fee_currency", "USDT")

        exit_order_id = order_result.get("order_id") or str(position.id)
        await position.close(
            order_id=exit_order_id,
            price=exit_price,
            reason=reason,
            fees=fee,
            fee_currency=fee_currency,
        )

        await self._record_transaction(
            position=position,
            reason=reason,
            price=exit_price,
            fee=fee,
            fee_currency=fee_currency,
            order_id=order_result.get("order_id"),
            status="filled",
        )
        
        # RecordLearning - happens before EndCycle
        await self._record_learning_outcome(position, reason)
        
        # Update flow statistics with realized P&L (UpdateFlowStats step)
        # Note: increment_executions=False because execution was already counted when it completed
        if position.flow_id:
            try:
                from app.modules.flows import service as flow_service
                await flow_service._update_flow_statistics(
                    db=self.db,
                    flow_id=str(position.flow_id),
                    position_id=str(position.id),
                    execution_completed=True,
                    completed_at=datetime.now(timezone.utc),
                    increment_executions=False,  # Don't double-count executions
                )
            except Exception as e:
                logger.error(f"Failed to update flow statistics after position close: {e}")
        
        # Trigger flow continuation - EndCycle --> WaitTrigger
        await self._trigger_flow_continuation(str(position.flow_id))

    async def _apply_ai_recommendations(
        self,
        position: Position,
        monitor_result: Dict[str, Any],
    ) -> None:
        """Apply AI-driven stop-loss/take-profit recommendations."""
        recommendations = monitor_result.get("recommendations", [])
        if not recommendations:
            return

        updated = False
        for rec in recommendations:
            if rec.get("position_id") != str(position.id):
                continue
            action = rec.get("action")
            value = rec.get("value")
            if value is None:
                continue
            if action == "update_stop_loss":
                position.risk_management["current_stop_loss"] = float(value)
                updated = True
            elif action == "update_take_profit":
                position.risk_management["current_take_profit"] = float(value)
                updated = True

        if updated:
            await position.save()

    async def _record_transaction(
        self,
        position: Position,
        reason: str,
        price: Decimal,
        fee: Decimal,
        fee_currency: str,
        order_id: Optional[str],
        status: str,
    ) -> None:
        """Insert a transaction ledger entry for a position close."""
        try:
            # Check if exit transaction already exists
            transaction_type = "sell" if position.side == PositionSide.LONG else "buy"
            existing = await self.db["transactions"].find_one({
                "position_id": position.id,
                "type": transaction_type,
                "status": "filled"
            })
            
            if existing:
                logger.warning(f"Exit transaction already exists for position {position.id}, skipping duplicate")
                return
            
            exit_data = position.exit or {}
            pnl = Decimal(str(exit_data.get("realized_pnl", 0)))
            pnl_percent = Decimal(str(exit_data.get("realized_pnl_percent", 0)))
            quantity = Decimal(str(exit_data.get("amount", position.entry.get("amount", 0))))
            total_value = quantity * price

            await self.db["transactions"].insert_one({
                "user_id": position.user_id,
                "position_id": position.id,
                "flow_id": position.flow_id,
                "exchange": "wallet",
                "symbol": position.symbol,
                "type": transaction_type,
                "side": position.side.value,
                "quantity": float(quantity),
                "price": float(price),
                "total_value": float(total_value),
                "fee": float(fee),
                "fee_currency": fee_currency,
                "pnl": float(pnl),
                "pnl_percent": float(pnl_percent),
                "order_id": order_id,
                "status": status,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc),
                "created_at": datetime.now(timezone.utc),
            })
        except Exception as e:
            logger.error(f"Failed to record transaction for position {position.id}: {e}")

    async def _record_learning_outcome(
        self,
        position: Position,
        reason: str,
    ) -> None:
        """
        Record learning outcome when position closes.
        
        This implements the RecordLearning step from the flowchart,
        which happens before EndCycle --> WaitTrigger.
        """
        try:
            exit_data = position.exit or {}
            pnl = float(exit_data.get("realized_pnl", 0))
            pnl_percent = float(exit_data.get("realized_pnl_percent", 0))
            
            learning_record = {
                "user_id": position.user_id,
                "flow_id": position.flow_id,
                "position_id": position.id,
                "symbol": position.symbol,
                "action": "close",
                "close_reason": reason,
                "side": position.side.value,
                "entry_price": position.entry.get("price"),
                "exit_price": exit_data.get("price"),
                "quantity": position.entry.get("amount"),
                "realized_pnl": pnl,
                "realized_pnl_percent": pnl_percent,
                "outcome": "profit" if pnl > 0 else ("loss" if pnl < 0 else "breakeven"),
                "risk_management": position.risk_management,
                "ai_monitoring": position.ai_monitoring,
                "opened_at": position.opened_at,
                "closed_at": position.closed_at,
                "created_at": datetime.now(timezone.utc),
            }
            
            await self.db["learning_outcomes"].insert_one(learning_record)
            logger.info(f"Recorded learning outcome for position {position.id}: {reason} - PnL: {pnl:.2f}")
        except Exception as e:
            logger.error(f"Failed to record learning outcome for position {position.id}: {e}")

    async def _trigger_flow_continuation(self, flow_id: str) -> None:
        """
        Trigger next trading cycle after position closes.
        
        This ensures the continuous loop continues:
        EndCycle --> WaitTrigger --> next execution
        """
        if not flow_id:
            return
        
        try:
            from app.modules.flows import service as flow_service
            
            flow = await flow_service.get_flow_by_id(self.db, str(flow_id))
            if not flow:
                logger.warning(f"Flow not found for continuation: {flow_id}")
                return
            
            if flow.status != FlowStatus.ACTIVE:
                logger.info(f"Flow {flow_id} is not active, skipping continuation")
                return
            
            logger.info(f"Triggering flow continuation after position close: {flow_id}")
            await flow_service._schedule_auto_loop(self.db, flow, "groq", None)
        except Exception as e:
            logger.error(f"Failed to trigger flow continuation for {flow_id}: {e}")


# Global instance helper
_position_tracker = None


async def get_position_tracker(db: AsyncIOMotorDatabase) -> PositionTrackerService:
    """
    Get global position tracker service instance.
    
    Args:
        db: Database instance
        
    Returns:
        Position tracker service
    """
    global _position_tracker
    
    if _position_tracker is None:
        _position_tracker = PositionTrackerService(db)
    
    return _position_tracker
