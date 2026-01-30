"""
User Wallet Repository

Repository for user wallet data access with automatic database routing.
Note: Wallet definitions (wallets collection) are shared, but user_wallets are mode-specific.
"""

from typing import Optional, List, Dict, Any
from bson import ObjectId

from app.infrastructure.db.repository import BaseRepository
from app.domain.models.user_wallet import UserWallet


class UserWalletRepository(BaseRepository):
    """Repository for user wallets with automatic database routing."""
    
    def __init__(self):
        super().__init__("user_wallets")
    
    async def save(self, user_wallet: UserWallet) -> UserWallet:
        """
        Save user wallet (insert or update).
        
        Uses Pydantic's model_dump() for clean conversion.
        Automatically routes to correct database (real/demo) based on context.
        
        Args:
            user_wallet: UserWallet domain model
            
        Returns:
            UserWallet: Saved user wallet with ID set
        """
        # Model → Dict using aliases (_id, etc.)
        data = user_wallet.model_dump(by_alias=True, exclude_none=True)
        
        # Convert PyObjectId to ObjectId for MongoDB
        if "_id" in data and data["_id"]:
            data["_id"] = ObjectId(data["_id"]) if not isinstance(data["_id"], ObjectId) else data["_id"]
        if "user_id" in data:
            data["user_id"] = ObjectId(data["user_id"]) if not isinstance(data["user_id"], ObjectId) else data["user_id"]
        if "wallet_provider_id" in data:
            data["wallet_provider_id"] = ObjectId(data["wallet_provider_id"]) if not isinstance(data["wallet_provider_id"], ObjectId) else data["wallet_provider_id"]
        
        if user_wallet.id:
            # Update existing user wallet
            wallet_id = ObjectId(user_wallet.id) if isinstance(user_wallet.id, str) else user_wallet.id
            await self.update_one(
                {"_id": wallet_id},
                {"$set": data}
            )
            user_wallet.id = str(wallet_id)
        else:
            # Insert new user wallet
            result = await self.insert_one(data)
            user_wallet.id = str(result)
        
        return user_wallet
    
    def _dict_to_user_wallet(self, data: Dict[str, Any]) -> UserWallet:
        """
        Convert MongoDB dict to UserWallet domain model.
        
        Handles ObjectId → string conversion.
        """
        # Convert ObjectId to string
        if "_id" in data:
            data["id"] = str(data["_id"])
        if "user_id" in data:
            data["user_id"] = str(data["user_id"])
        if "wallet_provider_id" in data:
            data["wallet_provider_id"] = str(data["wallet_provider_id"])
        
        return UserWallet(**data)
    
    async def find_by_id(self, wallet_id: str) -> Optional[UserWallet]:
        """
        Find user wallet by ID.
        
        Args:
            wallet_id: User wallet ID
            
        Returns:
            UserWallet domain model or None if not found
        """
        data = await super().find_by_id(wallet_id)
        if not data:
            return None
        return self._dict_to_user_wallet(data)
    
    async def find_by_user(
        self,
        user_id: str,
        is_active: Optional[bool] = None
    ) -> List[UserWallet]:
        """
        Find user wallets by user ID.
        
        Args:
            user_id: User ID
            is_active: Optional active status filter
            
        Returns:
            List of UserWallet domain models
        """
        filter: Dict[str, Any] = {
            "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id,
            "deleted_at": None
        }
        
        if is_active is not None:
            filter["is_active"] = is_active
        
        results = await self.find(filter=filter, sort=[("created_at", -1)])
        
        return [self._dict_to_user_wallet(doc) for doc in results]
    
    async def delete_one(self, wallet_id: str) -> bool:
        """
        Soft delete a user wallet.
        
        Args:
            wallet_id: Wallet ID
            
        Returns:
            True if wallet was deleted
        """
        from datetime import datetime, timezone
        return await self.update_one(
            {"_id": ObjectId(wallet_id)},
            {"$set": {"deleted_at": datetime.now(timezone.utc)}}
        )


# Factory function for dependency injection
def get_user_wallet_repository() -> UserWalletRepository:
    """Get user wallet repository instance."""
    return UserWalletRepository()
