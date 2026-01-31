"""
Order Repository

Repository pattern for order data access.
Uses DatabaseProvider for automatic database routing based on trading mode context.
"""

from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
from bson import ObjectId

from app.infrastructure.db.repository import BaseRepository


class OrderRepository(BaseRepository):
    """
    Repository for orders with automatic database routing.
    
    Automatically routes to correct database (real/demo) based on trading mode context.
    """
    
    def __init__(self):
        super().__init__("orders")
    
    async def find_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Find order by ID."""
        return await super().find_by_id(order_id)
    
    async def find_by_user(
        self,
        user_id: str,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        flow_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Find orders by user ID."""
        filter: Dict[str, Any] = {
            "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id,
            "deleted_at": None
        }
        
        if status:
            filter["status"] = status
        if symbol:
            filter["symbol"] = symbol
        if flow_id:
            filter["flow_id"] = ObjectId(flow_id) if isinstance(flow_id, str) else flow_id
        
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
        symbol: Optional[str] = None,
        flow_id: Optional[str] = None
    ) -> int:
        """Count orders by user ID."""
        filter: Dict[str, Any] = {
            "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id,
            "deleted_at": None
        }
        
        if status:
            filter["status"] = status
        if symbol:
            filter["symbol"] = symbol
        if flow_id:
            filter["flow_id"] = ObjectId(flow_id) if isinstance(flow_id, str) else flow_id
        
        return await self.count_documents(filter)
    
    async def insert_one(self, order_data: Dict[str, Any]) -> ObjectId:
        """Insert a new order."""
        return await super().insert_one(order_data)
    
    async def update_one(
        self,
        order_id: str,
        update_data: Dict[str, Any]
    ) -> bool:
        """Update an order."""
        return await super().update_one(
            {"_id": ObjectId(order_id)},
            {"$set": update_data}
        )
    
    async def delete_one(self, order_id: str) -> bool:
        """Soft delete an order."""
        from datetime import datetime, timezone
        return await super().update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"deleted_at": datetime.now(timezone.utc)}}
        )


def get_order_repository() -> OrderRepository:
    """
    Factory function to get order repository.
    
    Returns:
        OrderRepository instance (automatically routes based on context)
    """
    return OrderRepository()
