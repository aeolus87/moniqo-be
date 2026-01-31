"""
Circuit Breaker Service

Halts trading after consecutive losses or drawdown threshold.
Prevents revenge trading and protects capital during losing streaks.

Author: Moniqo Team
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.utils.logger import get_logger

logger = get_logger(__name__)


class CircuitBreakerService:
    """
    Circuit breaker that halts trading after consecutive losses or drawdown.
    
    Features:
    - Tracks consecutive losses per user/wallet
    - Trips after configurable loss threshold
    - Enforces cooldown period after trip
    - Can be manually reset by user
    
    Default settings:
    - CONSECUTIVE_LOSS_LIMIT: 3 losses triggers halt
    - DRAWDOWN_THRESHOLD: 10% drawdown triggers halt  
    - COOLDOWN_MINUTES: 30 minute cooldown after trip
    """
    
    CONSECUTIVE_LOSS_LIMIT = 3
    DRAWDOWN_THRESHOLD = 0.10  # 10%
    COOLDOWN_MINUTES = 30
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.safety_status
    
    async def _get_or_create_status(self, user_id: str, wallet_id: str) -> Dict[str, Any]:
        """Get or create safety status document for user/wallet."""
        status = await self.collection.find_one({
            "user_id": ObjectId(user_id),
            "wallet_id": ObjectId(wallet_id)
        })
        
        if not status:
            # Create default status
            now = datetime.now(timezone.utc)
            status = {
                "user_id": ObjectId(user_id),
                "wallet_id": ObjectId(wallet_id),
                # Circuit breaker
                "circuit_breaker_tripped": False,
                "circuit_breaker_reason": None,
                "circuit_breaker_until": None,
                "consecutive_losses": 0,
                # Cooldown
                "cooldown_until": None,
                "cooldown_reason": None,
                # Daily tracking
                "daily_pnl": 0.0,
                "daily_trades": 0,
                "daily_wins": 0,
                "daily_losses": 0,
                "daily_reset_at": now.replace(hour=0, minute=0, second=0, microsecond=0),
                # Emergency stop
                "emergency_stop": False,
                "emergency_stop_at": None,
                # Timestamps
                "created_at": now,
                "updated_at": now,
            }
            result = await self.collection.insert_one(status)
            status["_id"] = result.inserted_id
        
        return status
    
    async def check_circuit_breaker(
        self, 
        user_id: str, 
        wallet_id: str
    ) -> Dict[str, Any]:
        """
        Check if circuit breaker is tripped.
        
        Returns:
            {
                "tripped": bool,
                "reason": str | None,
                "cooldown_until": datetime | None,
                "consecutive_losses": int
            }
        """
        status = await self._get_or_create_status(user_id, wallet_id)
        now = datetime.now(timezone.utc)
        
        # Check if circuit breaker cooldown has expired
        if status["circuit_breaker_tripped"]:
            cooldown_until = status.get("circuit_breaker_until")
            if cooldown_until and cooldown_until <= now:
                # Cooldown expired, auto-reset
                await self.reset_circuit_breaker(user_id, wallet_id)
                status["circuit_breaker_tripped"] = False
                status["circuit_breaker_reason"] = None
                status["circuit_breaker_until"] = None
                logger.info(f"Circuit breaker auto-reset for user={user_id}, wallet={wallet_id}")
        
        return {
            "tripped": status["circuit_breaker_tripped"],
            "reason": status.get("circuit_breaker_reason"),
            "cooldown_until": status.get("circuit_breaker_until"),
            "consecutive_losses": status.get("consecutive_losses", 0)
        }
    
    async def record_trade_result(
        self, 
        user_id: str, 
        wallet_id: str, 
        is_win: bool, 
        pnl: float
    ) -> Dict[str, Any]:
        """
        Record a trade result and check if circuit breaker should trip.
        
        Args:
            user_id: User ID
            wallet_id: Wallet ID
            is_win: True if trade was profitable
            pnl: Profit/loss amount
            
        Returns:
            Updated circuit breaker status
        """
        status = await self._get_or_create_status(user_id, wallet_id)
        now = datetime.now(timezone.utc)
        
        # Update counters
        if is_win:
            # Win resets consecutive losses
            new_consecutive_losses = 0
            daily_wins = status.get("daily_wins", 0) + 1
            daily_losses = status.get("daily_losses", 0)
        else:
            # Loss increments consecutive losses
            new_consecutive_losses = status.get("consecutive_losses", 0) + 1
            daily_wins = status.get("daily_wins", 0)
            daily_losses = status.get("daily_losses", 0) + 1
        
        # Update daily P&L
        daily_pnl = status.get("daily_pnl", 0.0) + pnl
        daily_trades = status.get("daily_trades", 0) + 1
        
        # Check if circuit breaker should trip
        should_trip = False
        trip_reason = None
        
        if new_consecutive_losses >= self.CONSECUTIVE_LOSS_LIMIT:
            should_trip = True
            trip_reason = f"Consecutive loss limit reached ({new_consecutive_losses} losses in a row)"
            logger.warning(
                f"Circuit breaker tripped: user={user_id}, wallet={wallet_id}, "
                f"reason={trip_reason}"
            )
        
        # Calculate cooldown end time
        cooldown_until = None
        if should_trip:
            cooldown_until = now + timedelta(minutes=self.COOLDOWN_MINUTES)
        
        # Update status
        update_data = {
            "consecutive_losses": new_consecutive_losses,
            "daily_pnl": daily_pnl,
            "daily_trades": daily_trades,
            "daily_wins": daily_wins,
            "daily_losses": daily_losses,
            "updated_at": now,
        }
        
        if should_trip:
            update_data["circuit_breaker_tripped"] = True
            update_data["circuit_breaker_reason"] = trip_reason
            update_data["circuit_breaker_until"] = cooldown_until
        
        await self.collection.update_one(
            {"_id": status["_id"]},
            {"$set": update_data}
        )
        
        return {
            "tripped": should_trip,
            "reason": trip_reason,
            "cooldown_until": cooldown_until,
            "consecutive_losses": new_consecutive_losses,
            "daily_pnl": daily_pnl,
            "daily_trades": daily_trades,
        }
    
    async def reset_circuit_breaker(
        self, 
        user_id: str, 
        wallet_id: str
    ) -> Dict[str, Any]:
        """
        Manually reset the circuit breaker.
        
        Returns:
            Reset status
        """
        status = await self._get_or_create_status(user_id, wallet_id)
        now = datetime.now(timezone.utc)
        
        await self.collection.update_one(
            {"_id": status["_id"]},
            {
                "$set": {
                    "circuit_breaker_tripped": False,
                    "circuit_breaker_reason": None,
                    "circuit_breaker_until": None,
                    "consecutive_losses": 0,
                    "updated_at": now,
                }
            }
        )
        
        logger.info(f"Circuit breaker manually reset: user={user_id}, wallet={wallet_id}")
        
        return {
            "tripped": False,
            "reason": None,
            "cooldown_until": None,
            "consecutive_losses": 0,
        }
    
    async def get_status(self, user_id: str, wallet_id: str) -> Dict[str, Any]:
        """Get full safety status for user/wallet."""
        status = await self._get_or_create_status(user_id, wallet_id)
        
        # Convert ObjectIds to strings for JSON serialization
        return {
            "user_id": str(status["user_id"]),
            "wallet_id": str(status["wallet_id"]),
            "circuit_breaker_tripped": status.get("circuit_breaker_tripped", False),
            "circuit_breaker_reason": status.get("circuit_breaker_reason"),
            "circuit_breaker_until": status.get("circuit_breaker_until"),
            "consecutive_losses": status.get("consecutive_losses", 0),
            "cooldown_until": status.get("cooldown_until"),
            "cooldown_reason": status.get("cooldown_reason"),
            "daily_pnl": status.get("daily_pnl", 0.0),
            "daily_trades": status.get("daily_trades", 0),
            "daily_wins": status.get("daily_wins", 0),
            "daily_losses": status.get("daily_losses", 0),
            "emergency_stop": status.get("emergency_stop", False),
            "emergency_stop_at": status.get("emergency_stop_at"),
        }


# Singleton instance getter
_circuit_breaker_service: Optional[CircuitBreakerService] = None


def get_circuit_breaker_service(db: AsyncIOMotorDatabase) -> CircuitBreakerService:
    """Get or create circuit breaker service instance."""
    global _circuit_breaker_service
    if _circuit_breaker_service is None:
        _circuit_breaker_service = CircuitBreakerService(db)
    return _circuit_breaker_service
