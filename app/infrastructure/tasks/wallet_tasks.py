"""
Wallet Background Tasks

Celery tasks for wallet operations:
- Balance synchronization
- Connection testing
- Data cleanup

Author: Moniqo Team
Last Updated: 2025-11-22
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from celery import Task
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.infrastructure.tasks.celery_app import celery_app
from app.core.config import get_settings
from app.core.database import db_provider
from app.core.context import set_trading_mode, TradingMode
from app.infrastructure.tasks.trading_mode_helpers import get_trading_mode_from_wallet
from app.modules.user_wallets import service
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


# ==================== HELPER FUNCTIONS ====================

def get_async_db() -> AsyncIOMotorDatabase:
    """
    Get async database connection for Celery tasks.
    
    DEPRECATED: This function bypasses context-aware database routing.
    Use db_provider.get_db() or db_provider.get_db_for_mode() instead.
    
    This function is kept for backward compatibility but should NOT be used in new code.
    All new code must use db_provider for proper demo/real isolation.
    """
    import warnings
    warnings.warn(
        "get_async_db() is deprecated. Use db_provider.get_db() or db_provider.get_db_for_mode() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]
    return db


def run_async(coro):
    """
    Run async function in sync context (Celery tasks are sync).
    
    Args:
        coro: Async coroutine to run
        
    Returns:
        Result of coroutine
    """
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # Create new loop if current one is running
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)


# ==================== TASKS ====================

@celery_app.task(
    bind=True,
    name="app.tasks.wallet_tasks.sync_user_wallet_balance",
    max_retries=3,
    default_retry_delay=60  # Retry after 1 minute
)
def sync_user_wallet_balance(self: Task, user_wallet_id: str, user_id: str, trading_mode: str) -> Dict[str, Any]:
    """
    Sync balance for a single user wallet.
    
    Background task triggered by:
    - Manual sync request
    - Scheduled sync (every N minutes)
    - After trade execution
    
    Args:
        user_wallet_id: User wallet ID
        user_id: User ID
        trading_mode: Trading mode ("demo" or "real")
        
    Returns:
        Sync result dict
        
    Example:
        # Trigger from code
        sync_user_wallet_balance.delay("wallet_123", "user_456", "demo")
        
        # Or synchronous (for testing)
        result = sync_user_wallet_balance("wallet_123", "user_456", "demo")
    """
    try:
        # FIRST LINE: Set trading mode context
        set_trading_mode(TradingMode(trading_mode))
        
        logger.info(f"Starting balance sync: wallet={user_wallet_id}, mode={trading_mode}")
        
        # Get database using context-aware provider
        db = db_provider.get_db()
        
        # Run sync
        result = run_async(
            service.sync_wallet_balance(
                db=db,
                user_wallet_id=user_wallet_id,
                user_id=user_id
            )
        )
        
        if result["success"]:
            logger.info(
                f"Balance sync successful: wallet={user_wallet_id}, "
                f"duration={result['sync_duration_ms']}ms"
            )
        else:
            logger.warning(
                f"Balance sync failed: wallet={user_wallet_id}, "
                f"error={result['error']}"
            )
            
            # Retry on failure
            raise self.retry(exc=Exception(result["error"]))
        
        return result
    
    except Exception as e:
        logger.error(f"Balance sync error: wallet={user_wallet_id}, error={str(e)}")
        
        # Retry up to max_retries
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        # Max retries reached, return error
        return {
            "success": False,
            "error": str(e),
            "user_wallet_id": user_wallet_id
        }


@celery_app.task(
    bind=True,
    name="app.tasks.wallet_tasks.sync_all_active_wallets",
    soft_time_limit=600,  # 10 minutes soft limit
    time_limit=660  # 11 minutes hard limit
)
def sync_all_active_wallets(self: Task) -> Dict[str, Any]:
    """
    Sync balances for all active wallets.
    
    Scheduled task (runs every 5 minutes via Celery Beat).
    Processes wallets from both demo and real databases.
    
    Process:
    1. Find all active wallets from both databases
    2. Determine trading mode for each wallet
    3. Trigger individual sync tasks for each with correct mode
    4. Return summary
    
    Returns:
        Summary dict with counts
        
    Example:
        # Manually trigger
        sync_all_active_wallets.delay()
    """
    try:
        logger.info("Starting batch wallet sync...")
        
        all_wallets = []
        
        # Get wallets from both databases
        for mode in [TradingMode.DEMO, TradingMode.REAL]:
            set_trading_mode(mode)
            db = db_provider.get_db()
            
            async def get_active_wallets():
                wallets = await db.user_wallets.find({
                    "is_active": True,
                    "deleted_at": None
                }).to_list(length=10000)
                return wallets
            
            wallets = run_async(get_active_wallets())
            
            # Add mode info to each wallet
            for wallet in wallets:
                wallet["_trading_mode"] = mode.value
                all_wallets.append(wallet)
        
        logger.info(f"Found {len(all_wallets)} active wallets to sync")
        
        # Trigger sync tasks with correct mode
        success_count = 0
        failed_count = 0
        
        for wallet in all_wallets:
            try:
                wallet_id = str(wallet["_id"])
                user_id = wallet["user_id"]
                trading_mode = wallet.get("_trading_mode", "demo")
                
                # Trigger async task with trading mode
                sync_user_wallet_balance.delay(
                    wallet_id,
                    user_id,
                    trading_mode
                )
                success_count += 1
            except Exception as e:
                logger.error(
                    f"Failed to trigger sync for wallet {wallet['_id']}: {str(e)}"
                )
                failed_count += 1
        
        result = {
            "success": True,
            "total_wallets": len(all_wallets),
            "triggered": success_count,
            "failed": failed_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(
            f"Batch wallet sync complete: triggered={success_count}, "
            f"failed={failed_count}"
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Batch wallet sync error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@celery_app.task(
    bind=True,
    name="app.tasks.wallet_tasks.test_wallet_connection",
    max_retries=2
)
def test_wallet_connection(self: Task, user_wallet_id: str, user_id: str, trading_mode: str) -> Dict[str, Any]:
    """
    Test wallet connection (background task).
    
    Args:
        user_wallet_id: User wallet ID
        user_id: User ID
        trading_mode: Trading mode ("demo" or "real")
        
    Returns:
        Connection test result
        
    Example:
        # Trigger connection test
        test_wallet_connection.delay("wallet_123", "user_456", "demo")
    """
    try:
        # FIRST LINE: Set trading mode context
        set_trading_mode(TradingMode(trading_mode))
        
        logger.info(f"Testing wallet connection: wallet={user_wallet_id}, mode={trading_mode}")
        
        # Get database using context-aware provider
        db = db_provider.get_db()
        
        # Run connection test
        result = run_async(
            service.test_wallet_connection(
                db=db,
                user_wallet_id=user_wallet_id,
                user_id=user_id
            )
        )
        
        if result["success"]:
            logger.info(
                f"Connection test successful: wallet={user_wallet_id}, "
                f"latency={result['latency_ms']}ms"
            )
        else:
            logger.warning(
                f"Connection test failed: wallet={user_wallet_id}, "
                f"error={result['error']}"
            )
        
        return result
    
    except Exception as e:
        logger.error(f"Connection test error: wallet={user_wallet_id}, error={str(e)}")
        
        return {
            "success": False,
            "error": str(e),
            "user_wallet_id": user_wallet_id
        }


@celery_app.task(
    bind=True,
    name="app.tasks.wallet_tasks.cleanup_old_sync_logs",
    soft_time_limit=300,
    time_limit=330
)
def cleanup_old_sync_logs(self: Task, days: int = 30, trading_mode: Optional[str] = None) -> Dict[str, Any]:
    """
    Cleanup old wallet sync logs.
    
    Deletes sync logs older than specified days.
    Scheduled task (runs daily at 3 AM via Celery Beat).
    Processes both demo and real databases if trading_mode is None.
    
    Args:
        days: Delete logs older than this many days (default: 30)
        trading_mode: Optional trading mode ("demo" or "real"). If None, processes both.
        
    Returns:
        Cleanup result with count by mode
        
    Example:
        # Manually trigger for both modes
        cleanup_old_sync_logs.delay(days=7)
        
        # Process only demo mode
        cleanup_old_sync_logs.delay(days=7, trading_mode="demo")
    """
    try:
        from app.core.database import db_provider
        
        logger.info(f"Starting sync log cleanup (older than {days} days)...")
        
        # Calculate cutoff date
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Determine which modes to process
        if trading_mode:
            modes_to_process = [TradingMode(trading_mode)]
        else:
            modes_to_process = [TradingMode.DEMO, TradingMode.REAL]
        
        results_by_mode = {}
        total_deleted = 0
        
        # Process each mode
        for mode in modes_to_process:
            try:
                # Get database for this mode
                db = db_provider.get_db_for_mode(mode)
                
                # Delete old logs
                async def delete_old_logs():
                    result = await db.wallet_sync_log.delete_many({
                        "synced_at": {"$lt": cutoff_date}
                    })
                    return result.deleted_count
                
                deleted_count = run_async(delete_old_logs())
                results_by_mode[mode.value] = deleted_count
                total_deleted += deleted_count
                
                logger.info(f"Sync log cleanup for {mode.value} mode: deleted {deleted_count} logs")
            
            except Exception as e:
                logger.error(f"Error cleaning up sync logs for {mode.value} mode: {str(e)}")
                results_by_mode[mode.value] = {"error": str(e)}
        
        result = {
            "success": True,
            "total_deleted_count": total_deleted,
            "by_mode": results_by_mode,
            "cutoff_date": cutoff_date.isoformat(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Sync log cleanup complete: deleted {total_deleted} logs total")
        
        return result
    
    except Exception as e:
        logger.error(f"Sync log cleanup error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@celery_app.task(
    bind=True,
    name="app.tasks.wallet_tasks.sync_wallet_after_trade",
    max_retries=3
)
def sync_wallet_after_trade(
    self: Task,
    user_wallet_id: str,
    user_id: str,
    trade_id: str,
    trading_mode: str
) -> Dict[str, Any]:
    """
    Sync wallet balance after trade execution.
    
    Triggered automatically after a trade is executed to ensure
    balances are up-to-date.
    
    Args:
        user_wallet_id: User wallet ID
        user_id: User ID
        trade_id: Trade/order ID that was executed
        trading_mode: Trading mode ("demo" or "real")
        
    Returns:
        Sync result
        
    Example:
        # Trigger after trade execution
        sync_wallet_after_trade.delay(
            user_wallet_id="wallet_123",
            user_id="user_456",
            trade_id="order_789",
            trading_mode="demo"
        )
    """
    try:
        # FIRST LINE: Set trading mode context
        set_trading_mode(TradingMode(trading_mode))
        
        logger.info(
            f"Syncing wallet after trade: wallet={user_wallet_id}, "
            f"trade={trade_id}, mode={trading_mode}"
        )
        
        # Get database using context-aware provider
        db = db_provider.get_db()
        
        # Run sync
        result = run_async(
            service.sync_wallet_balance(
                db=db,
                user_wallet_id=user_wallet_id,
                user_id=user_id
            )
        )
        
        # Add trade context to result
        result["trade_id"] = trade_id
        result["triggered_by"] = "trade_execution"
        
        if result["success"]:
            logger.info(
                f"Post-trade balance sync successful: wallet={user_wallet_id}, "
                f"trade={trade_id}"
            )
        else:
            logger.warning(
                f"Post-trade balance sync failed: wallet={user_wallet_id}, "
                f"trade={trade_id}, error={result['error']}"
            )
            
            # Retry on failure
            raise self.retry(exc=Exception(result["error"]))
        
        return result
    
    except Exception as e:
        logger.error(
            f"Post-trade balance sync error: wallet={user_wallet_id}, "
            f"trade={trade_id}, error={str(e)}"
        )
        
        # Retry
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        return {
            "success": False,
            "error": str(e),
            "user_wallet_id": user_wallet_id,
            "trade_id": trade_id
        }


# ==================== TASK MONITORING ====================

@celery_app.task(
    bind=True,
    name="app.tasks.wallet_tasks.get_task_stats"
)
def get_task_stats(self: Task) -> Dict[str, Any]:
    """
    Get Celery task statistics.
    
    Returns:
        Stats dict with task counts, queue sizes, etc.
        
    Example:
        stats = get_task_stats.delay().get()
        print(f"Active tasks: {stats['active']}")
    """
    try:
        inspect = celery_app.control.inspect()
        
        stats = {
            "active": inspect.active(),
            "scheduled": inspect.scheduled(),
            "reserved": inspect.reserved(),
            "stats": inspect.stats(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return stats
    
    except Exception as e:
        logger.error(f"Failed to get task stats: {str(e)}")
        return {
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

