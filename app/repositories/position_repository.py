"""
Position Repository

Repository pattern for position data access.
Uses DatabaseProvider for automatic database routing based on trading mode context.
"""

from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
from bson import ObjectId

from app.infrastructure.db.repository import BaseRepository


class PositionRepository(BaseRepository):
    """
    Repository for positions with automatic database routing.
    
    Automatically routes to correct database (real/demo) based on trading mode context.
    """
    
    def __init__(self):
        super().__init__("positions")
    
    async def find_by_id(self, position_id: str) -> Optional[Dict[str, Any]]:
        """Find position by ID."""
        return await super().find_by_id(position_id)
    
    async def find_by_user(
        self,
        user_id: str,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Find positions by user ID."""
        filter: Dict[str, Any] = {
            "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id,
            "deleted_at": None
        }
        
        if status:
            filter["status"] = status
        if symbol:
            filter["symbol"] = symbol
        
        return await self.find(
            filter=filter,
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)]
        )
    
    async def count_by_user(
        self,
        user_id: str,
        status: Optional[str] = None,
        symbol: Optional[str] = None
    ) -> int:
        """Count positions by user ID."""
        filter: Dict[str, Any] = {
            "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id,
            "deleted_at": None
        }
        
        if status:
            filter["status"] = status
        if symbol:
            filter["symbol"] = symbol
        
        return await self.count_documents(filter)
    
    async def insert_one(self, position_data: Dict[str, Any]) -> ObjectId:
        """Insert a new position."""
        return await super().insert_one(position_data)
    
    async def update_one(
        self,
        position_id: str,
        update_data: Dict[str, Any]
    ) -> bool:
        """Update a position."""
        return await super().update_one(
            {"_id": ObjectId(position_id)},
            {"$set": update_data}
        )
    
    async def find_open_positions(self, user_id: str) -> List[Dict[str, Any]]:
        """Find all open positions for a user."""
        filter = {
            "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id,
            "status": {"$in": ["opening", "open", "closing"]},
            "deleted_at": None
        }
        return await self.find(filter=filter)


def get_position_repository() -> PositionRepository:
    """
    Factory function to get position repository.
    
    Returns:
        PositionRepository instance (automatically routes based on context)
    """
    return PositionRepository()
