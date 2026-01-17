"""
Flow Service

Business logic for flow management and execution.

Author: Moniqo Team
Last Updated: 2026-01-17
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.flows.models import (
    Flow,
    Execution,
    ExecutionStep,
    ExecutionResult,
    AgentDecision,
    FlowStatus,
    ExecutionStatus,
    StepStatus,
    StepName,
    create_standard_steps,
)
from app.modules.flows.schemas import FlowCreate, FlowUpdate
from app.integrations.market_data import get_binance_client
from app.services.indicators import calculate_all_indicators
from app.modules.ai_agents.market_analyst_agent import MarketAnalystAgent
from app.modules.ai_agents.risk_manager_agent import RiskManagerAgent
from app.utils.logger import get_logger

logger = get_logger(__name__)


# Collection names
FLOWS_COLLECTION = "flows"
EXECUTIONS_COLLECTION = "executions"
AGENT_DECISIONS_COLLECTION = "agent_decisions"


# ==================== FLOW CRUD ====================

async def create_flow(db: AsyncIOMotorDatabase, flow_data: FlowCreate) -> Flow:
    """Create a new flow"""
    flow = Flow(
        name=flow_data.name,
        symbol=flow_data.symbol,
        mode=flow_data.mode,
        trigger=flow_data.trigger,
        agents=flow_data.agents,
        schedule=flow_data.schedule,
        config=flow_data.config or {},
    )
    
    flow_dict = flow.model_dump(by_alias=True, exclude={"id"})
    
    result = await db[FLOWS_COLLECTION].insert_one(flow_dict)
    flow.id = str(result.inserted_id)
    
    logger.info(f"Created flow: {flow.id} - {flow.name}")
    return flow


async def get_flow_by_id(db: AsyncIOMotorDatabase, flow_id: str) -> Optional[Flow]:
    """Get flow by ID"""
    try:
        doc = await db[FLOWS_COLLECTION].find_one({"_id": ObjectId(flow_id)})
        if doc:
            doc["_id"] = str(doc["_id"])
            return Flow(**doc)
        return None
    except Exception as e:
        logger.error(f"Error fetching flow {flow_id}: {str(e)}")
        return None


async def get_flows(
    db: AsyncIOMotorDatabase,
    limit: int = 10,
    offset: int = 0,
    status: Optional[FlowStatus] = None,
) -> Tuple[List[Flow], int]:
    """Get flows with pagination"""
    query = {}
    if status:
        query["status"] = status.value
    
    total = await db[FLOWS_COLLECTION].count_documents(query)
    
    cursor = db[FLOWS_COLLECTION].find(query).skip(offset).limit(limit).sort("created_at", -1)
    
    flows = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        flows.append(Flow(**doc))
    
    return flows, total


async def update_flow(
    db: AsyncIOMotorDatabase,
    flow_id: str,
    updates: FlowUpdate,
) -> Optional[Flow]:
    """Update flow"""
    update_data = updates.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    result = await db[FLOWS_COLLECTION].update_one(
        {"_id": ObjectId(flow_id)},
        {"$set": update_data}
    )
    
    if result.modified_count > 0:
        return await get_flow_by_id(db, flow_id)
    return None


async def delete_flow(db: AsyncIOMotorDatabase, flow_id: str) -> bool:
    """Delete flow"""
    result = await db[FLOWS_COLLECTION].delete_one({"_id": ObjectId(flow_id)})
    return result.deleted_count > 0


# ==================== EXECUTION MANAGEMENT ====================

async def create_execution(
    db: AsyncIOMotorDatabase,
    flow: Flow,
) -> Execution:
    """Create a new execution for a flow"""
    # Use standard steps: data_fetch, market_analysis, risk_validation, decision
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


# ==================== FLOW EXECUTION ====================

async def execute_flow(
    db: AsyncIOMotorDatabase,
    flow: Flow,
    model_provider: str = "groq",
    model_name: Optional[str] = None,
) -> Execution:
    """
    Execute a trading flow.
    
    This orchestrates:
    1. Fetch market data
    2. Calculate indicators
    3. Run MarketAnalystAgent
    4. Run RiskManagerAgent
    5. Make final decision
    """
    # Create execution record
    execution = await create_execution(db, flow)
    
    # Step indices
    STEP_DATA_FETCH = 0
    STEP_MARKET_ANALYSIS = 1
    STEP_RISK_VALIDATION = 2
    STEP_DECISION = 3
    
    try:
        # Mark execution as running + start data fetch step
        await update_execution(db, execution.id, {
            "status": ExecutionStatus.RUNNING.value,
            f"steps.{STEP_DATA_FETCH}.status": StepStatus.RUNNING.value,
            f"steps.{STEP_DATA_FETCH}.started_at": datetime.now(timezone.utc),
        })
        
        # Step 0: Fetch market data
        binance = get_binance_client()
        candles = await binance.get_klines(flow.symbol, "1h", 100)
        ticker = await binance.get_24h_ticker(flow.symbol)
        
        if not candles or not ticker:
            raise Exception(f"Failed to fetch market data for {flow.symbol}")
        
        # Extract price data
        closes = [float(c.close) for c in candles]
        highs = [float(c.high) for c in candles]
        lows = [float(c.low) for c in candles]
        
        # Calculate indicators
        indicators = calculate_all_indicators(closes, highs, lows)
        
        # Save market data context
        market_context = {
            "symbol": flow.symbol,
            "current_price": float(ticker.price),
            "high_24h": float(ticker.high_24h),
            "low_24h": float(ticker.low_24h),
            "change_24h_percent": float(ticker.change_percent_24h),
            "volume_24h": float(ticker.volume_24h),
        }
        
        await update_execution(db, execution.id, {
            "market_data": market_context,
            "indicators": indicators,
            f"steps.{STEP_DATA_FETCH}.status": StepStatus.COMPLETED.value,
            f"steps.{STEP_DATA_FETCH}.completed_at": datetime.now(timezone.utc),
            f"steps.{STEP_DATA_FETCH}.data": {"candles_count": len(candles)},
        })
        
        # Step 1: Market Analysis
        await update_execution(db, execution.id, {
            f"steps.{STEP_MARKET_ANALYSIS}.status": StepStatus.RUNNING.value,
            f"steps.{STEP_MARKET_ANALYSIS}.started_at": datetime.now(timezone.utc),
        })
        
        # Run Market Analyst
        market_analyst = MarketAnalystAgent(
            model_provider=model_provider,
            model_name=model_name,
        )
        
        analysis_context = {
            "symbol": flow.symbol,
            "market_data": market_context,
            "indicators": indicators,
        }
        
        analysis_result = await market_analyst.process(analysis_context)
        analysis_action = analysis_result.get("action") or "hold"
        analysis_confidence = analysis_result.get("confidence") or 0
        analysis_reasoning = analysis_result.get("reasoning") or "No market analysis reasoning returned."
        
        # Save market analyst decision
        analyst_decision = AgentDecision(
            execution_id=execution.id,
            agent_role="market_analyst",
            action=analysis_action,
            confidence=analysis_confidence,
            reasoning=analysis_reasoning,
            data=analysis_result,
        )
        await save_agent_decision(db, analyst_decision)
        
        await update_execution(db, execution.id, {
            f"steps.{STEP_MARKET_ANALYSIS}.status": StepStatus.COMPLETED.value,
            f"steps.{STEP_MARKET_ANALYSIS}.completed_at": datetime.now(timezone.utc),
            f"steps.{STEP_MARKET_ANALYSIS}.data": analysis_result,
        })
        
        # Step 2: Risk Validation
        await update_execution(db, execution.id, {
            f"steps.{STEP_RISK_VALIDATION}.status": StepStatus.RUNNING.value,
            f"steps.{STEP_RISK_VALIDATION}.started_at": datetime.now(timezone.utc),
        })
        
        # Run Risk Manager
        risk_manager = RiskManagerAgent(
            model_provider=model_provider,
            model_name=model_name,
        )
        
        risk_context = {
            "symbol": flow.symbol,
            "proposed_action": analysis_result.get("action", "hold"),
            "confidence": analysis_result.get("confidence", 0),
            "market_data": market_context,
            "indicators": indicators,
            "reasoning": analysis_result.get("reasoning", ""),
        }
        
        risk_result = await risk_manager.process(risk_context)
        risk_action = risk_result.get("action") or "reject"
        risk_confidence = risk_result.get("confidence") or 0
        risk_reasoning = risk_result.get("reasoning") or "Risk validation rejected the trade."
        
        # Save risk manager decision
        risk_decision = AgentDecision(
            execution_id=execution.id,
            agent_role="risk_manager",
            action=risk_action,
            confidence=risk_confidence,
            reasoning=risk_reasoning,
            data=risk_result,
        )
        await save_agent_decision(db, risk_decision)
        
        # Determine final action
        final_action = "hold"
        final_confidence = 0.0
        final_reasoning = ""
        
        if risk_action == "approve":
            final_action = analysis_action
            final_confidence = analysis_confidence * risk_confidence
            final_reasoning = f"Market Analysis: {analysis_reasoning}. Risk Assessment: {risk_reasoning}"
        else:
            final_action = "hold"
            final_confidence = risk_confidence
            final_reasoning = f"Trade rejected by Risk Manager: {risk_reasoning}"
        
        # Complete execution
        completed_at = datetime.now(timezone.utc)
        duration = int((completed_at - execution.started_at).total_seconds() * 1000)
        
        result = ExecutionResult(
            action=final_action,
            confidence=final_confidence,
            reasoning=final_reasoning,
        )
        
        # Complete risk validation step
        await update_execution(db, execution.id, {
            f"steps.{STEP_RISK_VALIDATION}.status": StepStatus.COMPLETED.value,
            f"steps.{STEP_RISK_VALIDATION}.completed_at": datetime.now(timezone.utc),
            f"steps.{STEP_RISK_VALIDATION}.data": risk_result,
        })
        
        # Complete decision step
        await update_execution(db, execution.id, {
            f"steps.{STEP_DECISION}.status": StepStatus.RUNNING.value,
            f"steps.{STEP_DECISION}.started_at": datetime.now(timezone.utc),
        })
        
        await update_execution(db, execution.id, {
            "status": ExecutionStatus.COMPLETED.value,
            "completed_at": completed_at,
            "duration": duration,
            f"steps.{STEP_DECISION}.status": StepStatus.COMPLETED.value,
            f"steps.{STEP_DECISION}.completed_at": completed_at,
            f"steps.{STEP_DECISION}.data": {"final_action": final_action, "confidence": final_confidence},
            "result": result.model_dump(),
        })
        
        # Update flow statistics
        await db[FLOWS_COLLECTION].update_one(
            {"_id": ObjectId(flow.id)},
            {
                "$inc": {
                    "total_executions": 1,
                    "successful_executions": 1,
                },
                "$set": {
                    "last_run_at": completed_at,
                    "updated_at": completed_at,
                },
            }
        )
        
        # Return updated execution
        return await get_execution_by_id(db, execution.id)
        
    except Exception as e:
        logger.error(f"Flow execution failed: {str(e)}")
        
        failed_at = datetime.now(timezone.utc)
        
        # Mark execution as failed - mark all pending steps as failed
        await update_execution(db, execution.id, {
            "status": ExecutionStatus.FAILED.value,
            "completed_at": failed_at,
        })
        
        # Update any running/pending steps to failed
        for step_idx in [STEP_DATA_FETCH, STEP_MARKET_ANALYSIS, STEP_RISK_VALIDATION, STEP_DECISION]:
            await db[EXECUTIONS_COLLECTION].update_one(
                {
                    "_id": ObjectId(execution.id),
                    f"steps.{step_idx}.status": {"$in": [StepStatus.PENDING.value, StepStatus.RUNNING.value]}
                },
                {
                    "$set": {
                        f"steps.{step_idx}.status": StepStatus.FAILED.value,
                        f"steps.{step_idx}.completed_at": failed_at,
                        f"steps.{step_idx}.error": str(e),
                    }
                }
            )
        
        # Update flow statistics
        await db[FLOWS_COLLECTION].update_one(
            {"_id": ObjectId(flow.id)},
            {
                "$inc": {"total_executions": 1},
                "$set": {
                    "last_run_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                },
            }
        )
        
        raise
