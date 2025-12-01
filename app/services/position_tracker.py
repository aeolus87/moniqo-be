"""
Position Tracking Service

Monitors open positions, updates P&L in real-time, and manages risk.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from decimal import Decimal
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.positions.models import Position, PositionStatus, PositionSide, PositionUpdate
from app.integrations.wallets.factory import WalletFactory
from app.services.websocket_manager import get_websocket_manager
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
        self.wallet_factory = WalletFactory()
        
        logger.info("Position tracker service initialized")
    
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
            # Get position
            position = await Position.get(position_id)
            
            if not position:
                return {
                    "success": False,
                    "error": "Position not found"
                }
            
            if not position.is_open():
                return {
                    "success": True,
                    "message": "Position is not open",
                    "status": position.status.value
                }
            
            # Get current price from market
            wallet_instance = await self.wallet_factory.create_wallet(
                wallet_id=str(position.user_wallet_id),
                user_wallet_id=str(position.user_wallet_id)
            )
            
            current_price = await wallet_instance.get_market_price(position.symbol)
            
            # Update position
            result = await self.update_position_price(str(position.id), current_price)
            
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
            # Get all open positions
            positions = await Position.find(
                Position.status == PositionStatus.OPEN,
                Position.deleted_at == None
            ).to_list()
            
            results = {
                "success": True,
                "total_positions": len(positions),
                "updated": 0,
                "errors": 0,
                "details": []
            }
            
            # Monitor each position
            for position in positions:
                try:
                    result = await self.monitor_position(str(position.id))
                    
                    if result["success"]:
                        results["updated"] += 1
                    else:
                        results["errors"] += 1
                    
                    results["details"].append({
                        "position_id": str(position.id),
                        "symbol": position.symbol,
                        "result": result
                    })
                
                except Exception as e:
                    results["errors"] += 1
                    results["details"].append({
                        "position_id": str(position.id),
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
            # Create exit order
            wallet_instance = await self.wallet_factory.create_wallet(
                wallet_id=str(position.user_wallet_id),
                user_wallet_id=str(position.user_wallet_id)
            )
            
            # Place market sell order to close position
            exit_side = OrderSide.SELL if position.side == PositionSide.LONG else OrderSide.BUY
            entry_amount = Decimal(str(position.entry["amount"]))
            
            # Place order (this will be handled by order service)
            # For now, just close the position
            await position.close(
                order_id=position.id,  # TODO: Use actual exit order ID
                price=current_price,
                reason="stop_loss",
                fees=Decimal("0")  # TODO: Calculate actual fees
            )
            
            logger.info(f"Stop loss triggered for position {position.id} at {current_price}")
        
        except Exception as e:
            logger.error(f"Error triggering stop loss: {str(e)}")
    
    async def _trigger_take_profit(self, position: Position, current_price: Decimal):
        """Trigger take profit for position"""
        try:
            # Close position
            await position.close(
                order_id=position.id,  # TODO: Use actual exit order ID
                price=current_price,
                reason="take_profit",
                fees=Decimal("0")  # TODO: Calculate actual fees
            )
            
            logger.info(f"Take profit triggered for position {position.id} at {current_price}")
        
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


