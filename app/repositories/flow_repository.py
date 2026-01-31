"""
Flow Repository

Repository pattern for flow data access.
Uses DatabaseProvider for automatic database routing based on trading mode context.
"""

from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
from bson import ObjectId

from app.infrastructure.db.repository import BaseRepository


class FlowRepository(BaseRepository):
    """
    Repository for flows with automatic database routing.
    
    Automatically routes to correct database (real/demo) based on trading mode context.
    """
    
    def __init__(self):
        super().__init__("flows")
    
    async def find_by_id(self, flow_id: str) -> Optional[Dict[str, Any]]:
        """Find flow by ID."""
        return await super().find_by_id(flow_id)
    
    async def find_by_user(
        self,
        user_id: str,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Find flows by user ID."""
        filter: Dict[str, Any] = {
            "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id,
            "deleted_at": None
        }
        
        if status:
            filter["status"] = status
        
        return await self.find(
            filter=filter,
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)]
        )
    
    async def count_by_user(
        self,
        user_id: str,
        status: Optional[str] = None
    ) -> int:
        """Count flows by user ID."""
        filter: Dict[str, Any] = {
            "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id,
            "deleted_at": None
        }
        
        if status:
            filter["status"] = status
        
        return await self.count_documents(filter)
    
    async def insert_one(self, flow_data: Dict[str, Any]) -> ObjectId:
        """Insert a new flow."""
        return await super().insert_one(flow_data)
    
    async def update_one(
        self,
        flow_id: str,
        update_data: Dict[str, Any]
    ) -> bool:
        """Update a flow."""
        return await super().update_one(
            {"_id": ObjectId(flow_id)},
            {"$set": update_data}
        )
    
    async def delete_one(self, flow_id: str) -> bool:
        """Soft delete a flow."""
        from datetime import datetime, timezone
        return await super().update_one(
            {"_id": ObjectId(flow_id)},
            {"$set": {"deleted_at": datetime.now(timezone.utc)}}
        )


def get_flow_repository() -> FlowRepository:
    """
    Factory function to get flow repository.
    
    Returns:
        FlowRepository instance (automatically routes based on context)
    """
    return FlowRepository()
