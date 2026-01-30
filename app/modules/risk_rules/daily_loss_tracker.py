"""
Daily Loss Tracker Service

Tracks and enforces daily loss limits to protect capital.

Author: Moniqo Team
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from decimal import Decimal
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.utils.logger import get_logger

logger = get_logger(__name__)


class DailyLossTracker:
    """
    Daily loss tracker that enforces daily loss limits.
    
    Features:
    - Tracks daily P&L per user/wallet
    - Enforces configurable daily loss limit
    - Auto-resets at midnight UTC
    - Halts trading when limit reached
    
    Default settings:
    - DEFAULT_DAILY_LOSS_LIMIT: $100 or 5% of portfolio
    """
    
    DEFAULT_DAILY_LOSS_LIMIT_USD = 100.0
    DEFAULT_DAILY_LOSS_LIMIT_PERCENT = 0.05  # 5%
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.safety_status
    
    async def _get_status(self, user_id: str, wallet_id: str) -> Optional[Dict[str, Any]]:
        """Get safety status document for user/wallet."""
        return await self.collection.find_one({
            "user_id": ObjectId(user_id),
            "wallet_id": ObjectId(wallet_id)
        })
    
    async def _check_daily_reset(self, status: Dict[str, Any]) -> bool:
        """
        Check if daily counters need to be reset (new day started).
        
        Returns:
            True if reset was performed
        """
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        daily_reset_at = status.get("daily_reset_at")
        if not daily_reset_at or daily_reset_at < today_start:
            # Reset daily counters
            await self.collection.update_one(
                {"_id": status["_id"]},
                {
                    "$set": {
                        "daily_pnl": 0.0,
                        "daily_trades": 0,
                        "daily_wins": 0,
                        "daily_losses": 0,
                        "daily_reset_at": today_start,
                        "updated_at": now,
                    }
                }
            )
            logger.info(
                f"Daily counters reset: user={status['user_id']}, wallet={status['wallet_id']}"
            )
            return True
        
        return False
    
    async def get_daily_pnl(
        self, 
        user_id: str, 
        wallet_id: str
    ) -> float:
        """
        Get today's realized P&L.
        
        Returns:
            Today's P&L (negative for losses)
        """
        status = await self._get_status(user_id, wallet_id)
        if not status:
            return 0.0
        
        # Check if we need to reset for new day
        await self._check_daily_reset(status)
        
        # Re-fetch after potential reset
        status = await self._get_status(user_id, wallet_id)
        return status.get("daily_pnl", 0.0) if status else 0.0
    
    async def check_daily_limit(
        self, 
        user_id: str, 
        wallet_id: str,
        daily_loss_limit: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Check if daily loss limit has been exceeded.
        
        Args:
            user_id: User ID
            wallet_id: Wallet ID
            daily_loss_limit: Custom limit (uses default if not specified)
            
        Returns:
            {
                "exceeded": bool,
                "current_loss": float,
                "limit": float,
                "remaining": float,
                "daily_trades": int,
                "daily_wins": int,
                "daily_losses": int
            }
        """
        status = await self._get_status(user_id, wallet_id)
        
        if not status:
            limit = daily_loss_limit or self.DEFAULT_DAILY_LOSS_LIMIT_USD
            return {
                "exceeded": False,
                "current_loss": 0.0,
                "limit": limit,
                "remaining": limit,
                "daily_trades": 0,
                "daily_wins": 0,
                "daily_losses": 0,
            }
        
        # Check if we need to reset for new day
        await self._check_daily_reset(status)
        
        # Re-fetch after potential reset
        status = await self._get_status(user_id, wallet_id)
        if not status:
            limit = daily_loss_limit or self.DEFAULT_DAILY_LOSS_LIMIT_USD
            return {
                "exceeded": False,
                "current_loss": 0.0,
                "limit": limit,
                "remaining": limit,
                "daily_trades": 0,
                "daily_wins": 0,
                "daily_losses": 0,
            }
        
        daily_pnl = status.get("daily_pnl", 0.0)
        limit = daily_loss_limit or self.DEFAULT_DAILY_LOSS_LIMIT_USD
        
        # Calculate loss (negative P&L = loss)
        current_loss = abs(min(0, daily_pnl))
        remaining = max(0, limit - current_loss)
        exceeded = current_loss >= limit
        
        if exceeded:
            logger.warning(
                f"Daily loss limit exceeded: user={user_id}, wallet={wallet_id}, "
                f"loss=${current_loss:.2f}, limit=${limit:.2f}"
            )
        
        return {
            "exceeded": exceeded,
            "current_loss": current_loss,
            "limit": limit,
            "remaining": remaining,
            "daily_pnl": daily_pnl,
            "daily_trades": status.get("daily_trades", 0),
            "daily_wins": status.get("daily_wins", 0),
            "daily_losses": status.get("daily_losses", 0),
        }
    
    async def record_trade(
        self, 
        user_id: str, 
        wallet_id: str, 
        pnl: float,
        is_win: bool
    ) -> Dict[str, Any]:
        """
        Record a completed trade's P&L.
        
        Args:
            user_id: User ID
            wallet_id: Wallet ID
            pnl: Profit/loss amount
            is_win: True if trade was profitable
            
        Returns:
            Updated daily status
        """
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Use atomic update with upsert
        result = await self.collection.find_one_and_update(
            {
                "user_id": ObjectId(user_id),
                "wallet_id": ObjectId(wallet_id)
            },
            {
                "$inc": {
                    "daily_pnl": pnl,
                    "daily_trades": 1,
                    "daily_wins": 1 if is_win else 0,
                    "daily_losses": 0 if is_win else 1,
                },
                "$set": {
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "user_id": ObjectId(user_id),
                    "wallet_id": ObjectId(wallet_id),
                    "circuit_breaker_tripped": False,
                    "consecutive_losses": 0,
                    "cooldown_until": None,
                    "emergency_stop": False,
                    "daily_reset_at": today_start,
                    "created_at": now,
                }
            },
            upsert=True,
            return_document=True
        )
        
        logger.info(
            f"Trade recorded: user={user_id}, wallet={wallet_id}, "
            f"pnl=${pnl:.2f}, win={is_win}, daily_pnl=${result.get('daily_pnl', 0):.2f}"
        )
        
        return {
            "daily_pnl": result.get("daily_pnl", 0.0),
            "daily_trades": result.get("daily_trades", 0),
            "daily_wins": result.get("daily_wins", 0),
            "daily_losses": result.get("daily_losses", 0),
        }
    
    async def get_daily_stats(
        self, 
        user_id: str, 
        wallet_id: str
    ) -> Dict[str, Any]:
        """
        Get full daily statistics.
        
        Returns:
            Daily trading statistics
        """
        status = await self._get_status(user_id, wallet_id)
        
        if not status:
            return {
                "daily_pnl": 0.0,
                "daily_trades": 0,
                "daily_wins": 0,
                "daily_losses": 0,
                "win_rate": 0.0,
            }
        
        # Check if we need to reset for new day
        await self._check_daily_reset(status)
        
        # Re-fetch after potential reset
        status = await self._get_status(user_id, wallet_id)
        if not status:
            return {
                "daily_pnl": 0.0,
                "daily_trades": 0,
                "daily_wins": 0,
                "daily_losses": 0,
                "win_rate": 0.0,
            }
        
        daily_trades = status.get("daily_trades", 0)
        daily_wins = status.get("daily_wins", 0)
        win_rate = (daily_wins / daily_trades * 100) if daily_trades > 0 else 0.0
        
        return {
            "daily_pnl": status.get("daily_pnl", 0.0),
            "daily_trades": daily_trades,
            "daily_wins": daily_wins,
            "daily_losses": status.get("daily_losses", 0),
            "win_rate": win_rate,
        }


# Singleton instance getter
_daily_loss_tracker: Optional[DailyLossTracker] = None


def get_daily_loss_tracker(db: AsyncIOMotorDatabase) -> DailyLossTracker:
    """Get or create daily loss tracker instance."""
    global _daily_loss_tracker
    if _daily_loss_tracker is None:
        _daily_loss_tracker = DailyLossTracker(db)
    return _daily_loss_tracker
