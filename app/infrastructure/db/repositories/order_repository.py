"""
Order Repository

Repository for order data access with automatic database routing.
"""

from typing import Optional, List, Dict, Any
from bson import ObjectId

from app.infrastructure.db.repository import BaseRepository
from app.domain.models.order import Order


class OrderRepository(BaseRepository):
    """Repository for orders with automatic database routing."""
    
    def __init__(self):
        super().__init__("orders")
    
    async def save(self, order: Order) -> Order:
        """
        Save order (insert or update).
        
        Uses Pydantic's model_dump() for clean conversion.
        Automatically routes to correct database (real/demo) based on context.
        
        Args:
            order: Order domain model
            
        Returns:
            Order: Saved order with ID set
        """
        # Model → Dict using aliases (_id, etc.)
        data = order.model_dump(by_alias=True, exclude_none=True)
        
        # Convert PyObjectId to ObjectId for MongoDB
        # PyObjectId serializes to string, so convert back to ObjectId
        if "_id" in data and data["_id"]:
            data["_id"] = ObjectId(data["_id"])
        if "user_id" in data:
            data["user_id"] = ObjectId(data["user_id"]) if not isinstance(data["user_id"], ObjectId) else data["user_id"]
        if "user_wallet_id" in data:
            data["user_wallet_id"] = ObjectId(data["user_wallet_id"]) if not isinstance(data["user_wallet_id"], ObjectId) else data["user_wallet_id"]
        if data.get("position_id"):
            data["position_id"] = ObjectId(data["position_id"]) if not isinstance(data["position_id"], ObjectId) else data["position_id"]
        if data.get("flow_id"):
            data["flow_id"] = ObjectId(data["flow_id"]) if not isinstance(data["flow_id"], ObjectId) else data["flow_id"]
        if data.get("execution_id"):
            data["execution_id"] = ObjectId(data["execution_id"]) if not isinstance(data["execution_id"], ObjectId) else data["execution_id"]
        if data.get("ai_agent_id"):
            data["ai_agent_id"] = ObjectId(data["ai_agent_id"]) if not isinstance(data["ai_agent_id"], ObjectId) else data["ai_agent_id"]
        
        # Convert Decimal to float for MongoDB (MongoDB doesn't support Decimal)
        from decimal import Decimal
        for key, value in list(data.items()):
            if isinstance(value, Decimal):
                data[key] = float(value)
            elif isinstance(value, dict):
                data[key] = {k: float(v) if isinstance(v, Decimal) else v for k, v in value.items()}
            elif isinstance(value, list):
                data[key] = [
                    {k: float(v) if isinstance(v, Decimal) else v for k, v in item.items()} if isinstance(item, dict) else item
                    for item in value
                ]
        
        if order.id:
            # Update existing order
            order_id = ObjectId(order.id) if isinstance(order.id, str) else order.id
            await self.update_one(
                {"_id": order_id},
                {"$set": data}
            )
            order.id = str(order_id)
        else:
            # Insert new order
            result = await self.insert_one(data)
            order.id = str(result)
        
        return order
    
    async def find_by_id(self, order_id: str) -> Optional[Order]:
        """
        Find order by ID.
        
        Args:
            order_id: Order ID
            
        Returns:
            Order domain model or None if not found
        """
        data = await super().find_by_id(order_id)
        if not data:
            return None
        
        # Convert MongoDB dict to Order domain model
        return self._dict_to_order(data)
    
    def _dict_to_order(self, data: Dict[str, Any]) -> Order:
        """
        Convert MongoDB dict to Order domain model.
        
        Handles ObjectId → string and float → Decimal conversion.
        """
        from decimal import Decimal
        
        # Convert ObjectId to string
        if "_id" in data:
            data["id"] = str(data["_id"])
        if "user_id" in data:
            data["user_id"] = str(data["user_id"])
        if "user_wallet_id" in data:
            data["user_wallet_id"] = str(data["user_wallet_id"])
        if data.get("position_id"):
            data["position_id"] = str(data["position_id"])
        if data.get("flow_id"):
            data["flow_id"] = str(data["flow_id"])
        if data.get("execution_id"):
            data["execution_id"] = str(data["execution_id"])
        if data.get("ai_agent_id"):
            data["ai_agent_id"] = str(data["ai_agent_id"])
        
        # Convert float to Decimal for numeric fields
        decimal_fields = [
            "requested_amount", "filled_amount", "remaining_amount",
            "limit_price", "stop_price", "average_fill_price",
            "total_fees", "total_fees_usd"
        ]
        for field in decimal_fields:
            if field in data and data[field] is not None:
                data[field] = Decimal(str(data[field]))
        
        # Convert fills
        if "fills" in data:
            for fill in data["fills"]:
                if "amount" in fill:
                    fill["amount"] = Decimal(str(fill["amount"]))
                if "price" in fill:
                    fill["price"] = Decimal(str(fill["price"]))
                if "fee" in fill:
                    fill["fee"] = Decimal(str(fill["fee"]))
        
        return Order(**data)
    
    async def find_by_user(
        self,
        user_id: str,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        flow_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Order]:
        """
        Find orders by user ID.
        
        Args:
            user_id: User ID
            status: Optional status filter
            symbol: Optional symbol filter
            flow_id: Optional flow ID filter
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            
        Returns:
            List of Order domain models
        """
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
        
        results = await self.find(
            filter=filter,
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)]
        )
        
        return [self._dict_to_order(doc) for doc in results]
    
    async def count_by_user(
        self,
        user_id: str,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        flow_id: Optional[str] = None
    ) -> int:
        """
        Count orders by user ID.
        
        Args:
            user_id: User ID
            status: Optional status filter
            symbol: Optional symbol filter
            flow_id: Optional flow ID filter
            
        Returns:
            Number of matching orders
        """
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
    
    async def delete_one(self, order_id: str) -> bool:
        """
        Soft delete an order.
        
        Args:
            order_id: Order ID
            
        Returns:
            True if order was deleted
        """
        from datetime import datetime
        return await self.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"deleted_at": datetime.utcnow()}}
        )


# Factory function for dependency injection
def get_order_repository() -> OrderRepository:
    """Get order repository instance."""
    return OrderRepository()
