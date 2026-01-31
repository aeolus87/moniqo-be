"""
User Wallet Repository

Repository pattern for user wallet data access.
Uses DatabaseProvider for automatic database routing based on trading mode context.
"""

from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
from bson import ObjectId

from app.infrastructure.db.repository import BaseRepository


class UserWalletRepository(BaseRepository):
    """
    Repository for user wallets with automatic database routing.
    
    Automatically routes to correct database (real/demo) based on trading mode context.
    """
    
    def __init__(self):
        super().__init__("user_wallets")
    
    async def find_by_id(self, wallet_id: str) -> Optional[Dict[str, Any]]:
        """Find user wallet by ID."""
        return await super().find_by_id(wallet_id)
    
    async def find_by_user(
        self,
        user_id: str,
        is_active: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """Find user wallets by user ID."""
        filter: Dict[str, Any] = {
            "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id,
            "deleted_at": None
        }
        
        if is_active is not None:
            filter["is_active"] = is_active
        
        return await self.find(filter=filter, sort=[("created_at", -1)])
    
    async def insert_one(self, wallet_data: Dict[str, Any]) -> ObjectId:
        """Insert a new user wallet."""
        return await super().insert_one(wallet_data)
    
    async def update_one(
        self,
        wallet_id: str,
        update_data: Dict[str, Any]
    ) -> bool:
        """Update a user wallet."""
        return await super().update_one(
            {"_id": ObjectId(wallet_id)},
            {"$set": update_data}
        )
    
    async def delete_one(self, wallet_id: str) -> bool:
        """Soft delete a user wallet."""
        from datetime import datetime, timezone
        return await super().update_one(
            {"_id": ObjectId(wallet_id)},
            {"$set": {"deleted_at": datetime.now(timezone.utc)}}
        )


def get_user_wallet_repository() -> UserWalletRepository:
    """
    Factory function to get user wallet repository.
    
    Returns:
        UserWalletRepository instance (automatically routes based on context)
    """
    return UserWalletRepository()
