"""
User_Plans business logic.

Service layer for subscription management operations.
"""

from typing import List
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.modules.user_plans.models import UserPlan
from app.modules.user_plans.schemas import UserPlanCreate, UserPlanUpdate
from app.modules.plans.models import Plan
from app.shared.exceptions import ResourceNotFoundError, DuplicateResourceError, ValidationError, BadRequestError
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def create_subscription(
    db: AsyncIOMotorDatabase,
    user_id: str,
    subscription_data: UserPlanCreate
) -> dict:
    """
    Create a new subscription for a user.
    
    Args:
        db: Database connection
        user_id: User ID
        subscription_data: Subscription creation data
        
    Returns:
        dict: Created subscription
        
    Raises:
        ResourceNotFoundError: If plan not found
        DuplicateResourceError: If user already has an active subscription
    """
    # Check if plan exists
    plan = await Plan.get_plan_by_id(db, subscription_data.plan_id)
    if not plan:
        raise ResourceNotFoundError(f"Plan with ID '{subscription_data.plan_id}' not found")
    
    # Check if user already has an active subscription
    existing_subscription = await UserPlan.get_user_current_subscription(db, user_id)
    if existing_subscription:
        raise DuplicateResourceError("User already has an active subscription")
    
    # Create subscription
    payment_method_dict = subscription_data.payment_method.model_dump() if subscription_data.payment_method else None
    
    subscription = await UserPlan.create_subscription(
        db=db,
        user_id=user_id,
        plan_id=subscription_data.plan_id,
        billing_cycle=subscription_data.billing_cycle.value,
        auto_renew=subscription_data.auto_renew,
        payment_method=payment_method_dict
    )
    
    logger.info(f"Subscription created successfully: {subscription['_id']} for user {user_id}")
    return subscription


async def get_subscription_by_id(
    db: AsyncIOMotorDatabase,
    subscription_id: str,
    user_id: str
) -> dict:
    """
    Get subscription by ID.
    
    Args:
        db: Database connection
        subscription_id: Subscription ID
        user_id: User ID (for ownership verification)
        
    Returns:
        dict: Subscription data
        
    Raises:
        ResourceNotFoundError: If subscription not found or doesn't belong to user
    """
    subscription = await UserPlan.get_subscription_by_id(db, subscription_id)
    if not subscription:
        raise ResourceNotFoundError(f"Subscription with ID '{subscription_id}' not found")
    
    # Verify ownership
    if subscription["user_id"] != user_id:
        raise ResourceNotFoundError(f"Subscription with ID '{subscription_id}' not found")
    
    return subscription


async def get_current_subscription(
    db: AsyncIOMotorDatabase,
    user_id: str
) -> dict:
    """
    Get user's current active subscription.
    
    Args:
        db: Database connection
        user_id: User ID
        
    Returns:
        dict: Current subscription
        
    Raises:
        ResourceNotFoundError: If no active subscription found
    """
    subscription = await UserPlan.get_user_current_subscription(db, user_id)
    if not subscription:
        raise ResourceNotFoundError("No active subscription found")
    
    return subscription


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
    subscriptions, total = await UserPlan.list_user_subscriptions(db, user_id, limit, offset)
    
    logger.debug(f"Listed subscriptions: count={len(subscriptions)}, total={total} for user {user_id}")
    return subscriptions, total


async def update_subscription(
    db: AsyncIOMotorDatabase,
    subscription_id: str,
    user_id: str,
    subscription_data: UserPlanUpdate
) -> dict:
    """
    Update subscription.
    
    Args:
        db: Database connection
        subscription_id: Subscription ID
        user_id: User ID (for ownership verification)
        subscription_data: Subscription update data
        
    Returns:
        dict: Updated subscription
        
    Raises:
        ResourceNotFoundError: If subscription not found or doesn't belong to user
    """
    # Check if subscription exists and belongs to user
    existing_subscription = await UserPlan.get_subscription_by_id(db, subscription_id)
    if not existing_subscription:
        raise ResourceNotFoundError(f"Subscription with ID '{subscription_id}' not found")
    
    # Verify ownership
    if existing_subscription["user_id"] != user_id:
        raise ResourceNotFoundError(f"Subscription with ID '{subscription_id}' not found")
    
    # Prepare update data
    update_dict = subscription_data.model_dump(exclude_unset=True)
    
    # Convert payment_method to dict
    if "payment_method" in update_dict and subscription_data.payment_method:
        update_dict["payment_method"] = subscription_data.payment_method.model_dump()
    
    # Update subscription
    updated_subscription = await UserPlan.update_subscription(db, subscription_id, update_dict)
    if not updated_subscription:
        raise ResourceNotFoundError(f"Subscription with ID '{subscription_id}' not found")
    
    logger.info(f"Subscription updated successfully: {subscription_id}")
    return updated_subscription


async def cancel_subscription(
    db: AsyncIOMotorDatabase,
    subscription_id: str,
    user_id: str
) -> dict:
    """
    Cancel subscription.
    
    Args:
        db: Database connection
        subscription_id: Subscription ID
        user_id: User ID (for ownership verification)
        
    Returns:
        dict: Cancelled subscription
        
    Raises:
        ResourceNotFoundError: If subscription not found or doesn't belong to user
        ValidationError: If subscription is already cancelled
    """
    # Check if subscription exists and belongs to user
    subscription = await UserPlan.get_subscription_by_id(db, subscription_id)
    if not subscription:
        raise ResourceNotFoundError(f"Subscription with ID '{subscription_id}' not found")
    
    # Verify ownership
    if subscription["user_id"] != user_id:
        raise ResourceNotFoundError(f"Subscription with ID '{subscription_id}' not found")
    
    # Check if already cancelled
    if subscription["status"] == "cancelled":
        raise BadRequestError("Subscription is already cancelled")
    
    # Cancel subscription
    success = await UserPlan.cancel_subscription(db, subscription_id)
    if not success:
        raise ResourceNotFoundError(f"Subscription with ID '{subscription_id}' not found")
    
    # Get updated subscription
    updated_subscription = await UserPlan.get_subscription_by_id(db, subscription_id)
    
    logger.info(f"Subscription cancelled successfully: {subscription_id}")
    return updated_subscription


async def renew_subscription(
    db: AsyncIOMotorDatabase,
    subscription_id: str,
    user_id: str
) -> dict:
    """
    Renew subscription (extend end_date).
    
    Args:
        db: Database connection
        subscription_id: Subscription ID
        user_id: User ID (for ownership verification)
        
    Returns:
        dict: Renewed subscription
        
    Raises:
        ResourceNotFoundError: If subscription not found or doesn't belong to user
    """
    # Check if subscription exists and belongs to user
    subscription = await UserPlan.get_subscription_by_id(db, subscription_id)
    if not subscription:
        raise ResourceNotFoundError(f"Subscription with ID '{subscription_id}' not found")
    
    # Verify ownership
    if subscription["user_id"] != user_id:
        raise ResourceNotFoundError(f"Subscription with ID '{subscription_id}' not found")
    
    # Renew subscription
    renewed_subscription = await UserPlan.renew_subscription(
        db,
        subscription_id,
        subscription["billing_cycle"]
    )
    if not renewed_subscription:
        raise ResourceNotFoundError(f"Subscription with ID '{subscription_id}' not found")
    
    logger.info(f"Subscription renewed successfully: {subscription_id}")
    return renewed_subscription

