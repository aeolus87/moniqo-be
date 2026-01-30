"""
Position Repository

Repository for position data access with automatic database routing.
"""

from typing import Optional, List, Dict, Any
from bson import ObjectId
from decimal import Decimal

from app.infrastructure.db.repository import BaseRepository
from app.domain.models.position import Position


class PositionRepository(BaseRepository):
    """Repository for positions with automatic database routing."""
    
    def __init__(self):
        super().__init__("positions")
    
    async def save(self, position: Position) -> Position:
        """
        Save position (insert or update).
        
        Uses Pydantic's model_dump() for clean conversion.
        Automatically routes to correct database (real/demo) based on context.
        
        Args:
            position: Position domain model
            
        Returns:
            Position: Saved position with ID set
        """
        # Model → Dict using aliases (_id, etc.)
        data = position.model_dump(by_alias=True, exclude_none=True)
        
        # Convert PyObjectId to ObjectId for MongoDB
        if "_id" in data and data["_id"]:
            data["_id"] = ObjectId(data["_id"]) if not isinstance(data["_id"], ObjectId) else data["_id"]
        if "user_id" in data:
            data["user_id"] = ObjectId(data["user_id"]) if not isinstance(data["user_id"], ObjectId) else data["user_id"]
        if "user_wallet_id" in data:
            data["user_wallet_id"] = ObjectId(data["user_wallet_id"]) if not isinstance(data["user_wallet_id"], ObjectId) else data["user_wallet_id"]
        if data.get("flow_id"):
            data["flow_id"] = ObjectId(data["flow_id"]) if not isinstance(data["flow_id"], ObjectId) else data["flow_id"]
        
        # Convert Decimal to float for MongoDB (MongoDB doesn't support Decimal)
        # Note: entry, current, exit dicts may contain Decimal values
        def convert_decimals(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: convert_decimals(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_decimals(item) for item in obj]
            return obj
        
        data = convert_decimals(data)
        
        if position.id:
            # Update existing position
            position_id = ObjectId(position.id) if isinstance(position.id, str) else position.id
            await self.update_one(
                {"_id": position_id},
                {"$set": data}
            )
            position.id = str(position_id)
        else:
            # Insert new position
            result = await self.insert_one(data)
            position.id = str(result)
        
        return position
    
    def _dict_to_position(self, data: Dict[str, Any]) -> Position:
        """
        Convert MongoDB dict to Position domain model.
        
        Handles ObjectId → string and float → Decimal conversion.
        """
        # Convert ObjectId to string
        if "_id" in data:
            data["id"] = str(data["_id"])
        if "user_id" in data:
            data["user_id"] = str(data["user_id"])
        if "user_wallet_id" in data:
            data["user_wallet_id"] = str(data["user_wallet_id"])
        if data.get("flow_id"):
            data["flow_id"] = str(data["flow_id"])
        
        # Convert float to Decimal for numeric fields in entry/current/exit dicts
        def convert_floats_to_decimals(obj):
            if isinstance(obj, float):
                return Decimal(str(obj))
            elif isinstance(obj, dict):
                return {k: convert_floats_to_decimals(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_floats_to_decimals(item) for item in obj]
            return obj
        
        # Convert entry, current, exit dicts
        if "entry" in data:
            data["entry"] = convert_floats_to_decimals(data["entry"])
        if "current" in data and data["current"]:
            data["current"] = convert_floats_to_decimals(data["current"])
        if "exit" in data and data["exit"]:
            data["exit"] = convert_floats_to_decimals(data["exit"])
        if "statistics" in data:
            data["statistics"] = convert_floats_to_decimals(data["statistics"])
        
        return Position(**data)
    
    async def find_by_id(self, position_id: str) -> Optional[Position]:
        """
        Find position by ID.
        
        Args:
            position_id: Position ID
            
        Returns:
            Position domain model or None if not found
        """
        data = await super().find_by_id(position_id)
        if not data:
            return None
        return self._dict_to_position(data)
    
    async def find_by_user(
        self,
        user_id: str,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Position]:
        """
        Find positions by user ID.
        
        Args:
            user_id: User ID
            status: Optional status filter
            symbol: Optional symbol filter
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            
        Returns:
            List of Position domain models
        """
        filter: Dict[str, Any] = {
            "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id,
            "deleted_at": None
        }
        
        if status:
            filter["status"] = status
        if symbol:
            filter["symbol"] = symbol
        
        results = await self.find(
            filter=filter,
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)]
        )
        
        return [self._dict_to_position(doc) for doc in results]
    
    async def count_by_user(
        self,
        user_id: str,
        status: Optional[str] = None,
        symbol: Optional[str] = None
    ) -> int:
        """
        Count positions by user ID.
        
        Args:
            user_id: User ID
            status: Optional status filter
            symbol: Optional symbol filter
            
        Returns:
            Number of matching positions
        """
        filter: Dict[str, Any] = {
            "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id,
            "deleted_at": None
        }
        
        if status:
            filter["status"] = status
        if symbol:
            filter["symbol"] = symbol
        
        return await self.count_documents(filter)
    
    async def find_open_positions(self, user_id: str) -> List[Position]:
        """
        Find all open positions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of open Position domain models
        """
        filter: Dict[str, Any] = {
            "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id,
            "status": "open",
            "deleted_at": None
        }
        
        results = await self.find(
            filter=filter,
            sort=[("created_at", -1)]
        )
        
        return [self._dict_to_position(doc) for doc in results]


# Factory function for dependency injection
def get_position_repository() -> PositionRepository:
    """Get position repository instance."""
    return PositionRepository()
