"""
Order Monitoring Service

Monitors order status changes, handles partial fills, and triggers position updates.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from decimal import Decimal
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.modules.orders.models import Order, OrderStatus, OrderSide, OrderType
from app.modules.positions.models import Position, PositionStatus, PositionSide
from app.integrations.wallets.factory import WalletFactory
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OrderMonitorService:
    """
    Order Monitoring Service
    
    Monitors order status, syncs with exchanges, handles fills,
    and updates positions accordingly.
    
    Features:
    - Periodic order status checks
    - Partial fill aggregation
    - Position creation/updates
    - Error recovery
    
    Usage:
        monitor = OrderMonitorService(db)
        
        # Monitor single order
        await monitor.monitor_order(order_id)
        
        # Monitor all open orders for user
        await monitor.monitor_user_orders(user_id)
        
        # Sync order from exchange
        await monitor.sync_order_from_exchange(order)
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize order monitor service.
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.wallet_factory = WalletFactory()
        
        logger.info("Order monitor service initialized")
    
    async def monitor_order(self, order_id: str) -> Dict[str, Any]:
        """
        Monitor a single order and sync status from exchange.
        
        Args:
            order_id: Order ID to monitor
            
        Returns:
            Dict with monitoring result
        """
        try:
            # Get order from database
            order = await Order.get(order_id)
            
            if not order:
                return {
                    "success": False,
                    "error": "Order not found"
                }
            
            # Skip if order is complete
            if order.is_complete():
                return {
                    "success": True,
                    "message": "Order already complete",
                    "status": order.status.value
                }
            
            # Sync from exchange
            result = await self.sync_order_from_exchange(order)
            
            return {
                "success": True,
                "order_id": str(order.id),
                "status": order.status.value,
                "filled_amount": float(order.filled_amount),
                "remaining_amount": float(order.remaining_amount),
                "result": result
            }
        
        except Exception as e:
            logger.error(f"Error monitoring order {order_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def sync_order_from_exchange(self, order: Order) -> Dict[str, Any]:
        """
        Sync order status from exchange.
        
        Args:
            order: Order instance
            
        Returns:
            Dict with sync result
        """
        try:
            # Get wallet instance
            wallet_instance = await self.wallet_factory.create_wallet(
                wallet_id=str(order.user_wallet_id),
                user_wallet_id=str(order.user_wallet_id)
            )
            
            if not order.external_order_id:
                logger.warning(f"Order {order.id} has no external_order_id, skipping sync")
                return {
                    "success": False,
                    "error": "No external order ID"
                }
            
            # Get order status from exchange
            status_response = await wallet_instance.get_order_status(
                order_id=order.external_order_id,
                symbol=order.symbol
            )
            
            # Update order based on exchange response
            new_status = self._map_exchange_status(status_response["status"])
            
            # Check if status changed
            if new_status != order.status:
                await order.update_status(
                    new_status,
                    f"Synced from exchange: {status_response.get('status')}"
                )
            
            # Check for new fills
            filled_quantity = status_response.get("filled_quantity", Decimal("0"))
            
            if filled_quantity > order.filled_amount:
                # New fills detected
                fill_amount = filled_quantity - order.filled_amount
                fill_price = status_response.get("average_price") or order.limit_price or Decimal("0")
                
                # Create fill
                fill = {
                    "fill_id": f"fill_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                    "amount": fill_amount,
                    "price": fill_price,
                    "fee": Decimal("0"),  # TODO: Get actual fee from exchange
                    "fee_currency": order.symbol.split("/")[1] if "/" in order.symbol else "USDT"
                }
                
                await order.add_fill(fill)
                
                # Update position if exists
                if order.position_id:
                    await self._update_position_from_order(order)
                else:
                    # Create new position if entry order is filled
                    if order.side == OrderSide.BUY and order.is_complete():
                        await self._create_position_from_order(order)
            
            return {
                "success": True,
                "status": order.status.value,
                "filled_amount": float(order.filled_amount),
                "has_new_fills": filled_quantity > order.filled_amount
            }
        
        except Exception as e:
            logger.error(f"Error syncing order {order.id} from exchange: {str(e)}")
            
            # Update order status to failed if connection error
            if "connection" in str(e).lower() or "timeout" in str(e).lower():
                await order.update_status(
                    OrderStatus.FAILED,
                    f"Exchange sync failed: {str(e)}"
                )
            
            return {
                "success": False,
                "error": str(e)
            }
    
    def _map_exchange_status(self, exchange_status: Any) -> OrderStatus:
        """Map exchange order status to our OrderStatus enum"""
        status_map = {
            "NEW": OrderStatus.OPEN,
            "OPEN": OrderStatus.OPEN,
            "PARTIALLY_FILLED": OrderStatus.PARTIALLY_FILLED,
            "FILLED": OrderStatus.FILLED,
            "CANCELED": OrderStatus.CANCELLED,
            "CANCELLED": OrderStatus.CANCELLED,
            "CANCELLING": OrderStatus.CANCELLING,
            "REJECTED": OrderStatus.REJECTED,
            "EXPIRED": OrderStatus.EXPIRED,
            "PENDING": OrderStatus.PENDING,
            "SUBMITTED": OrderStatus.SUBMITTED
        }
        
        if isinstance(exchange_status, OrderStatus):
            return exchange_status
        
        status_str = str(exchange_status).upper()
        return status_map.get(status_str, OrderStatus.PENDING)
    
    async def _update_position_from_order(self, order: Order):
        """
        Update position based on order fills.
        
        Args:
            order: Order instance
        """
        try:
            position = await Position.get(order.position_id)
            
            if not position:
                logger.warning(f"Position {order.position_id} not found for order {order.id}")
                return
            
            # If entry order is filled, update position status
            if order.is_complete() and position.status == PositionStatus.OPENING:
                position.status = PositionStatus.OPEN
                position.opened_at = datetime.now(timezone.utc)
                
                # Update entry data with actual fill price
                if order.average_fill_price:
                    position.entry["price"] = order.average_fill_price
                    position.entry["fees"] = order.total_fees
                
                await position.save()
            
            # If exit order is filled, close position
            elif order.is_complete() and position.status == PositionStatus.CLOSING:
                await position.close(
                    order_id=order.id,
                    price=order.average_fill_price or order.limit_price or Decimal("0"),
                    reason="order_filled",
                    fees=order.total_fees
                )
        
        except Exception as e:
            logger.error(f"Error updating position from order: {str(e)}")
    
    async def _create_position_from_order(self, order: Order):
        """
        Create new position from filled entry order.
        
        Args:
            order: Order instance (must be filled entry order)
        """
        try:
            if order.side != OrderSide.BUY:
                return  # Only create positions from buy orders
            
            if not order.is_complete():
                return  # Only create if order is fully filled
            
            # Check if position already exists
            if order.position_id:
                return
            
            # Create entry data
            entry_price = order.average_fill_price or order.limit_price or Decimal("0")
            entry_amount = order.filled_amount
            
            entry_data = {
                "order_id": order.id,
                "timestamp": order.first_fill_at or datetime.now(timezone.utc),
                "price": entry_price,
                "amount": entry_amount,
                "value": entry_price * entry_amount,
                "leverage": Decimal("1"),
                "margin_used": entry_price * entry_amount,
                "fees": order.total_fees,
                "fee_currency": order.symbol.split("/")[1] if "/" in order.symbol else "USDT",
                "ai_reasoning": order.ai_reasoning,
                "ai_confidence": order.ai_confidence,
                "ai_agent": None  # TODO: Get from order if available
            }
            
            # Create position
            position = Position(
                user_id=order.user_id,
                user_wallet_id=order.user_wallet_id,
                symbol=order.symbol,
                side=PositionSide.LONG,
                entry=entry_data,
                status=PositionStatus.OPEN,
                flow_id=order.flow_id
            )
            position.opened_at = datetime.now(timezone.utc)
            
            await position.insert()
            
            # Link order to position
            order.position_id = position.id
            await order.save()
            
            logger.info(f"Created position {position.id} from order {order.id}")
        
        except Exception as e:
            logger.error(f"Error creating position from order: {str(e)}")
    
    async def monitor_user_orders(self, user_id: str) -> Dict[str, Any]:
        """
        Monitor all open orders for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with monitoring results
        """
        try:
            # Get all open orders for user
            orders = await Order.find(
                Order.user_id == ObjectId(user_id),
                Order.status.in_([
                    OrderStatus.PENDING,
                    OrderStatus.SUBMITTED,
                    OrderStatus.OPEN,
                    OrderStatus.PARTIALLY_FILLED
                ]),
                Order.deleted_at == None
            ).to_list()
            
            results = {
                "success": True,
                "total_orders": len(orders),
                "updated": 0,
                "errors": 0,
                "details": []
            }
            
            # Monitor each order
            for order in orders:
                try:
                    result = await self.monitor_order(str(order.id))
                    
                    if result["success"]:
                        results["updated"] += 1
                    else:
                        results["errors"] += 1
                    
                    results["details"].append({
                        "order_id": str(order.id),
                        "symbol": order.symbol,
                        "status": order.status.value,
                        "result": result
                    })
                
                except Exception as e:
                    results["errors"] += 1
                    results["details"].append({
                        "order_id": str(order.id),
                        "error": str(e)
                    })
            
            return results
        
        except Exception as e:
            logger.error(f"Error monitoring user orders: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def monitor_all_open_orders(self) -> Dict[str, Any]:
        """
        Monitor all open orders in the system.
        
        Returns:
            Dict with monitoring results
        """
        try:
            # Get all open orders
            orders = await Order.find(
                Order.status.in_([
                    OrderStatus.PENDING,
                    OrderStatus.SUBMITTED,
                    OrderStatus.OPEN,
                    OrderStatus.PARTIALLY_FILLED
                ]),
                Order.deleted_at == None
            ).to_list()
            
            results = {
                "success": True,
                "total_orders": len(orders),
                "updated": 0,
                "errors": 0
            }
            
            # Monitor each order (with batching to avoid overload)
            batch_size = 10
            for i in range(0, len(orders), batch_size):
                batch = orders[i:i + batch_size]
                
                for order in batch:
                    try:
                        result = await self.monitor_order(str(order.id))
                        
                        if result["success"]:
                            results["updated"] += 1
                        else:
                            results["errors"] += 1
                    
                    except Exception as e:
                        results["errors"] += 1
                        logger.error(f"Error monitoring order {order.id}: {str(e)}")
                
                # Small delay between batches
                import asyncio
                await asyncio.sleep(0.1)
            
            return results
        
        except Exception as e:
            logger.error(f"Error monitoring all open orders: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }


# Global instance helper
_order_monitor = None


async def get_order_monitor(db: AsyncIOMotorDatabase) -> OrderMonitorService:
    """
    Get global order monitor service instance.
    
    Args:
        db: Database instance
        
    Returns:
        Order monitor service
    """
    global _order_monitor
    
    if _order_monitor is None:
        _order_monitor = OrderMonitorService(db)
    
    return _order_monitor

