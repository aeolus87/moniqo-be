"""
Order Monitoring Celery Tasks

Background tasks for monitoring orders and positions.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

from celery import Task
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from app.infrastructure.tasks.celery_app import celery_app
from app.core.database import db_provider
from app.core.context import set_trading_mode, TradingMode
from app.infrastructure.tasks.order_monitor import get_order_monitor
from app.infrastructure.tasks.position_tracker import get_position_tracker, PositionTrackerService
from app.infrastructure.tasks.trading_mode_helpers import (
    get_trading_mode_from_order,
    get_trading_mode_from_position
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def monitor_order_task(self: Task, order_id: str, trading_mode: str) -> Dict[str, Any]:
    """
    Celery task to monitor a single order.
    
    Args:
        order_id: Order ID to monitor
        trading_mode: Trading mode ("demo" or "real")
        
    Returns:
        Dict with monitoring result
    """
    try:
        import asyncio
        
        # FIRST LINE: Set trading mode context
        set_trading_mode(TradingMode(trading_mode))
        
        # Get order monitor
        async def monitor():
            monitor_service = await get_order_monitor(db_provider.get_db())
            return await monitor_service.monitor_order(order_id)
        
        result = asyncio.run(monitor())
        
        logger.info(f"Order {order_id} monitored: {result.get('status')}")
        
        return result
    
    except Exception as e:
        logger.error(f"Error monitoring order {order_id}: {str(e)}")
        
        # Retry if retries left
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        return {
            "success": False,
            "error": str(e),
            "order_id": order_id
        }


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def monitor_user_orders_task(self: Task, user_id: str, trading_mode: str) -> Dict[str, Any]:
    """
    Celery task to monitor all orders for a user.
    
    Args:
        user_id: User ID
        trading_mode: Trading mode ("demo" or "real")
        
    Returns:
        Dict with monitoring results
    """
    try:
        import asyncio
        
        # FIRST LINE: Set trading mode context
        set_trading_mode(TradingMode(trading_mode))
        
        # Get order monitor
        async def monitor():
            monitor_service = await get_order_monitor(db_provider.get_db())
            return await monitor_service.monitor_user_orders(user_id)
        
        result = asyncio.run(monitor())
        
        logger.info(f"User {user_id} orders monitored: {result.get('total_orders')} orders")
        
        return result
    
    except Exception as e:
        logger.error(f"Error monitoring user orders {user_id}: {str(e)}")
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        return {
            "success": False,
            "error": str(e),
            "user_id": user_id
        }


@celery_app.task(bind=True)
def monitor_all_orders_task(self: Task, trading_mode: Optional[str] = None) -> Dict[str, Any]:
    """
    Periodic task to monitor all open orders in the system.
    
    This should run every N minutes (configured in celery beat).
    Processes both demo and real modes if trading_mode is None.
    
    Args:
        trading_mode: Optional trading mode ("demo" or "real"). If None, processes both.
        
    Returns:
        Dict with monitoring results
    """
    try:
        import asyncio
        
        results = {}
        
        if trading_mode:
            # Process single mode
            set_trading_mode(TradingMode(trading_mode))
            
            async def monitor():
                monitor_service = await get_order_monitor(db_provider.get_db())
                return await monitor_service.monitor_all_open_orders()
            
            result = asyncio.run(monitor())
            results[trading_mode] = result
            
            logger.info(
                f"All {trading_mode} orders monitored: {result.get('total_orders')} orders, "
                f"{result.get('updated')} updated, {result.get('errors')} errors"
            )
        else:
            # Process both modes
            for mode in [TradingMode.DEMO, TradingMode.REAL]:
                mode_value = mode.value  # Capture mode value for closure
                set_trading_mode(mode)
                
                async def monitor():
                    monitor_service = await get_order_monitor(db_provider.get_db())
                    return await monitor_service.monitor_all_open_orders()
                
                result = asyncio.run(monitor())
                results[mode_value] = result
                
                logger.info(
                    f"All {mode_value} orders monitored: {result.get('total_orders')} orders, "
                    f"{result.get('updated')} updated, {result.get('errors')} errors"
                )
        
        # Aggregate results
        total_orders = sum(r.get('total_orders', 0) for r in results.values())
        total_updated = sum(r.get('updated', 0) for r in results.values())
        total_errors = sum(r.get('errors', 0) for r in results.values())
        
        return {
            "success": True,
            "total_orders": total_orders,
            "updated": total_updated,
            "errors": total_errors,
            "by_mode": results
        }
    
    except Exception as e:
        logger.error(f"Error monitoring all orders: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@celery_app.task(bind=True)
def monitor_position_task(self: Task, position_id: str, trading_mode: str) -> Dict[str, Any]:
    """
    Celery task to monitor a single position.
    
    Args:
        position_id: Position ID to monitor
        trading_mode: Trading mode ("demo" or "real")
        
    Returns:
        Dict with monitoring result
    """
    try:
        import asyncio
        
        # FIRST LINE: Set trading mode context
        set_trading_mode(TradingMode(trading_mode))
        
        # Get position tracker
        async def monitor():
            tracker_service = await get_position_tracker()
            return await tracker_service.monitor_position(position_id)
        
        result = asyncio.run(monitor())
        
        logger.info(f"Position {position_id} monitored: {result.get('unrealized_pnl')}")
        
        return result
    
    except Exception as e:
        logger.error(f"Error monitoring position {position_id}: {str(e)}")
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        return {
            "success": False,
            "error": str(e),
            "position_id": position_id
        }


@celery_app.task(bind=True)
def monitor_all_positions_task(self: Task, trading_mode: Optional[str] = None) -> Dict[str, Any]:
    """
    Periodic task to monitor all open positions in the system.
    
    This should run every N minutes (configured in celery beat).
    Processes both demo and real modes if trading_mode is None.
    
    Args:
        trading_mode: Optional trading mode ("demo" or "real"). If None, processes both.
        
    Returns:
        Dict with monitoring results
    """
    try:
        import asyncio
        
        results = {}
        
        if trading_mode:
            # Process single mode
            set_trading_mode(TradingMode(trading_mode))
            
            async def monitor():
                tracker_service = await get_position_tracker()
                return await tracker_service.monitor_all_positions()
            
            result = asyncio.run(monitor())
            results[trading_mode] = result
            
            logger.info(
                f"All {trading_mode} positions monitored: {result.get('total_positions')} positions, "
                f"{result.get('updated')} updated, {result.get('errors')} errors"
            )
        else:
            # Process both modes
            for mode in [TradingMode.DEMO, TradingMode.REAL]:
                mode_value = mode.value  # Capture mode value for closure
                set_trading_mode(mode)
                
                async def monitor():
                    tracker_service = await get_position_tracker()
                    return await tracker_service.monitor_all_positions()
                
                result = asyncio.run(monitor())
                results[mode_value] = result
                
                logger.info(
                    f"All {mode_value} positions monitored: {result.get('total_positions')} positions, "
                    f"{result.get('updated')} updated, {result.get('errors')} errors"
                )
        
        # Aggregate results
        total_positions = sum(r.get('total_positions', 0) for r in results.values())
        total_updated = sum(r.get('updated', 0) for r in results.values())
        total_errors = sum(r.get('errors', 0) for r in results.values())
        
        return {
            "success": True,
            "total_positions": total_positions,
            "updated": total_updated,
            "errors": total_errors,
            "by_mode": results
        }
    
    except Exception as e:
        logger.error(f"Error monitoring all positions: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@celery_app.task(bind=True)
def update_position_price_task(
    self: Task,
    position_id: str,
    current_price: float,
    trading_mode: str
) -> Dict[str, Any]:
    """
    Celery task to update position with current price.
    
    Args:
        position_id: Position ID
        current_price: Current market price
        trading_mode: Trading mode ("demo" or "real")
        
    Returns:
        Dict with update result
    """
    try:
        from decimal import Decimal
        import asyncio
        
        # FIRST LINE: Set trading mode context
        set_trading_mode(TradingMode(trading_mode))
        
        # Get position tracker
        async def update():
            tracker_service = await get_position_tracker()
            return await tracker_service.update_position_price(
                position_id,
                Decimal(str(current_price))
            )
        
        result = asyncio.run(update())
        
        return result
    
    except Exception as e:
        logger.error(f"Error updating position price: {str(e)}")
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        return {
            "success": False,
            "error": str(e),
            "position_id": position_id
        }

