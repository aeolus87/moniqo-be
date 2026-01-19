"""
Risk Rules Service

Business logic for risk rule management.

Author: Moniqo Team
Last Updated: 2026-01-17
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.risk_rules.models import RiskRule
from app.modules.risk_rules.schemas import RiskRuleCreate, RiskRuleUpdate
from app.utils.logger import get_logger

logger = get_logger(__name__)

RISK_RULES_COLLECTION = "risk_rules"


async def create_risk_rule(db: AsyncIOMotorDatabase, data: RiskRuleCreate) -> RiskRule:
    """Create a new risk rule"""
    rule = RiskRule(
        name=data.name,
        description=data.description,
        user_id=data.user_id,
        wallet_id=data.wallet_id,
        limits=data.limits,
        is_active=data.is_active,
    )
    rule_dict = rule.model_dump(by_alias=True, exclude={"id"})
    result = await db[RISK_RULES_COLLECTION].insert_one(rule_dict)
    rule.id = str(result.inserted_id)
    return rule


async def get_risk_rule_by_id(
    db: AsyncIOMotorDatabase,
    rule_id: str,
) -> Optional[RiskRule]:
    """Get risk rule by ID"""
    try:
        doc = await db[RISK_RULES_COLLECTION].find_one({"_id": ObjectId(rule_id)})
        if doc:
            doc["_id"] = str(doc["_id"])
            return RiskRule(**doc)
        return None
    except Exception as e:
        logger.error(f"Error fetching risk rule {rule_id}: {str(e)}")
        return None


async def get_risk_rules(
    db: AsyncIOMotorDatabase,
    limit: int = 10,
    offset: int = 0,
    user_id: Optional[str] = None,
    wallet_id: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> Tuple[List[RiskRule], int]:
    """List risk rules with filters and pagination"""
    query: Dict[str, Any] = {}
    if user_id:
        query["user_id"] = user_id
    if wallet_id:
        query["wallet_id"] = wallet_id
    if is_active is not None:
        query["is_active"] = is_active

    total = await db[RISK_RULES_COLLECTION].count_documents(query)
    cursor = db[RISK_RULES_COLLECTION].find(query).skip(offset).limit(limit).sort("created_at", -1)

    rules: List[RiskRule] = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        rules.append(RiskRule(**doc))

    return rules, total


async def update_risk_rule(
    db: AsyncIOMotorDatabase,
    rule_id: str,
    updates: RiskRuleUpdate,
) -> Optional[RiskRule]:
    """Update a risk rule"""
    update_data = updates.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.now(timezone.utc)
    result = await db[RISK_RULES_COLLECTION].update_one(
        {"_id": ObjectId(rule_id)},
        {"$set": update_data}
    )
    if result.modified_count > 0:
        return await get_risk_rule_by_id(db, rule_id)
    return None


async def delete_risk_rule(
    db: AsyncIOMotorDatabase,
    rule_id: str,
) -> bool:
    """Delete a risk rule"""
    result = await db[RISK_RULES_COLLECTION].delete_one({"_id": ObjectId(rule_id)})
    return result.deleted_count > 0
