"""
Cooldown Service

Enforces wait time between trades to prevent impulsive/revenge trading.

Author: Moniqo Team
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.utils.logger import get_logger

logger = get_logger(__name__)


class CooldownService:
    """
    Cooldown service that enforces wait time between trades.
    
    Features:
    - Minimum cooldown between any trades
    - Extended cooldown after losses
    - Progressive cooldown for consecutive losses
    
    Default settings:
    - MIN_COOLDOWN_SECONDS: 60 (1 min between any trades)
    - LOSS_COOLDOWN_SECONDS: 300 (5 min after a loss)
    - DOUBLE_LOSS_COOLDOWN_SECONDS: 900 (15 min after 2 consecutive losses)
    """
    
    MIN_COOLDOWN_SECONDS = 60        # 1 minute between any trades
    LOSS_COOLDOWN_SECONDS = 300      # 5 minutes after a loss
    DOUBLE_LOSS_COOLDOWN_SECONDS = 900  # 15 minutes after 2 consecutive losses
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.safety_status
    
    async def _get_status(self, user_id: str, wallet_id: str) -> Optional[Dict[str, Any]]:
        """Get safety status document for user/wallet."""
        return await self.collection.find_one({
            "user_id": ObjectId(user_id),
            "wallet_id": ObjectId(wallet_id)
        })
    
    async def check_cooldown(
        self, 
        user_id: str, 
        wallet_id: str
    ) -> Dict[str, Any]:
        """
        Check if cooldown is active.
        
        Returns:
            {
                "active": bool,
                "remaining_seconds": int,
                "reason": str | None,
                "cooldown_until": datetime | None
            }
        """
        status = await self._get_status(user_id, wallet_id)
        now = datetime.now(timezone.utc)
        
        if not status:
            return {
                "active": False,
                "remaining_seconds": 0,
                "reason": None,
                "cooldown_until": None
            }
        
        cooldown_until = status.get("cooldown_until")
        if not cooldown_until:
            return {
                "active": False,
                "remaining_seconds": 0,
                "reason": None,
                "cooldown_until": None
            }
        
        # Check if cooldown is still active
        if cooldown_until > now:
            remaining = (cooldown_until - now).total_seconds()
            return {
                "active": True,
                "remaining_seconds": int(remaining),
                "reason": status.get("cooldown_reason", "Cooldown active"),
                "cooldown_until": cooldown_until
            }
        
        # Cooldown expired
        return {
            "active": False,
            "remaining_seconds": 0,
            "reason": None,
            "cooldown_until": None
        }
    
    async def start_cooldown(
        self, 
        user_id: str, 
        wallet_id: str, 
        reason: str,
        duration_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Start a cooldown period.
        
        Args:
            user_id: User ID
            wallet_id: Wallet ID
            reason: Reason for cooldown
            duration_seconds: Custom duration (uses default if not specified)
            
        Returns:
            Cooldown status
        """
        now = datetime.now(timezone.utc)
        duration = duration_seconds or self.MIN_COOLDOWN_SECONDS
        cooldown_until = now + timedelta(seconds=duration)
        
        await self.collection.update_one(
            {
                "user_id": ObjectId(user_id),
                "wallet_id": ObjectId(wallet_id)
            },
            {
                "$set": {
                    "cooldown_until": cooldown_until,
                    "cooldown_reason": reason,
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "user_id": ObjectId(user_id),
                    "wallet_id": ObjectId(wallet_id),
                    "circuit_breaker_tripped": False,
                    "consecutive_losses": 0,
                    "daily_pnl": 0.0,
                    "daily_trades": 0,
                    "emergency_stop": False,
                    "created_at": now,
                }
            },
            upsert=True
        )
        
        logger.info(
            f"Cooldown started: user={user_id}, wallet={wallet_id}, "
            f"duration={duration}s, reason={reason}"
        )
        
        return {
            "active": True,
            "remaining_seconds": duration,
            "reason": reason,
            "cooldown_until": cooldown_until
        }
    
    async def start_loss_cooldown(
        self, 
        user_id: str, 
        wallet_id: str,
        consecutive_losses: int = 1
    ) -> Dict[str, Any]:
        """
        Start cooldown after a loss with progressive duration.
        
        Args:
            user_id: User ID
            wallet_id: Wallet ID
            consecutive_losses: Number of consecutive losses
            
        Returns:
            Cooldown status
        """
        # Determine cooldown duration based on consecutive losses
        if consecutive_losses >= 2:
            duration = self.DOUBLE_LOSS_COOLDOWN_SECONDS
            reason = f"Extended cooldown after {consecutive_losses} consecutive losses"
        else:
            duration = self.LOSS_COOLDOWN_SECONDS
            reason = "Cooldown after loss (take a break and review)"
        
        return await self.start_cooldown(user_id, wallet_id, reason, duration)
    
    async def start_trade_cooldown(
        self, 
        user_id: str, 
        wallet_id: str
    ) -> Dict[str, Any]:
        """
        Start minimum cooldown after any trade.
        
        Returns:
            Cooldown status
        """
        return await self.start_cooldown(
            user_id, 
            wallet_id, 
            "Minimum interval between trades",
            self.MIN_COOLDOWN_SECONDS
        )
    
    async def clear_cooldown(
        self, 
        user_id: str, 
        wallet_id: str
    ) -> Dict[str, Any]:
        """
        Clear cooldown (admin/manual reset).
        
        Returns:
            Cooldown status
        """
        now = datetime.now(timezone.utc)
        
        await self.collection.update_one(
            {
                "user_id": ObjectId(user_id),
                "wallet_id": ObjectId(wallet_id)
            },
            {
                "$set": {
                    "cooldown_until": None,
                    "cooldown_reason": None,
                    "updated_at": now,
                }
            }
        )
        
        logger.info(f"Cooldown cleared: user={user_id}, wallet={wallet_id}")
        
        return {
            "active": False,
            "remaining_seconds": 0,
            "reason": None,
            "cooldown_until": None
        }


# Singleton instance getter
_cooldown_service: Optional[CooldownService] = None


def get_cooldown_service(db: AsyncIOMotorDatabase) -> CooldownService:
    """Get or create cooldown service instance."""
    global _cooldown_service
    if _cooldown_service is None:
        _cooldown_service = CooldownService(db)
    return _cooldown_service
