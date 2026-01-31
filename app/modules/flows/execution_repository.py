"""
Execution Repository

Repository for execution data access with automatic database routing.
"""

from typing import List, Dict, Any
from bson import ObjectId

from app.infrastructure.db.repository import BaseRepository


class ExecutionRepository(BaseRepository):
    """Repository for executions with automatic database routing."""
    
    def __init__(self):
        super().__init__("executions")
    
    async def find_by_flow(
        self,
        flow_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Find executions by flow ID.
        
        Args:
            flow_id: Flow ID
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            
        Returns:
            List of execution documents
        """
        filter = {
            "flow_id": ObjectId(flow_id) if isinstance(flow_id, str) else flow_id
        }
        
        return await self.find(
            filter=filter,
            skip=skip,
            limit=limit,
            sort=[("started_at", -1)]
        )
    
    async def count_by_flow(self, flow_id: str) -> int:
        """
        Count executions by flow ID.
        
        Args:
            flow_id: Flow ID
            
        Returns:
            Number of matching executions
        """
        filter = {
            "flow_id": ObjectId(flow_id) if isinstance(flow_id, str) else flow_id
        }
        return await self.count_documents(filter)
    
    async def find_running_executions(self) -> List[Dict[str, Any]]:
        """
        Find all running executions.
        
        Returns:
            List of running execution documents
        """
        filter = {
            "status": {"$in": ["pending", "running"]}
        }
        return await self.find(filter=filter)


# Factory function for dependency injection
def get_execution_repository() -> ExecutionRepository:
    """Get execution repository instance."""
    return ExecutionRepository()
