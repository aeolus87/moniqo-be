"""
Flow Service

Business logic for flow management and execution.
Refactored to use modular services for better maintainability.

Author: Moniqo Team
Last Updated: 2026-01-28
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
import asyncio
import time
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.flows.models import (
    Flow,
    Execution,
    ExecutionStep,
    ExecutionResult,
    AgentDecision,
    FlowStatus,
    FlowMode,
    ExecutionStatus,
    StepStatus,
    StepName,
    create_standard_steps,
)
from app.modules.positions.models import PositionStatus, PositionSide
from app.modules.flows.schemas import FlowCreate, FlowUpdate
from app.integrations.market_data import get_binance_client
from app.integrations.wallets.base import OrderSide, OrderType, TimeInForce, OrderStatus
from app.integrations.wallets.factory import create_wallet_from_db
from app.services.indicators import calculate_all_indicators
from app.services.risk_rules import evaluate_risk_limits
from app.services.signal_aggregator import get_signal_aggregator
from app.modules.ai_agents.market_analyst_agent import MarketAnalystAgent
from app.modules.ai_agents.risk_manager_agent import RiskManagerAgent
from app.modules.risk_rules import service as risk_rule_service
from app.utils.logger import get_logger

# Import from refactored service modules
from app.modules.flows.utils import (
    to_object_id as _to_object_id,
    to_serializable as _to_serializable,
    to_response_payload as _to_response_payload,
    get_or_create_demo_user as _get_or_create_demo_user,
    resolve_order_quantity as _resolve_order_quantity,
    resolve_demo_force_action as _resolve_demo_force_action,
)
# Note: execution_service.py contains equivalent functions but we keep local
# implementations here to maintain backward compatibility with existing imports
from app.modules.flows.execution_lock import (
    acquire_execution_lock,
    heartbeat_execution_lock,
    release_execution_lock,
    recover_stuck_executions,
)
from app.modules.flows.data_aggregator import (
    get_cached_sentiment as _get_cached_sentiment,
    set_cached_sentiment as _set_cached_sentiment,
)
from app.modules.flows.swarm_coordinator import (
    usage_delta as _usage_delta,
    aggregate_usage as _aggregate_usage,
    aggregate_swarm_results as _aggregate_swarm_results,
)
from app.modules.flows.statistics import update_flow_statistics as _update_flow_statistics
from app.modules.flows.orchestrator import (
    emit_execution_update as _emit_execution_update,
    get_auto_loop_settings as _get_auto_loop_settings,
)
from app.modules.flows.trade_executor import (
    place_order_with_retry as _place_order_with_retry,
)

logger = get_logger(__name__)


# _emit_execution_update is imported from orchestrator.py


# Collection names
FLOWS_COLLECTION = "flows"
EXECUTIONS_COLLECTION = "executions"
AGENT_DECISIONS_COLLECTION = "agent_decisions"
AI_DECISIONS_LOG_COLLECTION = "ai_decisions_log"
ORDERS_COLLECTION = "orders"
POSITIONS_COLLECTION = "positions"
AI_CONVERSATIONS_COLLECTION = "ai_conversations"
LEARNING_OUTCOMES_COLLECTION = "learning_outcomes"


# Sentiment cache functions imported from data_aggregator.py


# _get_or_create_demo_user imported from utils.py


# _usage_delta and _aggregate_usage imported from swarm_coordinator.py


# _update_flow_statistics imported from statistics.py


# _aggregate_swarm_results imported from swarm_coordinator.py


# Utility functions imported from utils.py:
# _resolve_order_quantity, _resolve_demo_force_action
# _to_object_id, _to_serializable, _to_response_payload

# Auto-loop and scheduling functions imported from orchestrator.py:
# _get_auto_loop_settings, _schedule_auto_loop

# NOTE: The _schedule_auto_loop function in orchestrator.py references
# get_flow_by_id and execute_flow from this module, so we keep the definition
# here to avoid circular imports. The orchestrator.py version is a simplified
# facade that delegates to this module.

async def _schedule_auto_loop_impl(
    db: AsyncIOMotorDatabase,
    flow: Flow,
    model_provider: str,
    model_name: Optional[str],
) -> None:
    """
    Schedule the next iteration of the continuous trading loop.
    
    Internal implementation - use _schedule_auto_loop from orchestrator for external calls.
    """
    enabled, delay_seconds, max_cycles = _get_auto_loop_settings(flow)
    if not enabled:
        logger.info(f"Auto-loop disabled for flow {flow.id}")
        return
    cycle_count = int((flow.config or {}).get("auto_loop_cycle_count", 0)) + 1
    if max_cycles is not None and cycle_count >= max_cycles:
        logger.info(f"Flow {flow.id} reached max cycles ({max_cycles}), stopping auto-loop")
        await db[FLOWS_COLLECTION].update_one(
            {"_id": ObjectId(flow.id)},
            {"$set": {"config.auto_loop_cycle_count": cycle_count}},
        )
        return
    await db[FLOWS_COLLECTION].update_one(
        {"_id": ObjectId(flow.id)},
        {"$set": {"config.auto_loop_cycle_count": cycle_count}},
    )

    async def _delayed_run() -> None:
        """Execute the next cycle with robust error handling."""
        await asyncio.sleep(delay_seconds)
        
        try:
            refreshed = await get_flow_by_id(db, flow.id)
            if not refreshed:
                logger.warning(f"Flow {flow.id} not found, stopping auto-loop")
                return
            if refreshed.status != FlowStatus.ACTIVE:
                logger.info(f"Flow {flow.id} is not active (status: {refreshed.status}), stopping auto-loop")
                return
            
            await execute_flow(db, refreshed, model_provider, model_name)
        except Exception as e:
            logger.error(f"Auto-loop execution failed for flow {flow.id}: {e}")
            
            try:
                refreshed = await get_flow_by_id(db, flow.id)
                if refreshed and refreshed.status == FlowStatus.ACTIVE:
                    logger.info(f"Scheduling retry for flow {flow.id} after error")
                    await _schedule_auto_loop_impl(db, refreshed, model_provider, model_name)
            except Exception as retry_error:
                logger.error(f"Failed to schedule retry for flow {flow.id}: {retry_error}")

    try:
        from celery import current_task
        if current_task and current_task.request is not None:
            from app.tasks.flow_tasks import execute_flow_task

            execute_flow_task.apply_async(
                args=[str(flow.id), model_provider, model_name],
                countdown=delay_seconds,
            )
            return
    except Exception:
        pass

    asyncio.create_task(_delayed_run())


# _place_order_with_retry imported from trade_executor.py


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


async def start_flow(
    db: AsyncIOMotorDatabase,
    flow_id: str,
    model_provider: str = "groq",
    model_name: Optional[str] = None,
) -> Optional[Flow]:
    """
    Start continuous trading flow.
    
    Sets flow status to ACTIVE, resets cycle count, and triggers first execution.
    The flow will continue looping until manually stopped via stop_flow().
    
    Args:
        db: Database instance
        flow_id: Flow ID to start
        model_provider: AI model provider (default: groq)
        model_name: Specific model name (optional)
        
    Returns:
        Updated Flow instance
    """
    flow = await get_flow_by_id(db, flow_id)
    if not flow:
        return None
    
    # Set flow to ACTIVE and reset cycle count
    now = datetime.now(timezone.utc)
    await db[FLOWS_COLLECTION].update_one(
        {"_id": ObjectId(flow_id)},
        {
            "$set": {
                "status": FlowStatus.ACTIVE.value,
                "config.auto_loop_cycle_count": 0,
                "config.auto_loop_enabled": True,
                "updated_at": now,
            }
        }
    )
    
    # Refresh flow
    flow = await get_flow_by_id(db, flow_id)
    
    logger.info(f"Starting continuous trading flow: {flow_id} - {flow.name}")
    
    # Trigger first execution cycle
    try:
        await execute_flow(db, flow, model_provider, model_name)
    except Exception as e:
        logger.error(f"Failed to start first execution for flow {flow_id}: {e}")
        # Schedule retry even on failure
        await _schedule_auto_loop(db, flow, model_provider, model_name)
    
    return flow


async def stop_flow(db: AsyncIOMotorDatabase, flow_id: str) -> Optional[Flow]:
    """
    Stop continuous trading flow.
    
    Sets flow status to PAUSED, which breaks the auto-loop.
    The flow can be restarted via start_flow().
    
    Args:
        db: Database instance
        flow_id: Flow ID to stop
        
    Returns:
        Updated Flow instance
    """
    flow = await get_flow_by_id(db, flow_id)
    if not flow:
        return None
    
    now = datetime.now(timezone.utc)
    await db[FLOWS_COLLECTION].update_one(
        {"_id": ObjectId(flow_id)},
        {
            "$set": {
                "status": FlowStatus.PAUSED.value,
                "updated_at": now,
            }
        }
    )
    
    logger.info(f"Stopped continuous trading flow: {flow_id} - {flow.name}")
    
    return await get_flow_by_id(db, flow_id)


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


# ==================== EXECUTION LOCK MANAGEMENT ====================
# Lock management functions imported from execution_lock.py:
# acquire_execution_lock, heartbeat_execution_lock, release_execution_lock, recover_stuck_executions


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
    # EXECUTION SAFEGUARD #1: Atomic Lock Acquisition

    # Create execution record first (needed for execution_id in lock)
    execution = await create_execution(db, flow)
    
    # Atomically acquire lock - only succeeds if lock doesn't exist OR is expired
    lock_acquired = await acquire_execution_lock(db, flow.id, str(execution.id))
    
    if not lock_acquired:
        # Lock acquisition failed - another execution is running
        logger.warning(f"Flow {flow.id} is locked by another execution - rejecting duplicate trigger")
        await update_execution(db, execution.id, {
            "status": ExecutionStatus.FAILED.value,
            "completed_at": datetime.now(timezone.utc),
            "duration": 0,
            "error": "Execution rejected: Another execution is already running for this flow (idempotency safeguard)"
        })
        return execution
    
    logger.info(f"Acquired execution lock for flow {flow.id} (execution {execution.id})")

    # Set to RUNNING status
    await update_execution(db, execution.id, {
        "status": ExecutionStatus.RUNNING.value,
        "started_at": datetime.now(timezone.utc)
    })

    logger.info(f"Idempotency check passed - execution {execution.id} is now running for flow {flow.id}")
    execution_config = flow.config or {}
    # Default to True - bypass gates to ensure AI decisions result in actual trades
    demo_force_position = bool(execution_config.get("demo_force_position", True))
    
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
        user_id = str((flow.config or {}).get("user_id") or (execution_config or {}).get("user_id"))
        await _emit_execution_update(
            execution.id, flow.id, "RUNNING", STEP_DATA_FETCH,
            "Fetching Market & Sentiment Data", 10, "Loading market data and sentiment analysis...", user_id
        )
        
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
        
        # Fetch aggregated sentiment signal (social + prediction markets)
        signal_data = None
        try:
            base_symbol = flow.symbol.split("/")[0] if "/" in flow.symbol else flow.symbol
            aggregator = get_signal_aggregator()
            signal = await aggregator.get_signal(base_symbol.upper())
            signal_data = signal.to_dict()
        except Exception as e:
            logger.error(f"Failed to fetch sentiment signal for {flow.symbol}: {e}")
        
        if signal_data:
            market_context["signal"] = signal_data
        
        # Fetch Polymarket odds for BTC Price Up markets (with 15-min cache)
        polymarket_data = None
        try:
            from app.integrations.market_data.polymarket_client import get_polymarket_client
            base_symbol = flow.symbol.split("/")[0] if "/" in flow.symbol else flow.symbol
            if base_symbol.upper() == "BTC":
                # Check cache first
                cache_key_1h = f"polymarket:btc:1h"
                cache_key_15m = f"polymarket:btc:15m"
                
                polymarket_data = _get_cached_sentiment(cache_key_1h)
                if polymarket_data is None:
                    polymarket_client = get_polymarket_client()
                    # Try 1h timeframe first
                    polymarket_data = await polymarket_client.get_btc_price_up_odds("1h")
                    if polymarket_data:
                        _set_cached_sentiment(cache_key_1h, polymarket_data)
                        logger.info(f"Polymarket 1h data fetched and cached for {flow.symbol}")
                
                # Fallback to 15m if 1h not found
                if polymarket_data is None:
                    polymarket_data = _get_cached_sentiment(cache_key_15m)
                    if polymarket_data is None:
                        polymarket_client = get_polymarket_client()
                        polymarket_data = await polymarket_client.get_btc_price_up_odds("15m")
                        if polymarket_data:
                            _set_cached_sentiment(cache_key_15m, polymarket_data)
                            logger.info(f"Polymarket 15m data fetched and cached for {flow.symbol}")
        except Exception as e:
            logger.error(f"Failed to fetch Polymarket data for {flow.symbol}: {e}")
        
        if polymarket_data:
            market_context["polymarket_odds"] = polymarket_data
        
        # Fetch Reddit sentiment for symbol (with 15-min cache)
        reddit_sentiment = None
        try:
            from app.integrations.market_data.reddit_client import get_reddit_client
            base_symbol = flow.symbol.split("/")[0] if "/" in flow.symbol else flow.symbol
            cache_key = f"reddit:{base_symbol.upper()}"
            
            # Check cache first
            reddit_sentiment = _get_cached_sentiment(cache_key)
            if reddit_sentiment is None:
                reddit_client = get_reddit_client()
                reddit_sentiment = await reddit_client.get_symbol_sentiment(base_symbol.upper(), limit=10)
                if reddit_sentiment:
                    _set_cached_sentiment(cache_key, reddit_sentiment)
                    logger.info(f"Reddit sentiment fetched and cached for {base_symbol.upper()}")
        except Exception as e:
            logger.error(f"Failed to fetch Reddit sentiment for {flow.symbol}: {e}")
        
        if reddit_sentiment:
            market_context["reddit_sentiment"] = reddit_sentiment
        
        await update_execution(db, execution.id, {
            "market_data": market_context,
            "indicators": indicators,
            f"steps.{STEP_DATA_FETCH}.status": StepStatus.COMPLETED.value,
            f"steps.{STEP_DATA_FETCH}.completed_at": datetime.now(timezone.utc),
            f"steps.{STEP_DATA_FETCH}.data": {"candles_count": len(candles)},
        })
        await _emit_execution_update(
            execution.id, flow.id, "RUNNING", STEP_MARKET_ANALYSIS,
            "AI Swarm Analyzing", 30, "Running market analysis with AI agents...", user_id
        )
        
        # Heartbeat: Update lock expiration after data fetch
        await heartbeat_execution_lock(db, flow.id, str(execution.id))
        
        # Step 1: Market Analysis
        await update_execution(db, execution.id, {
            f"steps.{STEP_MARKET_ANALYSIS}.status": StepStatus.RUNNING.value,
            f"steps.{STEP_MARKET_ANALYSIS}.started_at": datetime.now(timezone.utc),
        })
        
        analysis_context = {
            "symbol": flow.symbol,
            "market_data": market_context,
            "indicators": indicators,
        }

        if flow.mode == FlowMode.SWARM:
            swarm_config = flow.config or {}
            swarm_runs = int(swarm_config.get("swarm_runs", max(3, len(flow.agents))))
            swarm_min_agreement = int(swarm_config.get("swarm_min_agreement", 50))
            role_weights = swarm_config.get("swarm_role_weights", {"market_analyst": 1.0})

            async def run_swarm_member() -> Dict[str, Any]:
                agent = MarketAnalystAgent(
                    model_provider=model_provider,
                    model_name=model_name,
                )
                before = agent.model.get_model_info()
                start = time.perf_counter()
                result = await agent.process(analysis_context)
                duration_ms = int((time.perf_counter() - start) * 1000)
                after = agent.model.get_model_info()
                usage = _usage_delta(before, after)
                return {
                    "result": result,
                    "role": "market_analyst",
                    "usage": usage,
                    "duration_ms": duration_ms,
                }

            swarm_results = await asyncio.gather(*[run_swarm_member() for _ in range(swarm_runs)])
            swarm_usage = _aggregate_usage([r["usage"] for r in swarm_results])
            swarm_aggregate = _aggregate_swarm_results(
                [
                    {**r["result"], "role": r["role"]}
                    for r in swarm_results
                ],
                role_weights=role_weights,
            )
            if swarm_aggregate["agreement"] < swarm_min_agreement:
                swarm_aggregate["action"] = "hold"
                swarm_aggregate["reasoning"] = (
                    f"Swarm agreement {swarm_aggregate['agreement']}% below "
                    f"minimum {swarm_min_agreement}%."
                )
            analysis_result = {
                "success": True,
                "agent": "market_analyst_swarm",
                "timestamp": datetime.now(timezone.utc),
                "action": swarm_aggregate["action"],
                "confidence": swarm_aggregate["confidence"],
                "reasoning": swarm_aggregate["reasoning"],
                "swarm": {
                    "runs": swarm_runs,
                    "members": swarm_aggregate["members"],
                    "votes": swarm_aggregate["votes"],
                    "agreement": swarm_aggregate["agreement"],
                    "is_unanimous": swarm_aggregate["is_unanimous"],
                    "min_agreement": swarm_min_agreement,
                },
            }
            analyst_duration_ms = int(sum(r["duration_ms"] for r in swarm_results) / swarm_runs)
            analyst_usage = swarm_usage
            await db[AI_CONVERSATIONS_COLLECTION].insert_one({
                "user_id": (flow.config or {}).get("user_id"),
                "execution_id": str(execution.id),
                "flow_id": str(execution.flow_id),
                "context": {
                    "symbol": flow.symbol,
                    "action": "voting",
                    "phase": StepName.MARKET_ANALYSIS.value,
                },
                "messages": [
                    {
                        "agent_name": f"market_analyst_{idx + 1}",
                        "agent_role": "market_analyst",
                        "ai_model": analyst_usage.get("model_name"),
                        "message_type": "vote",
                        "content": {
                            "text": result["result"].get("reasoning", ""),
                            "confidence": int((result["result"].get("confidence") or 0) * 100),
                            "sentiment": "bullish" if result["result"].get("action") == "buy" else (
                                "bearish" if result["result"].get("action") == "sell" else "neutral"
                            ),
                            "data": result["result"],
                        },
                        "vote": {
                            "action": result["result"].get("action"),
                            "confidence": int((result["result"].get("confidence") or 0) * 100),
                            "weight": int((result["result"].get("confidence") or 0) * 100 * role_weights.get("market_analyst", 1.0)),
                        },
                        "timestamp": datetime.now(timezone.utc),
                        "ui": {
                            "tone": "neutral",
                            "icon": "activity",
                            "color": "blue",
                        },
                    }
                    for idx, result in enumerate(swarm_results)
                ],
                "swarm_vote": {
                    "total_agents": len(swarm_results),
                    "votes": swarm_aggregate["members"],
                    "results": swarm_aggregate["votes"],
                    "consensus": {
                        "action": swarm_aggregate["action"],
                        "confidence": int(swarm_aggregate["confidence"] * 100),
                        "agreement": swarm_aggregate["agreement"],
                        "is_unanimous": swarm_aggregate["is_unanimous"],
                    },
                    "voting_completed": datetime.now(timezone.utc),
                },
                "outcome": {
                    "executed": False,
                    "action": swarm_aggregate["action"],
                    "reasoning": swarm_aggregate["reasoning"],
                    "timestamp": datetime.now(timezone.utc),
                },
                "status": "completed",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            })
        else:
            # Run Market Analyst
            market_analyst = MarketAnalystAgent(
                model_provider=model_provider,
                model_name=model_name,
            )
            analyst_before = market_analyst.model.get_model_info()
            analyst_start = time.perf_counter()
            analysis_result = await market_analyst.process(analysis_context)
            analyst_duration_ms = int((time.perf_counter() - analyst_start) * 1000)
            analyst_after = market_analyst.model.get_model_info()
            analyst_usage = _usage_delta(analyst_before, analyst_after)
        analysis_action = analysis_result.get("action") or "hold"
        analysis_confidence = analysis_result.get("confidence") or 0
        analysis_reasoning = analysis_result.get("reasoning") or "No market analysis reasoning returned."
        effective_action = analysis_action
        demo_force_reason = None
        if demo_force_position:
            effective_action, demo_force_reason = _resolve_demo_force_action(
                analysis_action,
                signal_data,
                execution_config,
            )
        
        # Save market analyst decision
        analyst_decision = AgentDecision(
            execution_id=execution.id,
            agent_role="market_analyst",
            action=analysis_action,
            confidence=analysis_confidence,
            reasoning=analysis_reasoning,
            data={
                **analysis_result,
                "signal": signal_data,
                "usage": analyst_usage,
            },
        )
        await save_agent_decision(db, analyst_decision)
        
        await db[AI_DECISIONS_LOG_COLLECTION].insert_one({
            "user_id": (flow.config or {}).get("user_id"),
            "flow_id": execution.flow_id,
            "agent_role": "market_analyst",
            "model_provider": analyst_usage.get("model_provider") or market_analyst.model_provider,
            "model_name": analyst_usage.get("model_name") or market_analyst.model.model_name,
            "decision_type": "market_analysis",
            "step": StepName.MARKET_ANALYSIS.value,
            "input_context": analysis_context,
            "ai_response": analysis_result,
            "prompt_used": None,
            "system_prompt_used": None,
            "input_tokens": analyst_usage.get("input_tokens", 0),
            "output_tokens": analyst_usage.get("output_tokens", 0),
            "cost_usd": analyst_usage.get("cost_usd", 0.0),
            "success": True,
            "error_message": None,
            "timestamp": datetime.now(timezone.utc),
            "execution_time_ms": analyst_duration_ms,
            "metadata": {
                "execution_id": execution.id,
            },
        })
        
        await update_execution(db, execution.id, {
            f"steps.{STEP_MARKET_ANALYSIS}.status": StepStatus.COMPLETED.value,
            f"steps.{STEP_MARKET_ANALYSIS}.completed_at": datetime.now(timezone.utc),
            f"steps.{STEP_MARKET_ANALYSIS}.data": analysis_result,
        })
        await _emit_execution_update(
            execution.id, flow.id, "RUNNING", STEP_RISK_VALIDATION,
            "Risk Check Gate", 60, "Evaluating risk parameters and constraints...", user_id
        )
        
        # Heartbeat: Update lock expiration after market analysis
        await heartbeat_execution_lock(db, flow.id, str(execution.id))

        # Phase 2: Pre-trade gate (configurable thresholds + signal alignment)
        pre_trade_config = execution_config
        min_confidence = float(pre_trade_config.get("pre_trade_min_confidence", 0.6))
        signal_min_confidence = float(pre_trade_config.get("pre_trade_signal_min_confidence", 0.4))
        require_signal = bool(pre_trade_config.get("pre_trade_require_signal", False))
        require_alignment = bool(pre_trade_config.get("pre_trade_require_signal_alignment", True))

        pre_trade_reasons = []
        proceed = True

        if analysis_action == "hold":
            proceed = False
            pre_trade_reasons.append("Market analysis returned hold.")

        if analysis_confidence < min_confidence:
            proceed = False
            pre_trade_reasons.append(
                f"Market analysis confidence {analysis_confidence:.2f} below {min_confidence:.2f}."
            )

        signal_confidence = None
        signal_classification = None
        if signal_data:
            signal_confidence = signal_data.get("confidence")
            signal_classification = signal_data.get("classification")

            if signal_confidence is not None and signal_confidence < signal_min_confidence:
                proceed = False
                pre_trade_reasons.append(
                    f"Signal confidence {signal_confidence:.2f} below {signal_min_confidence:.2f}."
                )

            if require_alignment:
                bullish = {"bullish", "very_bullish"}
                bearish = {"bearish", "very_bearish"}
                aligned = False
                if analysis_action == "buy" and signal_classification in bullish:
                    aligned = True
                elif analysis_action == "sell" and signal_classification in bearish:
                    aligned = True
                elif analysis_action == "hold" and signal_classification == "neutral":
                    aligned = True

                if not aligned:
                    proceed = False
                    pre_trade_reasons.append(
                        f"Signal classification '{signal_classification}' not aligned with '{analysis_action}'."
                    )
        elif require_signal:
            proceed = False
            pre_trade_reasons.append("Signal data required but unavailable.")

        if demo_force_position:
            proceed = True
            pre_trade_reasons.append("Demo force position enabled; bypassing pre-trade gate.")
        pre_trade_action = "proceed" if proceed else "skip"
        if signal_confidence is not None:
            pre_trade_confidence = round((analysis_confidence + signal_confidence) / 2, 4)
        else:
            pre_trade_confidence = round(analysis_confidence, 4)

        if proceed:
            pre_trade_reasoning = "Pre-trade gate passed."
        else:
            pre_trade_reasoning = "Pre-trade gate blocked: " + " ".join(pre_trade_reasons)
        if demo_force_position:
            pre_trade_reasoning = "Pre-trade gate bypassed for demo execution. " + pre_trade_reasoning

        pre_trade_decision = AgentDecision(
            execution_id=execution.id,
            agent_role="pre_trade_evaluator",
            action=pre_trade_action,
            confidence=pre_trade_confidence,
            reasoning=pre_trade_reasoning,
            data={
                "analysis_action": analysis_action,
                "analysis_confidence": analysis_confidence,
                "signal": signal_data,
                "thresholds": {
                    "min_confidence": min_confidence,
                    "signal_min_confidence": signal_min_confidence,
                    "require_signal": require_signal,
                    "require_alignment": require_alignment,
                },
            },
        )
        await save_agent_decision(db, pre_trade_decision)

        if not proceed and not demo_force_position:
            completed_at = datetime.now(timezone.utc)
            duration = int((completed_at - execution.started_at).total_seconds() * 1000)

            result = ExecutionResult(
                action="hold",
                confidence=pre_trade_confidence,
                reasoning=pre_trade_reasoning,
            )

            await update_execution(db, execution.id, {
                f"steps.{STEP_RISK_VALIDATION}.status": StepStatus.SKIPPED.value,
                f"steps.{STEP_RISK_VALIDATION}.completed_at": completed_at,
                f"steps.{STEP_RISK_VALIDATION}.data": {"reason": pre_trade_reasoning},
            })

            await update_execution(db, execution.id, {
                f"steps.{STEP_DECISION}.status": StepStatus.RUNNING.value,
                f"steps.{STEP_DECISION}.started_at": completed_at,
            })

            await update_execution(db, execution.id, {
                "status": ExecutionStatus.COMPLETED.value,
                "completed_at": completed_at,
                "duration": duration,
                f"steps.{STEP_DECISION}.status": StepStatus.COMPLETED.value,
                f"steps.{STEP_DECISION}.completed_at": completed_at,
                f"steps.{STEP_DECISION}.data": {
                    "final_action": "hold",
                    "confidence": pre_trade_confidence,
                    "reason": pre_trade_reasoning,
                },
                "result": result.model_dump(),
            })

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

            await _schedule_auto_loop(db, flow, model_provider, model_name)
            return await get_execution_by_id(db, execution.id)

        # Step 2: Risk Validation
        await update_execution(db, execution.id, {
            f"steps.{STEP_RISK_VALIDATION}.status": StepStatus.RUNNING.value,
            f"steps.{STEP_RISK_VALIDATION}.started_at": datetime.now(timezone.utc),
        })

        # Phase 3: Risk rules engine (hard limits)
        risk_config = execution_config
        risk_rule_id = risk_config.get("risk_rule_id")
        risk_rule = None
        if risk_rule_id:
            risk_rule = await risk_rule_service.get_risk_rule_by_id(db, risk_rule_id)
        risk_limits = (risk_rule.limits if risk_rule else risk_config.get("risk_limits", {}))
        portfolio_state = {
            "portfolio_value_usd": risk_config.get("portfolio_value_usd", 10000),
            "open_positions": risk_config.get("open_positions", 0),
            "daily_loss_usd": risk_config.get("daily_loss_usd", 0),
            "portfolio_utilization_percent": risk_config.get("portfolio_utilization_percent", 0),
        }

        order_size_usd = risk_config.get("order_size_usd")
        order_size_percent = risk_config.get("order_size_percent")
        portfolio_value_usd = float(portfolio_state.get("portfolio_value_usd") or 0)

        if order_size_usd is None and order_size_percent is not None:
            order_size_usd = (float(order_size_percent) / 100.0) * portfolio_value_usd
        if order_size_usd is None:
            order_size_usd = 100.0

        current_price = market_context.get("current_price")
        order_type_value = risk_config.get("order_type", "market")
        quantity = None
        if current_price:
            quantity = float(order_size_usd) / float(current_price)
        order_request = {
            "symbol": flow.symbol,
            "action": effective_action,
            "side": effective_action,
            "order_type": order_type_value,
            "quantity": quantity,
            "estimated_value": float(order_size_usd),
            "size_usd": float(order_size_usd),
            "price": current_price,
        }

        risk_rules_result = evaluate_risk_limits(order_request, risk_limits, portfolio_state)
        risk_rules_action = "approve" if risk_rules_result["approved"] else "reject"
        risk_rules_reasoning = (
            "Risk rules passed."
            if risk_rules_result["approved"]
            else "Risk rules blocked: " + " ".join(risk_rules_result["violations"])
        )

        risk_rules_decision = AgentDecision(
            execution_id=execution.id,
            agent_role="risk_rules_engine",
            action=risk_rules_action,
            confidence=1.0 if risk_rules_result["approved"] else 0.0,
            reasoning=risk_rules_reasoning,
            data={
                "order_request": order_request,
                "risk_rule_id": str(risk_rule.id) if risk_rule else None,
                "risk_limits": risk_limits,
                "portfolio_state": portfolio_state,
                "validation": risk_rules_result,
            },
        )
        await save_agent_decision(db, risk_rules_decision)

        if not risk_rules_result["approved"] and demo_force_position:
            risk_rules_result["overridden"] = True
            risk_rules_reasoning = f"Demo force position override. {risk_rules_reasoning}"

        if not risk_rules_result["approved"] and not demo_force_position:
            completed_at = datetime.now(timezone.utc)
            duration = int((completed_at - execution.started_at).total_seconds() * 1000)

            result = ExecutionResult(
                action="hold",
                confidence=0.0,
                reasoning=risk_rules_reasoning,
            )

            await update_execution(db, execution.id, {
                f"steps.{STEP_RISK_VALIDATION}.status": StepStatus.COMPLETED.value,
                f"steps.{STEP_RISK_VALIDATION}.completed_at": completed_at,
                f"steps.{STEP_RISK_VALIDATION}.data": risk_rules_result,
            })
            await _emit_execution_update(
                execution.id, flow.id, "RUNNING", STEP_DECISION,
                "Placing Order on Exchange", 90, "Executing trade order...", user_id
            )
            
            # Heartbeat: Update lock expiration after risk validation
            await heartbeat_execution_lock(db, flow.id, str(execution.id))

            await update_execution(db, execution.id, {
                f"steps.{STEP_DECISION}.status": StepStatus.RUNNING.value,
                f"steps.{STEP_DECISION}.started_at": completed_at,
            })

            await update_execution(db, execution.id, {
                "status": ExecutionStatus.COMPLETED.value,
                "completed_at": completed_at,
                "duration": duration,
                f"steps.{STEP_DECISION}.status": StepStatus.COMPLETED.value,
                f"steps.{STEP_DECISION}.completed_at": completed_at,
                f"steps.{STEP_DECISION}.data": {
                    "final_action": "hold",
                    "confidence": 0.0,
                    "reason": risk_rules_reasoning,
                },
                "result": result.model_dump(),
            })

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

            await _schedule_auto_loop(db, flow, model_provider, model_name)
            return await get_execution_by_id(db, execution.id)
        
        # Run Risk Manager
        risk_manager = RiskManagerAgent(
            model_provider=model_provider,
            model_name=model_name,
        )
        
        risk_context = {
            "symbol": flow.symbol,
            "proposed_action": effective_action,
            "confidence": analysis_result.get("confidence", 0),
            "market_data": market_context,
            "indicators": indicators,
            "reasoning": analysis_result.get("reasoning", ""),
            "signal": signal_data,
            "risk_limits": risk_limits,
            "risk_rules": risk_rules_result,
            "order_request": order_request,
            "portfolio_balance": float(portfolio_state.get("portfolio_value_usd") or 0),
            "current_positions": risk_config.get("current_positions", []),
        }
        
        risk_before = risk_manager.model.get_model_info()
        risk_start = time.perf_counter()
        risk_result = await risk_manager.process(risk_context)
        risk_duration_ms = int((time.perf_counter() - risk_start) * 1000)
        risk_after = risk_manager.model.get_model_info()
        risk_usage = _usage_delta(risk_before, risk_after)
        risk_approved = risk_result.get("approved")
        risk_action = "approve" if risk_approved else "reject"
        risk_score = risk_result.get("risk_score")
        risk_confidence = risk_result.get("confidence")
        if risk_confidence is None and risk_score is not None:
            risk_confidence = max(0.0, min(1.0, 1 - float(risk_score)))
        risk_confidence = risk_confidence or 0
        risk_reasoning = risk_result.get("reason") or "Risk validation rejected the trade."

        risk_warning_score = float((flow.config or {}).get("risk_warning_score", 0.6))
        risk_warning_reduce_percent = float((flow.config or {}).get("risk_warning_reduce_percent", 50))
        risk_warning = False
        order_quantity_override: Optional[Decimal] = None
        order_size_usd_override: Optional[Decimal] = None

        if risk_action == "approve" and risk_score is not None and float(risk_score) >= risk_warning_score:
            risk_warning = True
            adjustments = risk_result.get("adjustments") or {}
            suggested_quantity = adjustments.get("suggested_quantity")
            if suggested_quantity:
                order_quantity_override = Decimal(str(suggested_quantity))
            else:
                order_size_usd = (flow.config or {}).get("order_size_usd")
                if order_size_usd is not None:
                    reduction = max(0.0, min(100.0, risk_warning_reduce_percent))
                    order_size_usd_override = Decimal(str(order_size_usd)) * (Decimal("1") - Decimal(str(reduction)) / Decimal("100"))
            risk_result["warning"] = True
            risk_result["warning_action"] = "reduce_size"
        
        # Save risk manager decision
        risk_decision = AgentDecision(
            execution_id=execution.id,
            agent_role="risk_manager",
            action=risk_action,
            confidence=risk_confidence,
            reasoning=risk_reasoning,
            data={
                **risk_result,
                "usage": risk_usage,
            },
        )
        await save_agent_decision(db, risk_decision)
        
        await db[AI_DECISIONS_LOG_COLLECTION].insert_one({
            "user_id": (flow.config or {}).get("user_id"),
            "flow_id": execution.flow_id,
            "agent_role": "risk_manager",
            "model_provider": risk_usage.get("model_provider") or risk_manager.model_provider,
            "model_name": risk_usage.get("model_name") or risk_manager.model.model_name,
            "decision_type": "risk_validation",
            "step": StepName.RISK_VALIDATION.value,
            "input_context": risk_context,
            "ai_response": risk_result,
            "prompt_used": None,
            "system_prompt_used": None,
            "input_tokens": risk_usage.get("input_tokens", 0),
            "output_tokens": risk_usage.get("output_tokens", 0),
            "cost_usd": risk_usage.get("cost_usd", 0.0),
            "success": True,
            "error_message": None,
            "timestamp": datetime.now(timezone.utc),
            "execution_time_ms": risk_duration_ms,
            "metadata": {
                "execution_id": execution.id,
                "risk_rules": risk_rules_result,
                "order_request": order_request,
            },
        })
        
        # Determine final action
        final_action = "hold"
        final_confidence = 0.0
        final_reasoning = ""
        total_ai_cost_usd = round(
            float(analyst_usage.get("cost_usd", 0.0)) + float(risk_usage.get("cost_usd", 0.0)),
            6,
        )
        
        if risk_action == "approve":
            final_action = effective_action
            final_confidence = analysis_confidence * risk_confidence
            final_reasoning = f"Market Analysis: {analysis_reasoning}. Risk Assessment: {risk_reasoning}"
        else:
            final_action = "hold"
            final_confidence = risk_confidence
            final_reasoning = f"Trade rejected by Risk Manager: {risk_reasoning}"

        if demo_force_position:
            if final_action == "hold":
                final_action = effective_action
            final_reasoning = f"{final_reasoning} Demo force position override: {demo_force_reason or 'enabled'}."

        single_position_mode = bool(execution_config.get("single_position_mode", True))
        if single_position_mode and final_action in ["buy", "sell"]:
            user_id = execution_config.get("user_id") or (flow.config or {}).get("user_id")
            flow_id_obj = _to_object_id(execution.flow_id) or execution.flow_id
            user_id_obj = _to_object_id(user_id) or user_id if user_id else None

            query = {
                "flow_id": flow_id_obj,
                "status": {"$in": [PositionStatus.OPEN.value, PositionStatus.OPENING.value]},
                "deleted_at": None,
            }
            if user_id_obj:
                query["user_id"] = user_id_obj

            existing_position = await db[POSITIONS_COLLECTION].find_one(
                query,
                sort=[("opened_at", -1)],
            )
            if existing_position:
                existing_side = existing_position.get("side")
                existing_action = "buy" if existing_side == PositionSide.LONG.value else "sell"
                if existing_action == final_action:
                    final_action = "hold"
                    final_reasoning = (
                        f"{final_reasoning} Single-position mode active: "
                        f"existing {existing_side} position already open; skipping new order."
                    )
                else:
                    close_price = market_context.get("current_price") or existing_position.get("current", {}).get("price")
                    close_price = close_price or existing_position.get("entry", {}).get("price")
                    close_price = Decimal(str(close_price or 0))
                    if close_price > 0:
                        try:
                            position_doc = await Position.get(str(existing_position.get("_id")))
                        except Exception as e:
                            logger.warning(f"Failed to close existing position {existing_position.get('_id')}: {e}")
                            position_doc = None

                        if position_doc and position_doc.is_open():
                            await position_doc.close(
                                order_id=position_doc.id,
                                price=close_price,
                                reason="reverse_signal",
                                fees=Decimal("0"),
                            )
                        else:
                            entry_data = existing_position.get("entry", {})
                            entry_amount = Decimal(str(entry_data.get("amount", 0)))
                            exit_value = entry_amount * close_price
                            exit_data = {
                                "order_id": str(existing_position.get("_id")),
                                "timestamp": datetime.now(timezone.utc),
                                "price": float(close_price),
                                "amount": float(entry_amount),
                                "value": float(exit_value),
                                "fees": 0.0,
                                "fee_currency": "USDT",
                                "reason": "reverse_signal",
                                "realized_pnl": 0.0,
                                "realized_pnl_percent": 0.0,
                                "time_held_minutes": 0,
                            }
                            await db[POSITIONS_COLLECTION].update_one(
                                {"_id": existing_position.get("_id")},
                                {
                                    "$set": {
                                        "status": PositionStatus.CLOSED.value,
                                        "closed_at": datetime.now(timezone.utc),
                                        "updated_at": datetime.now(timezone.utc),
                                        "exit": exit_data,
                                    }
                                },
                            )

                        final_reasoning = (
                            f"{final_reasoning} Single-position mode active: "
                            f"closed existing {existing_side} position before opening {final_action}."
                        )

        order_record = None
        position_record = None
        if final_action in ["buy", "sell"]:
            user_wallet_id = execution_config.get("user_wallet_id")
            user_id = execution_config.get("user_id")
            
            # Auto-detect wallet if user_id is provided but wallet_id is not
            if not user_wallet_id and user_id:
                try:
                    from app.modules.user_wallets import service as user_wallet_service
                    user_wallets = await user_wallet_service.get_user_wallets(db, str(user_id), is_active=True)
                    if user_wallets:
                        user_wallet_id = user_wallets[0]["id"]  # Use first active wallet
                        logger.info(f"Auto-detected wallet {user_wallet_id} for user {user_id}")
                except Exception as e:
                    logger.warning(f"Failed to auto-detect wallet: {e}")
            
            # If no wallet configured, create simulated position (demo mode)
            is_simulated = not user_wallet_id
            if is_simulated:
                logger.info(f"No wallet configured - creating simulated position for {flow.symbol}")
                wallet = None
                base_balance = None
                quote_balance = None
            else:
                wallet = await create_wallet_from_db(db, user_wallet_id)
                symbol_parts = flow.symbol.split("/")
                base_asset = symbol_parts[0] if symbol_parts else None
                quote_asset = symbol_parts[1] if len(symbol_parts) > 1 else None
                base_balance = await wallet.get_balance(base_asset) if base_asset else None
                quote_balance = await wallet.get_balance(quote_asset) if quote_asset else None
                logger.info(f"Wallet balances - Base ({base_asset}): {base_balance}, Quote ({quote_asset}): {quote_balance}")

            order_type_value = execution_config.get("order_type", "market")
            time_in_force_value = execution_config.get("time_in_force", "GTC")
            order_type = OrderType(order_type_value)
            time_in_force = TimeInForce(time_in_force_value)

            # Parse symbol for asset names
            symbol_parts = flow.symbol.split("/")
            base_asset = symbol_parts[0] if symbol_parts else None
            quote_asset = symbol_parts[1] if len(symbol_parts) > 1 else None

            quantity_value = execution_config.get("order_quantity")
            if order_quantity_override is not None:
                quantity_value = order_quantity_override
            quantity = Decimal(str(quantity_value)) if quantity_value is not None else None
            order_size_usd = execution_config.get("order_size_usd")
            if order_size_usd_override is not None:
                order_size_usd = order_size_usd_override
            order_size_usd = Decimal(str(order_size_usd)) if order_size_usd is not None else None
            order_size_percent = execution_config.get("order_size_percent")
            order_size_percent = Decimal(str(order_size_percent)) if order_size_percent is not None else None
            default_balance_percent = Decimal(str(execution_config.get("order_balance_percent", 10)))

            current_price = Decimal(str(market_context.get("current_price", 0)))
            
            # For simulated trades, use default sizing
            if is_simulated:
                # Default to $100 USD order size for simulated trades
                default_order_usd = Decimal(str(execution_config.get("order_size_usd", 100)))
                if current_price > 0:
                    quantity = default_order_usd / current_price
                else:
                    quantity = Decimal("0.001")  # Fallback quantity
                sizing_meta = {
                    "simulated": True,
                    "order_size_usd": float(default_order_usd),
                    "sizing_method": "simulated_default",
                }
                logger.info(f"Simulated trade - Using ${default_order_usd} order size = {quantity} {base_asset}")
            else:
                # Use actual wallet balances
                quantity, sizing_meta = _resolve_order_quantity(
                    action=final_action,
                    current_price=current_price,
                    base_balance=base_balance,
                    quote_balance=quote_balance,
                    order_quantity=quantity,
                    order_size_usd=order_size_usd,
                    order_size_percent=order_size_percent,
                    default_balance_percent=default_balance_percent,
                )
                logger.info(f"Real wallet trade - Quantity: {quantity} {base_asset}, Method: {sizing_meta.get('sizing_method', 'unknown')}")

                # Balance checks only for real trades
                if final_action == "buy" and quote_balance is not None:
                    estimated_cost = quantity * current_price
                    if estimated_cost > quote_balance:
                        raise Exception("Insufficient quote balance for buy order")

                if final_action == "sell" and base_balance is not None:
                    if quantity > base_balance:
                        raise Exception("Insufficient base balance for sell order")

            price = execution_config.get("limit_price")
            stop_price = execution_config.get("stop_price")
            price_decimal = Decimal(str(price)) if price is not None else None
            stop_decimal = Decimal(str(stop_price)) if stop_price is not None else None

            # EXECUTION SAFEGUARD #2: Price Staleness Check
            # For real trades, refetch current price and check staleness
            if not is_simulated:
                # Refetch current price from exchange
                fresh_price = None
                if wallet:
                    try:
                        fresh_price = await wallet.get_market_price(flow.symbol)
                    except Exception as e:
                        logger.warning(f"Failed to refetch price from wallet: {e}")

                if fresh_price is None:
                    # Fallback to Binance API
                    async with BinanceClient() as binance_client:
                        fresh_price = await binance_client.get_price(flow.symbol)

                if fresh_price is not None:
                    fresh_price = Decimal(str(fresh_price))
                    original_price = Decimal(str(current_price))

                    # Calculate price movement percentage
                    if original_price > 0:
                        price_change_pct = ((fresh_price - original_price) / original_price) * 100

                        # Check if price moved against us by more than 1%
                        if final_action == "buy" and price_change_pct > 1.0:
                            logger.warning(f"Price Staleness: BUY order canceled due to {price_change_pct:.2f}% price increase")
                            await update_execution(db, execution.id, {
                                "status": ExecutionStatus.FAILED.value,
                                "completed_at": datetime.now(timezone.utc),
                                "duration": int((datetime.now(timezone.utc) - execution.started_at).total_seconds() * 1000),
                                "error": f"Price Staleness Error: Price increased {price_change_pct:.2f}% from {original_price} to {fresh_price} during analysis - canceling BUY order"
                            })
                            raise Exception(f"Price staleness: BUY order canceled due to {price_change_pct:.2f}% price increase")

                        elif final_action == "sell" and price_change_pct < -1.0:
                            logger.warning(f"Price Staleness: SELL order canceled due to {price_change_pct:.2f}% price decrease")
                            await update_execution(db, execution.id, {
                                "status": ExecutionStatus.FAILED.value,
                                "completed_at": datetime.now(timezone.utc),
                                "duration": int((datetime.now(timezone.utc) - execution.started_at).total_seconds() * 1000),
                                "error": f"Price Staleness Error: Price decreased {price_change_pct:.2f}% from {original_price} to {fresh_price} during analysis - canceling SELL order"
                            })
                            raise Exception(f"Price staleness: SELL order canceled due to {price_change_pct:.2f}% price decrease")

                        else:
                            logger.info(f"Price Staleness: Price change {price_change_pct:.2f}% within acceptable range")
                    else:
                        logger.warning("Original price is zero or invalid - skipping staleness check")
                else:
                    logger.warning("Could not fetch fresh price for staleness check")

            # Place real order or simulate
            if is_simulated:
                # Simulated order - no actual exchange interaction
                order_result = {
                    "success": True,
                    "order_id": f"SIM-{execution.id}",
                    "client_order_id": f"SIM-{execution.id}",
                    "status": OrderStatus.FILLED.value,
                    "filled_quantity": quantity,
                    "average_price": current_price,
                    "fee": Decimal("0"),
                    "fee_currency": quote_asset or "USDT",
                    "simulated": True,
                }
                logger.info(f"Simulated order created: {order_result['order_id']}")
            else:
                max_retries = int(execution_config.get("order_max_retries", 2))
                retry_delay_seconds = float(execution_config.get("order_retry_delay_seconds", 1.5))

                order_result = await _place_order_with_retry(
                    wallet=wallet,
                    symbol=flow.symbol,
                    side=OrderSide.BUY if final_action == "buy" else OrderSide.SELL,
                    order_type=order_type,
                    quantity=quantity,
                    price=price_decimal,
                    stop_price=stop_decimal,
                    time_in_force=time_in_force,
                    max_retries=max_retries,
                    retry_delay_seconds=retry_delay_seconds,
                )

                if not order_result.get("success", True):
                    raise Exception("Order placement failed")

            filled_quantity = order_result.get("filled_quantity") or Decimal("0")
            average_price = order_result.get("average_price")
            status_value = order_result.get("status")
            if isinstance(status_value, OrderStatus):
                status_value = status_value.value

            now = datetime.now(timezone.utc)
            user_id = execution_config.get("user_id")
            exchange_response = _to_serializable(order_result)
            exchange_name = "simulated" if is_simulated else (wallet.__class__.__name__.lower() if wallet else "unknown")
            order_record = {
                "user_id": _to_object_id(user_id) or user_id,
                "user_wallet_id": _to_object_id(user_wallet_id) if user_wallet_id else None,
                "flow_id": _to_object_id(execution.flow_id) or execution.flow_id,
                "execution_id": _to_object_id(execution.id) or execution.id,
                "symbol": flow.symbol,
                "side": final_action,
                "order_type": order_type.value,
                "time_in_force": time_in_force.value,
                "requested_amount": float(quantity),
                "filled_amount": float(filled_quantity),
                "remaining_amount": float(quantity - Decimal(str(filled_quantity))),
                "limit_price": float(price_decimal) if price_decimal is not None else None,
                "stop_price": float(stop_decimal) if stop_decimal is not None else None,
                "average_fill_price": float(average_price) if average_price is not None else None,
                "status": status_value or OrderStatus.SUBMITTED.value,
                "exchange": exchange_name,
                "external_order_id": order_result.get("order_id"),
                "exchange_response": exchange_response,
                "fills": [],
                "status_history": [
                    {
                        "status": status_value or OrderStatus.SUBMITTED.value,
                        "timestamp": now,
                        "reason": "Simulated order via flow execution" if is_simulated else "Order placed via flow execution",
                        "metadata": {"simulated": is_simulated},
                    }
                ],
                "total_fees": float(order_result.get("fee", 0)) if order_result.get("fee") else 0,
                "total_fees_usd": float(order_result.get("fee", 0)) if order_result.get("fee") else 0,
                "ai_reasoning": final_reasoning,
                "ai_confidence": int(final_confidence * 100),
                "created_at": now,
                "submitted_at": now,
                "simulated": is_simulated,
                "metadata": {
                    "client_order_id": order_result.get("client_order_id"),
                    "balances": {
                        "base_asset": base_asset,
                        "quote_asset": quote_asset,
                        "base_balance": float(base_balance) if base_balance is not None else None,
                        "quote_balance": float(quote_balance) if quote_balance is not None else None,
                    },
                    "sizing": sizing_meta,
                },
            }

            order_record = _to_serializable(order_record)
            insert_result = await db[ORDERS_COLLECTION].insert_one(order_record)
            order_object_id = insert_result.inserted_id
            order_record["_id"] = str(order_object_id)
            final_reasoning += f" Order placed: {order_record.get('external_order_id')}."

            position_quantity = Decimal(str(filled_quantity))
            demo_forced_position = False
            
            # Force position creation when demo_force_position is enabled
            if demo_force_position:
                demo_forced_position = True
                # Ensure we have a valid quantity - use filled_quantity, quantity, or calculate from order_size_usd
                if position_quantity <= 0:
                    if quantity and quantity > 0:
                        position_quantity = quantity
                    elif order_size_usd and current_price > 0:
                        position_quantity = order_size_usd / current_price
                    else:
                        # Default to $100 USD worth if nothing else available
                        default_order_usd = Decimal("100")
                        if current_price > 0:
                            position_quantity = default_order_usd / current_price
                        else:
                            position_quantity = Decimal("0.001")  # Fallback minimum
            
            # Also handle non-demo cases
            if position_quantity <= 0 and not demo_force_position:
                if quantity and quantity > 0:
                    position_quantity = quantity
                elif order_size_usd and current_price > 0:
                    position_quantity = order_size_usd / current_price

            # ALWAYS create position if demo_force_position is enabled OR if we have valid quantity
            if demo_force_position or position_quantity > 0:
                side = "long" if final_action == "buy" else "short"
                entry_price_value = average_price
                if entry_price_value is None:
                    entry_price_value = price_decimal
                if entry_price_value is None:
                    entry_price_value = market_context.get("current_price")
                entry_price = Decimal(str(entry_price_value or 0))
                entry_value = (Decimal(str(position_quantity)) * entry_price) if entry_price else Decimal("0")
                stop_loss = analysis_result.get("stop_loss")
                take_profit = analysis_result.get("take_profit")
                adjustments = risk_result.get("adjustments") or {}
                if stop_loss is None:
                    stop_loss = adjustments.get("suggested_stop_loss")
                if take_profit is None:
                    take_profit = adjustments.get("suggested_take_profit")
                default_stop_loss_percent = float(execution_config.get("default_stop_loss_percent", 1.5))
                default_take_profit_percent = float(execution_config.get("default_take_profit_percent", 3))
                stop_loss_source = "agent"
                take_profit_source = "agent"
                if stop_loss is None and entry_price:
                    stop_loss_source = "default"
                    if side == "long":
                        stop_loss = float(entry_price * (Decimal("1") - Decimal(str(default_stop_loss_percent)) / Decimal("100")))
                    else:
                        stop_loss = float(entry_price * (Decimal("1") + Decimal(str(default_stop_loss_percent)) / Decimal("100")))
                if take_profit is None and entry_price:
                    take_profit_source = "default"
                    if side == "long":
                        take_profit = float(entry_price * (Decimal("1") + Decimal(str(default_take_profit_percent)) / Decimal("100")))
                    else:
                        take_profit = float(entry_price * (Decimal("1") - Decimal(str(default_take_profit_percent)) / Decimal("100")))

                # Set position status - use PositionStatus enum values for Beanie compatibility
                if filled_quantity and Decimal(str(filled_quantity)) > 0:
                    position_status = PositionStatus.OPEN.value
                else:
                    position_status = PositionStatus.OPENING.value
                if is_simulated:
                    position_status = PositionStatus.OPEN.value  # Simulated positions are immediately open
                
                # Ensure user_id is set - required for position queries
                if not user_id:
                    user_id = (flow.config or {}).get("user_id")
                if not user_id:
                    logger.warning(f"No user_id in flow config - checking flow document")
                    # Try to get from flow document config if available
                    flow_doc = await db[FLOWS_COLLECTION].find_one({"_id": ObjectId(flow.id)})
                    if flow_doc:
                        flow_config = flow_doc.get("config", {})
                        if flow_config and flow_config.get("user_id"):
                            user_id = flow_config["user_id"]
                            logger.info(f"Retrieved user_id from flow document config: {user_id}")
                        # Also check if user_id is stored at root level (legacy support)
                        elif flow_doc.get("user_id"):
                            user_id = flow_doc["user_id"]
                            logger.info(f"Retrieved user_id from flow document root: {user_id}")
                
                # Use demo user fallback for ALL positions when user_id is missing
                # (Previously only applied to simulated positions, causing Beanie errors)
                if not user_id:
                    logger.info("No user_id found - attempting to use demo user as fallback")
                    user_id = await _get_or_create_demo_user(db)
                    if user_id:
                        logger.info(f"Using demo user_id: {user_id} for position")
                        # Update flow config with demo user_id for future executions
                        try:
                            await db[FLOWS_COLLECTION].update_one(
                                {"_id": ObjectId(flow.id)},
                                {"$set": {"config.user_id": user_id}}
                            )
                            logger.info(f"Updated flow config with demo user_id: {user_id}")
                        except Exception as e:
                            logger.warning(f"Failed to update flow config with demo user_id: {e}")
                
                # Convert to ObjectId for Beanie compatibility
                user_id_obj = _to_object_id(user_id) if user_id else None
                if not user_id_obj and user_id:
                    try:
                        user_id_obj = ObjectId(str(user_id))
                        logger.info(f"Converted user_id to ObjectId: {user_id_obj}")
                    except Exception as e:
                        logger.error(f"Invalid user_id format: {user_id} - {e}")
                        user_id_obj = None
                
                # Validation: Prevent position creation without user_id
                # This ensures Beanie queries work and positions appear in user lists
                if not user_id_obj:
                    error_msg = f"Cannot create position: No user_id available for flow {flow.id}. All fallback methods failed."
                    logger.error(error_msg)
                    # Update execution with error instead of creating orphaned position
                    # Note: Lock will be released in finally block - no need to release here
                    await update_execution(db, execution.id, {
                        "status": ExecutionStatus.FAILED.value,
                        "completed_at": datetime.now(timezone.utc),
                        "error": error_msg
                    })
                    return execution
                
                # Ensure flow_id is properly set - use flow.id as fallback
                position_flow_id = _to_object_id(execution.flow_id) or _to_object_id(str(flow.id))
                if not position_flow_id:
                    logger.warning(f"Could not set flow_id for position. execution.flow_id={execution.flow_id}, flow.id={flow.id}")
                
                position_record = {
                    "user_id": user_id_obj,
                    "user_wallet_id": _to_object_id(user_wallet_id) if user_wallet_id else None,
                    "simulated": is_simulated,
                    "flow_id": position_flow_id,
                    "symbol": flow.symbol,
                    "side": PositionSide.LONG.value if side == "long" else PositionSide.SHORT.value,
                    "status": position_status,
                    "entry": {
                        "order_id": order_object_id,
                        "timestamp": now,
                        "price": float(entry_price),
                        "amount": float(position_quantity),
                        "value": float(entry_value),
                        "leverage": 1,
                        "margin_used": float(entry_value),
                        "fees": float(order_record.get("total_fees", 0)),
                        "fee_currency": order_result.get("fee_currency", "USDT"),
                        "ai_reasoning": final_reasoning,
                        "ai_confidence": int(final_confidence * 100),
                        "ai_agent": "flow_execution",
                    },
                    "current": {
                        "price": float(entry_price),
                        "value": float(entry_value),
                        "unrealized_pnl": 0.0,
                        "unrealized_pnl_percent": 0.0,
                        "risk_level": "medium",
                        "time_held_minutes": 0,
                        "high_water_mark": float(entry_price),
                        "low_water_mark": float(entry_price),
                        "max_drawdown_percent": 0.0,
                        "last_updated": now,
                    },
                    "risk_management": {
                        "stop_loss": stop_loss,
                        "take_profit": take_profit,
                        "stop_loss_source": stop_loss_source,
                        "take_profit_source": take_profit_source,
                        "demo_forced_position": demo_forced_position,
                    },
                    "ai_monitoring": {},
                    "statistics": {},
                    "created_at": now,
                    "opened_at": now,
                    "updated_at": now,
                    "deleted_at": None,
                }

                position_record = _to_serializable(position_record)
                try:
                    position_insert = await db[POSITIONS_COLLECTION].insert_one(position_record)
                    position_record["_id"] = str(position_insert.inserted_id)
                    logger.info(f"Position created: {position_record['_id']} for {flow.symbol} ({side}) - Quantity: {position_quantity}, Price: {entry_price}")
                    
                    # Try to enqueue position monitoring task (optional - requires celery)
                    try:
                        from app.tasks.order_tasks import monitor_position_task
                        monitor_position_task.delay(position_record["_id"])
                        logger.debug(f"Position monitor task enqueued for {position_record['_id']}")
                    except ImportError:
                        # Celery not installed - monitoring will happen via other means
                        logger.debug("Celery not available - position monitoring will use alternative methods")
                    except Exception as e:
                        logger.warning(f"Failed to enqueue position monitor task: {e}")
                except Exception as e:
                    logger.error(f"CRITICAL: Failed to create position record: {e}")
                    logger.error(f"Position data: {position_record}")
                    raise Exception(f"Failed to create position: {e}")
            else:
                # This should NEVER happen with demo_force_position enabled
                if demo_force_position:
                    logger.error(f"CRITICAL: Position creation skipped despite demo_force_position=True!")
                    logger.error(f"position_quantity={position_quantity}, quantity={quantity}, order_size_usd={order_size_usd}, current_price={current_price}")
                    raise Exception("Position creation failed: demo_force_position enabled but position_quantity is 0")
                else:
                    logger.warning(f"Position creation skipped: position_quantity={position_quantity} (not forced)")

        # Complete execution
        completed_at = datetime.now(timezone.utc)
        duration = int((completed_at - execution.started_at).total_seconds() * 1000)
        
        result = ExecutionResult(
            action=final_action,
            confidence=final_confidence,
            reasoning=final_reasoning,
            position_id=position_record["_id"] if position_record else None,
        )
        
        # Complete risk validation step
        await update_execution(db, execution.id, {
            f"steps.{STEP_RISK_VALIDATION}.status": StepStatus.COMPLETED.value,
            f"steps.{STEP_RISK_VALIDATION}.completed_at": datetime.now(timezone.utc),
            f"steps.{STEP_RISK_VALIDATION}.data": risk_result,
        })
        
        # Heartbeat: Update lock expiration after risk validation
        await heartbeat_execution_lock(db, flow.id, str(execution.id))
        
        # Complete decision step
        await update_execution(db, execution.id, {
            f"steps.{STEP_DECISION}.status": StepStatus.RUNNING.value,
            f"steps.{STEP_DECISION}.started_at": datetime.now(timezone.utc),
        })
        
        order_payload = _to_response_payload(order_record) if order_record else None
        position_payload = _to_response_payload(position_record) if position_record else None
        await update_execution(db, execution.id, {
            "status": ExecutionStatus.COMPLETED.value,
            "completed_at": completed_at,
            "duration": duration,
            f"steps.{STEP_DECISION}.status": StepStatus.COMPLETED.value,
            f"steps.{STEP_DECISION}.completed_at": completed_at,
            "total_cost_usd": total_ai_cost_usd,
            f"steps.{STEP_DECISION}.data": {
                "final_action": final_action,
                "confidence": final_confidence,
                "order": order_payload,
                "position": position_payload,
                "force_position": demo_force_position,
                "ai_cost_usd": total_ai_cost_usd,
            },
            "result": result.model_dump(),
        })
        await _emit_execution_update(
            execution.id, flow.id, "COMPLETED", STEP_DECISION,
            "Placing Order on Exchange", 100, f"Trade {final_action.upper()} executed successfully", user_id
        )
        
        # Heartbeat: Update lock expiration after decision step
        await heartbeat_execution_lock(db, flow.id, str(execution.id))

        learning_record = {
            "user_id": _to_object_id((flow.config or {}).get("user_id")) or (flow.config or {}).get("user_id"),
            "flow_id": _to_object_id(execution.flow_id) or execution.flow_id,
            "execution_id": _to_object_id(execution.id) or execution.id,
            "symbol": flow.symbol,
            "action": final_action,
            "confidence": final_confidence,
            "status": ExecutionStatus.COMPLETED.value,
            "risk_score": risk_score,
            "risk_warning": risk_warning,
            "reasoning": final_reasoning,
            "order_id": order_record.get("_id") if order_record else None,
            "position_id": position_record.get("_id") if position_record else None,
            "market_summary": indicators.get("summary") if isinstance(indicators, dict) else None,
            "signal": signal_data,
            "started_at": execution.started_at,
            "completed_at": completed_at,
            "created_at": datetime.now(timezone.utc),
        }
        await db[LEARNING_OUTCOMES_COLLECTION].insert_one(_to_serializable(learning_record))
        
        # Update flow statistics with P&L analytics
        position_id_str = position_record.get("_id") if position_record else None
        await _update_flow_statistics(
            db=db,
            flow_id=flow.id,
            position_id=position_id_str,
            execution_completed=True,
            completed_at=completed_at,
        )

        await _schedule_auto_loop(db, flow, model_provider, model_name)
        # Return updated execution
        return await get_execution_by_id(db, execution.id)

    except Exception as e:
        logger.error(f"Flow execution failed: {str(e)}")

        failed_at = datetime.now(timezone.utc)
        # Safe fallback for execution_config in case exception occurs before it's defined
        execution_config = flow.config or {}

        # Mark execution as failed - mark all pending steps as failed
        await update_execution(db, execution.id, {
            "status": ExecutionStatus.FAILED.value,
            "completed_at": failed_at,
        })

        user_id = str((flow.config or {}).get("user_id") or (execution_config or {}).get("user_id"))
        await _emit_execution_update(
            execution.id, flow.id, "FAILED", STEP_DECISION,
            "Execution Failed", 0, f"Flow execution failed: {str(e)}", user_id
        )
        
        # Update any running/pending steps to failed (only on exception)
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
        
        # Re-raise after cleanup in finally block
        raise

    finally:
        # EXECUTION SAFEGUARD CLEANUP: Always release the lock
        # Only delete if lock matches this execution_id (prevents deleting wrong lock)
        try:
            lock_collection = "execution_locks"
            lock_id = f"flow_lock_{flow.id}"
            execution_id_str = str(execution.id) if execution else None
            
            if execution_id_str:
                # Atomic delete: only delete if execution_id matches
                delete_result = await db[lock_collection].delete_one({
                    "_id": lock_id,
                    "execution_id": execution_id_str  # Critical: verify ownership
                })
                
                if delete_result.deleted_count > 0:
                    logger.info(f"Released execution lock for flow {flow.id} (execution {execution.id})")
                else:
                    logger.warning(
                        f"Lock release failed: Lock {lock_id} doesn't match execution_id {execution_id_str} "
                        f"(may have been stolen or already released)"
                    )
            else:
                logger.error(f"Cannot release lock: execution.id is None")
                
        except Exception as cleanup_error:
            logger.error(f"Failed to release execution lock for flow {flow.id}: {cleanup_error}")
            # Don't raise - cleanup failure shouldn't break execution
        
        # Update flow statistics (always runs - success or failure)
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
