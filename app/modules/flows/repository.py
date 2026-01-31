"""
Flow Repository

Repository for flow data access with automatic database routing.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId

from app.infrastructure.db.repository import BaseRepository


class FlowRepository(BaseRepository):
    """Repository for flows with automatic database routing."""
    
    def __init__(self):
        super().__init__("flows")
    
    async def find_by_user(
        self,
        user_id: str,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Find flows by user ID.
        
        Args:
            user_id: User ID
            status: Optional status filter
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            
        Returns:
            List of flow documents
        """
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
        """
        Count flows by user ID.
        
        Args:
            user_id: User ID
            status: Optional status filter
            
        Returns:
            Number of matching flows
        """
        filter: Dict[str, Any] = {
            "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id,
            "deleted_at": None
        }
        
        if status:
            filter["status"] = status
        
        return await self.count_documents(filter)
    
    async def delete_one(self, flow_id: str) -> bool:
        """
        Soft delete a flow.
        
        Args:
            flow_id: Flow ID
            
        Returns:
            True if flow was deleted
        """
        return await self.update_one(
            {"_id": ObjectId(flow_id)},
            {"$set": {"deleted_at": datetime.utcnow()}}
        )


# Factory function for dependency injection
def get_flow_repository() -> FlowRepository:
    """Get flow repository instance."""
    return FlowRepository()
