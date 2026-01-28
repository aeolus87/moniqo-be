"""
Execution Service

Business logic for execution management.

Author: Moniqo Team
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.flows.models import (
    Flow,
    Execution,
    AgentDecision,
    ExecutionStatus,
    create_standard_steps,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Collection names
EXECUTIONS_COLLECTION = "executions"
AGENT_DECISIONS_COLLECTION = "agent_decisions"


async def create_execution(
    db: AsyncIOMotorDatabase,
    flow: Flow,
) -> Execution:
    """Create a new execution for a flow"""
    steps = create_standard_steps()
    
    execution = Execution(
        flow_id=str(flow.id),
        flow_name=flow.name,
        status=ExecutionStatus.PENDING,
        steps=steps,
    )
    
    exec_dict = execution.model_dump(by_alias=True, exclude={"id"})
    
    result = await db[EXECUTIONS_COLLECTION].insert_one(exec_dict)
    execution.id = str(result.inserted_id)
    
    logger.info(f"Created execution: {execution.id} for flow {flow.id}")
    return execution


async def get_execution_by_id(
    db: AsyncIOMotorDatabase,
    execution_id: str,
) -> Optional[Execution]:
    """Get execution by ID"""
    try:
        doc = await db[EXECUTIONS_COLLECTION].find_one({"_id": ObjectId(execution_id)})
        if doc:
            doc["_id"] = str(doc["_id"])
            return Execution(**doc)
        return None
    except Exception as e:
        logger.error(f"Error fetching execution {execution_id}: {str(e)}")
        return None


async def get_executions(
    db: AsyncIOMotorDatabase,
    flow_id: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
) -> Tuple[List[Execution], int]:
    """Get executions with pagination"""
    query = {}
    if flow_id:
        query["flow_id"] = flow_id
    
    total = await db[EXECUTIONS_COLLECTION].count_documents(query)
    
    cursor = db[EXECUTIONS_COLLECTION].find(query).skip(offset).limit(limit).sort("started_at", -1)
    
    executions = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        executions.append(Execution(**doc))
    
    return executions, total


async def update_execution(
    db: AsyncIOMotorDatabase,
    execution_id: str,
    updates: Dict[str, Any],
) -> Optional[Execution]:
    """Update execution"""
    result = await db[EXECUTIONS_COLLECTION].update_one(
        {"_id": ObjectId(execution_id)},
        {"$set": updates}
    )
    
    if result.modified_count > 0:
        return await get_execution_by_id(db, execution_id)
    return None


async def save_agent_decision(
    db: AsyncIOMotorDatabase,
    decision: AgentDecision,
) -> str:
    """Save agent decision to database"""
    decision_dict = decision.model_dump(by_alias=True, exclude={"id"})
    result = await db[AGENT_DECISIONS_COLLECTION].insert_one(decision_dict)
    return str(result.inserted_id)


async def get_agent_decisions(
    db: AsyncIOMotorDatabase,
    execution_id: Optional[str] = None,
    limit: int = 50,
) -> List[AgentDecision]:
    """Get agent decisions"""
    query = {}
    if execution_id:
        query["execution_id"] = execution_id
    
    cursor = db[AGENT_DECISIONS_COLLECTION].find(query).limit(limit).sort("timestamp", -1)
    
    decisions = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        decisions.append(AgentDecision(**doc))
    
    return decisions


async def delete_execution(
    db: AsyncIOMotorDatabase,
    execution_id: str,
) -> bool:
    """Delete a single execution and its agent decisions"""
    await db[AGENT_DECISIONS_COLLECTION].delete_many({"execution_id": execution_id})
    result = await db[EXECUTIONS_COLLECTION].delete_one({"_id": ObjectId(execution_id)})
    return result.deleted_count > 0


async def delete_all_executions(
    db: AsyncIOMotorDatabase,
) -> int:
    """Delete all executions and related agent decisions"""
    await db[AGENT_DECISIONS_COLLECTION].delete_many({})
    result = await db[EXECUTIONS_COLLECTION].delete_many({})
    return result.deleted_count
