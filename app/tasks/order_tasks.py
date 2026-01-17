"""
Order Monitoring Celery Tasks

Background tasks for monitoring orders and positions.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

from celery import Task
from datetime import datetime, timezone
from typing import Dict, Any

from app.tasks.celery_app import celery_app
from app.config.database import get_database
from app.services.order_monitor import get_order_monitor
from app.services.position_tracker import get_position_tracker, PositionTrackerService
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def monitor_order_task(self: Task, order_id: str) -> Dict[str, Any]:
    """
    Celery task to monitor a single order.
    
    Args:
        order_id: Order ID to monitor
        
    Returns:
        Dict with monitoring result
    """
    try:
        import asyncio
        
        # Get database
        db = asyncio.run(get_database())
        
        # Get order monitor
        async def monitor():
            monitor_service = await get_order_monitor(db)
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
def monitor_user_orders_task(self: Task, user_id: str) -> Dict[str, Any]:
    """
    Celery task to monitor all orders for a user.
    
    Args:
        user_id: User ID
        
    Returns:
        Dict with monitoring results
    """
    try:
        import asyncio
        
        # Get database
        db = asyncio.run(get_database())
        
        # Get order monitor
        async def monitor():
            monitor_service = await get_order_monitor(db)
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
def monitor_all_orders_task(self: Task) -> Dict[str, Any]:
    """
    Periodic task to monitor all open orders in the system.
    
    This should run every N minutes (configured in celery beat).
    
    Returns:
        Dict with monitoring results
    """
    try:
        import asyncio
        
        # Get database
        db = asyncio.run(get_database())
        
        # Get order monitor
        async def monitor():
            monitor_service = await get_order_monitor(db)
            return await monitor_service.monitor_all_open_orders()
        
        result = asyncio.run(monitor())
        
        logger.info(
            f"All orders monitored: {result.get('total_orders')} orders, "
            f"{result.get('updated')} updated, {result.get('errors')} errors"
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Error monitoring all orders: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@celery_app.task(bind=True)
def monitor_position_task(self: Task, position_id: str) -> Dict[str, Any]:
    """
    Celery task to monitor a single position.
    
    Args:
        position_id: Position ID to monitor
        
    Returns:
        Dict with monitoring result
    """
    try:
        import asyncio
        
        # Get database
        db = asyncio.run(get_database())
        
        # Get position tracker
        async def monitor():
            tracker_service = await get_position_tracker(db)
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
def monitor_all_positions_task(self: Task) -> Dict[str, Any]:
    """
    Periodic task to monitor all open positions in the system.
    
    This should run every N minutes (configured in celery beat).
    
    Returns:
        Dict with monitoring results
    """
    try:
        import asyncio
        
        # Get database
        db = asyncio.run(get_database())
        
        # Get position tracker
        async def monitor():
            tracker_service = await get_position_tracker(db)
            return await tracker_service.monitor_all_positions()
        
        result = asyncio.run(monitor())
        
        logger.info(
            f"All positions monitored: {result.get('total_positions')} positions, "
            f"{result.get('updated')} updated, {result.get('errors')} errors"
        )
        
        return result
    
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
    current_price: float
) -> Dict[str, Any]:
    """
    Celery task to update position with current price.
    
    Args:
        position_id: Position ID
        current_price: Current market price
        
    Returns:
        Dict with update result
    """
    try:
        from decimal import Decimal
        import asyncio
        
        # Get database
        db = asyncio.run(get_database())
        
        # Get position tracker
        async def update():
            tracker_service = await get_position_tracker(db)
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

