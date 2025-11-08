"""
User_Plans MongoDB model.

Handles database operations for user subscriptions.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from app.utils.logger import get_logger

logger = get_logger(__name__)


class UserPlan:
    """UserPlan model for database operations."""
    
    @staticmethod
    async def create_subscription(
        db: AsyncIOMotorDatabase,
        user_id: str,
        plan_id: str,
        billing_cycle: str,
        auto_renew: bool,
        payment_method: Optional[Dict[str, str]] = None
    ) -> dict:
        """
        Create a new subscription for a user.
        
        Args:
            db: Database connection
            user_id: User ID
            plan_id: Plan ID
            billing_cycle: Billing cycle (monthly, yearly)
            auto_renew: Auto-renew flag
            payment_method: Payment method details
            
        Returns:
            dict: Created subscription document
        """
        start_date = datetime.utcnow()
        
        # Calculate end_date based on billing cycle
        if billing_cycle == "monthly":
            end_date = start_date + timedelta(days=30)
        elif billing_cycle == "yearly":
            end_date = start_date + timedelta(days=365)
        else:
            end_date = start_date + timedelta(days=30)  # Default to monthly
        
        subscription_doc = {
            "user_id": ObjectId(user_id),
            "plan_id": ObjectId(plan_id),
            "status": "active",
            "start_date": start_date,
            "end_date": end_date,
            "auto_renew": auto_renew,
            "billing_cycle": billing_cycle,
            "payment_method": payment_method,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_deleted": False
        }
        
        result = await db.user_plans.insert_one(subscription_doc)
        subscription_doc["_id"] = str(result.inserted_id)
        subscription_doc["user_id"] = str(subscription_doc["user_id"])
        subscription_doc["plan_id"] = str(subscription_doc["plan_id"])
        
        logger.info(f"Subscription created: subscription_id={subscription_doc['_id']}, user_id={user_id}, plan_id={plan_id}")
        return subscription_doc
    
    @staticmethod
    async def get_subscription_by_id(db: AsyncIOMotorDatabase, subscription_id: str) -> dict | None:
        """
        Get subscription by ID.
        
        Args:
            db: Database connection
            subscription_id: Subscription ID
            
        Returns:
            dict | None: Subscription document or None if not found
        """
        try:
            subscription = await db.user_plans.find_one({
                "_id": ObjectId(subscription_id),
                "is_deleted": False
            })
            
            if subscription:
                subscription["_id"] = str(subscription["_id"])
                subscription["user_id"] = str(subscription["user_id"])
                subscription["plan_id"] = str(subscription["plan_id"])
            
            return subscription
        except Exception as e:
            logger.error(f"Error getting subscription by ID: {str(e)}")
            return None
    
    @staticmethod
    async def get_user_current_subscription(db: AsyncIOMotorDatabase, user_id: str) -> dict | None:
        """
        Get user's current active subscription.
        
        Args:
            db: Database connection
            user_id: User ID
            
        Returns:
            dict | None: Active subscription or None if not found
        """
        subscription = await db.user_plans.find_one({
            "user_id": ObjectId(user_id),
            "status": "active",
            "is_deleted": False
        })
        
        if subscription:
            subscription["_id"] = str(subscription["_id"])
            subscription["user_id"] = str(subscription["user_id"])
            subscription["plan_id"] = str(subscription["plan_id"])
        
        return subscription
    
    @staticmethod
    async def list_user_subscriptions(
        db: AsyncIOMotorDatabase,
        user_id: str,
        limit: int = 10,
        offset: int = 0
    ) -> tuple[List[dict], int]:
        """
        List user's subscriptions with pagination.
        
        Args:
            db: Database connection
            user_id: User ID
            limit: Number of items per page
            offset: Number of items to skip
            
        Returns:
            tuple: (list of subscriptions, total count)
        """
        cursor = db.user_plans.find({
            "user_id": ObjectId(user_id),
            "is_deleted": False
        }).sort("created_at", -1)
        
        total = await db.user_plans.count_documents({
            "user_id": ObjectId(user_id),
            "is_deleted": False
        })
        
        subscriptions = await cursor.skip(offset).limit(limit).to_list(length=limit)
        
        # Convert ObjectId to string
        for subscription in subscriptions:
            subscription["_id"] = str(subscription["_id"])
            subscription["user_id"] = str(subscription["user_id"])
            subscription["plan_id"] = str(subscription["plan_id"])
        
        return subscriptions, total
    
    @staticmethod
    async def update_subscription(
        db: AsyncIOMotorDatabase,
        subscription_id: str,
        update_data: dict
    ) -> dict | None:
        """
        Update subscription.
        
        Args:
            db: Database connection
            subscription_id: Subscription ID
            update_data: Fields to update
            
        Returns:
            dict | None: Updated subscription document or None if not found
        """
        try:
            update_data["updated_at"] = datetime.utcnow()
            
            result = await db.user_plans.find_one_and_update(
                {"_id": ObjectId(subscription_id), "is_deleted": False},
                {"$set": update_data},
                return_document=True
            )
            
            if result:
                result["_id"] = str(result["_id"])
                result["user_id"] = str(result["user_id"])
                result["plan_id"] = str(result["plan_id"])
                logger.info(f"Subscription updated: subscription_id={subscription_id}")
            
            return result
        except Exception as e:
            logger.error(f"Error updating subscription: {str(e)}")
            return None
    
    @staticmethod
    async def cancel_subscription(db: AsyncIOMotorDatabase, subscription_id: str) -> bool:
        """
        Cancel subscription (set status to cancelled).
        
        Args:
            db: Database connection
            subscription_id: Subscription ID
            
        Returns:
            bool: True if cancelled, False otherwise
        """
        try:
            result = await db.user_plans.update_one(
                {"_id": ObjectId(subscription_id), "is_deleted": False},
                {"$set": {
                    "status": "cancelled",
                    "auto_renew": False,
                    "updated_at": datetime.utcnow()
                }}
            )
            
            if result.modified_count > 0:
                logger.info(f"Subscription cancelled: subscription_id={subscription_id}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error cancelling subscription: {str(e)}")
            return False
    
    @staticmethod
    async def renew_subscription(
        db: AsyncIOMotorDatabase,
        subscription_id: str,
        billing_cycle: str
    ) -> dict | None:
        """
        Renew subscription (extend end_date).
        
        Args:
            db: Database connection
            subscription_id: Subscription ID
            billing_cycle: Billing cycle to extend by
            
        Returns:
            dict | None: Updated subscription or None if not found
        """
        try:
            # Get current subscription
            subscription = await db.user_plans.find_one({
                "_id": ObjectId(subscription_id),
                "is_deleted": False
            })
            
            if not subscription:
                return None
            
            # Calculate new end_date
            current_end_date = subscription["end_date"]
            if billing_cycle == "monthly":
                new_end_date = current_end_date + timedelta(days=30)
            elif billing_cycle == "yearly":
                new_end_date = current_end_date + timedelta(days=365)
            else:
                new_end_date = current_end_date + timedelta(days=30)
            
            # Update subscription
            result = await db.user_plans.find_one_and_update(
                {"_id": ObjectId(subscription_id), "is_deleted": False},
                {"$set": {
                    "end_date": new_end_date,
                    "status": "active",
                    "updated_at": datetime.utcnow()
                }},
                return_document=True
            )
            
            if result:
                result["_id"] = str(result["_id"])
                result["user_id"] = str(result["user_id"])
                result["plan_id"] = str(result["plan_id"])
                logger.info(f"Subscription renewed: subscription_id={subscription_id}, new_end_date={new_end_date}")
            
            return result
        except Exception as e:
            logger.error(f"Error renewing subscription: {str(e)}")
            return None

