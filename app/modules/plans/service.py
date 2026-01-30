"""
Plans business logic.

Service layer for plan management operations.
"""

from typing import List
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.modules.plans.models import Plan
from app.modules.plans.schemas import PlanCreate, PlanUpdate
from app.shared.exceptions import DuplicateResourceError, ResourceNotFoundError
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def create_plan(db: AsyncIOMotorDatabase, plan_data: PlanCreate) -> dict:
    """
    Create a new plan.
    
    Args:
        db: Database connection
        plan_data: Plan creation data
        
    Returns:
        dict: Created plan
        
    Raises:
        DuplicateResourceError: If plan name already exists
    """
    # Check for duplicate name
    existing_plan = await Plan.get_plan_by_name(db, plan_data.name)
    if existing_plan:
        raise DuplicateResourceError(f"Plan with name '{plan_data.name}' already exists")
    
    # Create plan
    plan = await Plan.create_plan(
        db=db,
        name=plan_data.name,
        description=plan_data.description,
        price=plan_data.price,
        features=[f.model_dump() for f in plan_data.features],
        limits=[l.model_dump() for l in plan_data.limits]
    )
    
    logger.info(f"Plan created successfully: {plan['_id']}")
    return plan


async def get_plan_by_id(db: AsyncIOMotorDatabase, plan_id: str) -> dict:
    """
    Get plan by ID.
    
    Args:
        db: Database connection
        plan_id: Plan ID
        
    Returns:
        dict: Plan data
        
    Raises:
        ResourceNotFoundError: If plan not found
    """
    plan = await Plan.get_plan_by_id(db, plan_id)
    if not plan:
        raise ResourceNotFoundError(f"Plan with ID '{plan_id}' not found")
    
    return plan


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
    plans, total = await Plan.list_plans(db, limit, offset)
    
    logger.debug(f"Listed plans: count={len(plans)}, total={total}")
    return plans, total


async def update_plan(
    db: AsyncIOMotorDatabase,
    plan_id: str,
    plan_data: PlanUpdate
) -> dict:
    """
    Update plan.
    
    Args:
        db: Database connection
        plan_id: Plan ID
        plan_data: Plan update data
        
    Returns:
        dict: Updated plan
        
    Raises:
        ResourceNotFoundError: If plan not found
        DuplicateResourceError: If new name already exists
    """
    # Check if plan exists
    existing_plan = await Plan.get_plan_by_id(db, plan_id)
    if not existing_plan:
        raise ResourceNotFoundError(f"Plan with ID '{plan_id}' not found")
    
    # Check for duplicate name if updating name
    if plan_data.name and plan_data.name != existing_plan["name"]:
        name_exists = await Plan.get_plan_by_name(db, plan_data.name)
        if name_exists:
            raise DuplicateResourceError(f"Plan with name '{plan_data.name}' already exists")
    
    # Prepare update data
    update_dict = plan_data.model_dump(exclude_unset=True)
    
    # Convert nested models to dicts
    if "features" in update_dict:
        update_dict["features"] = [f.model_dump() for f in plan_data.features]
    if "limits" in update_dict:
        update_dict["limits"] = [l.model_dump() for l in plan_data.limits]
    
    # Update plan
    updated_plan = await Plan.update_plan(db, plan_id, update_dict)
    if not updated_plan:
        raise ResourceNotFoundError(f"Plan with ID '{plan_id}' not found")
    
    logger.info(f"Plan updated successfully: {plan_id}")
    return updated_plan


async def delete_plan(db: AsyncIOMotorDatabase, plan_id: str) -> dict:
    """
    Soft delete plan.
    
    Args:
        db: Database connection
        plan_id: Plan ID
        
    Returns:
        dict: Deleted plan confirmation
        
    Raises:
        ResourceNotFoundError: If plan not found
    """
    # Check if plan exists
    plan = await Plan.get_plan_by_id(db, plan_id)
    if not plan:
        raise ResourceNotFoundError(f"Plan with ID '{plan_id}' not found")
    
    # Soft delete
    success = await Plan.delete_plan(db, plan_id)
    if not success:
        raise ResourceNotFoundError(f"Plan with ID '{plan_id}' not found")
    
    logger.info(f"Plan deleted successfully: {plan_id}")
    return {"message": "Plan deleted successfully", "plan_id": plan_id}

