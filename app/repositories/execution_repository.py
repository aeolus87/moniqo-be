"""
Execution Repository

Repository pattern for execution data access.
Uses DatabaseProvider for automatic database routing based on trading mode context.
"""

from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
from bson import ObjectId

from app.infrastructure.db.repository import BaseRepository


class ExecutionRepository(BaseRepository):
    """
    Repository for executions with automatic database routing.
    
    Automatically routes to correct database (real/demo) based on trading mode context.
    """
    
    def __init__(self):
        super().__init__("executions")
    
    async def find_by_id(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Find execution by ID."""
        return await super().find_by_id(execution_id)
    
    async def find_by_flow(
        self,
        flow_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Find executions by flow ID."""
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
        """Count executions by flow ID."""
        filter = {
            "flow_id": ObjectId(flow_id) if isinstance(flow_id, str) else flow_id
        }
        return await self.count_documents(filter)
    
    async def insert_one(self, execution_data: Dict[str, Any]) -> ObjectId:
        """Insert a new execution."""
        return await super().insert_one(execution_data)
    
    async def update_one(
        self,
        execution_id: str,
        update_data: Dict[str, Any]
    ) -> bool:
        """Update an execution."""
        return await super().update_one(
            {"_id": ObjectId(execution_id)},
            {"$set": update_data}
        )
    
    async def delete_one(self, execution_id: str) -> bool:
        """Delete an execution."""
        return await super().delete_one({"_id": ObjectId(execution_id)})
    
    async def find_running_executions(self) -> List[Dict[str, Any]]:
        """Find all running executions."""
        filter = {
            "status": {"$in": ["pending", "running"]}
        }
        return await self.find(filter=filter)


def get_execution_repository() -> ExecutionRepository:
    """
    Factory function to get execution repository.
    
    Returns:
        ExecutionRepository instance (automatically routes based on context)
    """
    return ExecutionRepository()
