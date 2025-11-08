"""
Plans MongoDB model.

Handles database operations for subscription plans.
"""

from datetime import datetime
from typing import List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Plan:
    """Plan model for database operations."""
    
    @staticmethod
    async def create_plan(
        db: AsyncIOMotorDatabase,
        name: str,
        description: str,
        price: float,
        features: List[Dict[str, str]],
        limits: List[Dict[str, Any]]
    ) -> dict:
        """
        Create a new plan in the database.
        
        Args:
            db: Database connection
            name: Plan name
            description: Plan description
            price: Monthly price
            features: List of features
            limits: List of limits
            
        Returns:
            dict: Created plan document
        """
        plan_doc = {
            "name": name,
            "description": description,
            "price": price,
            "features": features,
            "limits": limits,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_deleted": False
        }
        
        result = await db.plans.insert_one(plan_doc)
        plan_doc["_id"] = str(result.inserted_id)
        
        logger.info(f"Plan created: plan_id={plan_doc['_id']}, name={name}")
        return plan_doc
    
    @staticmethod
    async def get_plan_by_id(db: AsyncIOMotorDatabase, plan_id: str) -> dict | None:
        """
        Get plan by ID.
        
        Args:
            db: Database connection
            plan_id: Plan ID
            
        Returns:
            dict | None: Plan document or None if not found
        """
        try:
            plan = await db.plans.find_one({
                "_id": ObjectId(plan_id),
                "is_deleted": False
            })
            
            if plan:
                plan["_id"] = str(plan["_id"])
            
            return plan
        except Exception as e:
            logger.error(f"Error getting plan by ID: {str(e)}")
            return None
    
    @staticmethod
    async def get_plan_by_name(db: AsyncIOMotorDatabase, name: str) -> dict | None:
        """
        Get plan by name.
        
        Args:
            db: Database connection
            name: Plan name
            
        Returns:
            dict | None: Plan document or None if not found
        """
        plan = await db.plans.find_one({
            "name": name,
            "is_deleted": False
        })
        
        if plan:
            plan["_id"] = str(plan["_id"])
        
        return plan
    
    @staticmethod
    async def list_plans(
        db: AsyncIOMotorDatabase,
        limit: int = 10,
        offset: int = 0
    ) -> tuple[List[dict], int]:
        """
        List plans with pagination.
        
        Args:
            db: Database connection
            limit: Number of items per page
            offset: Number of items to skip
            
        Returns:
            tuple: (list of plans, total count)
        """
        cursor = db.plans.find({"is_deleted": False})
        
        total = await db.plans.count_documents({"is_deleted": False})
        
        plans = await cursor.skip(offset).limit(limit).to_list(length=limit)
        
        # Convert ObjectId to string
        for plan in plans:
            plan["_id"] = str(plan["_id"])
        
        return plans, total
    
    @staticmethod
    async def update_plan(
        db: AsyncIOMotorDatabase,
        plan_id: str,
        update_data: dict
    ) -> dict | None:
        """
        Update plan.
        
        Args:
            db: Database connection
            plan_id: Plan ID
            update_data: Fields to update
            
        Returns:
            dict | None: Updated plan document or None if not found
        """
        try:
            update_data["updated_at"] = datetime.utcnow()
            
            result = await db.plans.find_one_and_update(
                {"_id": ObjectId(plan_id), "is_deleted": False},
                {"$set": update_data},
                return_document=True
            )
            
            if result:
                result["_id"] = str(result["_id"])
                logger.info(f"Plan updated: plan_id={plan_id}")
            
            return result
        except Exception as e:
            logger.error(f"Error updating plan: {str(e)}")
            return None
    
    @staticmethod
    async def delete_plan(db: AsyncIOMotorDatabase, plan_id: str) -> bool:
        """
        Soft delete plan.
        
        Args:
            db: Database connection
            plan_id: Plan ID
            
        Returns:
            bool: True if deleted, False otherwise
        """
        try:
            result = await db.plans.update_one(
                {"_id": ObjectId(plan_id), "is_deleted": False},
                {"$set": {"is_deleted": True, "updated_at": datetime.utcnow()}}
            )
            
            if result.modified_count > 0:
                logger.info(f"Plan soft deleted: plan_id={plan_id}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error deleting plan: {str(e)}")
            return False

