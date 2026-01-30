"""
Flow Router

API endpoints for flow management and execution.
No authentication required for demo.

Author: Moniqo Team
Last Updated: 2026-01-17
"""

from typing import Optional, Any
from fastapi import APIRouter, HTTPException, Query, Depends
from bson import ObjectId
from decimal import Decimal
from enum import Enum
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import db_provider
from app.core.dependencies import get_current_user_optional
from app.modules.flows.schemas import (
    FlowCreate,
    FlowUpdate,
    FlowResponse,
    FlowListResponse,
    ExecutionResponse,
    ExecutionListResponse,
    TriggerFlowRequest,
    AgentDecisionResponse,
)
from app.modules.flows.models import FlowStatus, ExecutionStatus
from app.modules.flows import service as flow_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/flows", tags=["Flows"])


def flow_to_response(flow) -> FlowResponse:
    """Convert Flow model to response"""
    return FlowResponse(
        id=str(flow.id),
        name=flow.name,
        symbol=flow.symbol,
        mode=flow.mode,
        trigger=flow.trigger,
        status=flow.status,
        agents=flow.agents,
        schedule=flow.schedule,
        config=flow.config,
        total_executions=flow.total_executions,
        successful_executions=flow.successful_executions,
        last_run_at=flow.last_run_at,
        created_at=flow.created_at,
        updated_at=flow.updated_at,
    )


def execution_to_response(execution) -> ExecutionResponse:
    """Convert Execution model to response"""
    from app.modules.flows.schemas import ExecutionStepResponse, ExecutionResultResponse
    
    def _serialize_data(data: Any) -> Any:
        """Serialize data for response, converting ObjectId and Decimal to JSON-serializable types"""
        if data is None:
            return None
        if isinstance(data, ObjectId):
            return str(data)
        if isinstance(data, Decimal):
            return float(data)
        if isinstance(data, Enum):
            return data.value
        if isinstance(data, dict):
            return {key: _serialize_data(val) for key, val in data.items()}
        if isinstance(data, (list, tuple)):
            return [_serialize_data(item) for item in data]
        return data
    
    steps = [
        ExecutionStepResponse(
            name=s.name,
            status=s.status,
            started_at=s.started_at,
            completed_at=s.completed_at,
            data=_serialize_data(s.data) if s.data else None,
            error=s.error,
        )
        for s in execution.steps
    ]
    
    result = None
    if execution.result:
        result = ExecutionResultResponse(
            action=execution.result.action,
            confidence=execution.result.confidence,
            reasoning=execution.result.reasoning,
            position_id=execution.result.position_id,
            rationale=execution.result.rationale,
            decision_trace=execution.result.decision_trace,
        )
    
    return ExecutionResponse(
        id=str(execution.id),
        flow_id=execution.flow_id,
        flow_name=execution.flow_name,
        status=execution.status,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        duration=execution.duration,
        steps=steps,
        result=result,
    )


# ==================== FLOW CRUD ====================

@router.post(
    "",
    response_model=FlowResponse,
    status_code=201,
    summary="Create flow",
    description="Create a new trading automation flow",
)
async def create_flow(
    flow_data: FlowCreate,
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db()),
):
    """Create a new flow"""
    try:
        flow = await flow_service.create_flow(db, flow_data)
        return flow_to_response(flow)
    except Exception as e:
        logger.error(f"Failed to create flow: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create flow: {str(e)}")


@router.get(
    "",
    response_model=FlowListResponse,
    summary="List flows",
    description="Get all trading flows with pagination",
)
async def list_flows(
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    status: Optional[FlowStatus] = Query(None, description="Filter by status"),
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db()),
):
    """List all flows"""
    try:
        flows, total = await flow_service.get_flows(db, limit, offset, status)
        
        return FlowListResponse(
            items=[flow_to_response(f) for f in flows],
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + len(flows) < total,
        )
    except Exception as e:
        logger.error(f"Failed to list flows: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list flows: {str(e)}")


@router.get(
    "/{flow_id}",
    response_model=FlowResponse,
    summary="Get flow",
    description="Get a specific flow by ID",
)
async def get_flow(
    flow_id: str,
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db()),
):
    """Get flow by ID"""
    flow = await flow_service.get_flow_by_id(db, flow_id)
    
    if not flow:
        raise HTTPException(status_code=404, detail=f"Flow not found: {flow_id}")
    
    return flow_to_response(flow)


@router.patch(
    "/{flow_id}",
    response_model=FlowResponse,
    summary="Update flow",
    description="Update a flow's configuration",
)
async def update_flow(
    flow_id: str,
    updates: FlowUpdate,
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db()),
):
    """Update flow"""
    existing = await flow_service.get_flow_by_id(db, flow_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Flow not found: {flow_id}")
    
    try:
        flow = await flow_service.update_flow(db, flow_id, updates)
        if not flow:
            raise HTTPException(status_code=500, detail="Failed to update flow")
        return flow_to_response(flow)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update flow: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update flow: {str(e)}")


@router.delete(
    "/{flow_id}",
    status_code=204,
    summary="Delete flow",
    description="Delete a flow",
)
async def delete_flow(
    flow_id: str,
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db()),
):
    """Delete flow"""
    existing = await flow_service.get_flow_by_id(db, flow_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Flow not found: {flow_id}")
    
    success = await flow_service.delete_flow(db, flow_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete flow")


# ==================== FLOW EXECUTION ====================

@router.post(
    "/{flow_id}/start",
    response_model=FlowResponse,
    summary="Start continuous trading",
    description="Start continuous trading flow - loops until manually stopped via /stop",
)
async def start_flow_endpoint(
    flow_id: str,
    trigger_request: Optional[TriggerFlowRequest] = None,
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db()),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """
    Start continuous trading flow.
    
    This will:
    1. Set flow status to ACTIVE
    2. Reset cycle counter
    3. Trigger first execution
    4. Continue looping automatically until stopped
    
    The flow will keep running through cycles:
    - Fetch market data
    - AI analysis (solo or swarm)
    - Risk checks
    - Execute trade (if approved)
    - Monitor position
    - Close position (SL/TP)
    - Loop back to start
    
    Use POST /flows/{flow_id}/stop to stop the continuous loop.
    """
    flow = await flow_service.get_flow_by_id(db, flow_id)
    
    if not flow:
        raise HTTPException(status_code=404, detail=f"Flow not found: {flow_id}")
    
    try:
        # Set user_id in flow config if authenticated user and not already set
        if current_user and not (flow.config or {}).get("user_id"):
            if not flow.config:
                flow.config = {}
            flow.config["user_id"] = str(current_user["_id"])
            # Update flow document
            await db[flow_service.FLOWS_COLLECTION].update_one(
                {"_id": ObjectId(flow.id)},
                {"$set": {"config.user_id": str(current_user["_id"])}}
            )
            logger.info(f"Set user_id in flow config: {current_user['_id']}")
            # Refresh flow to get updated config
            flow = await flow_service.get_flow_by_id(db, flow_id)
        
        model_provider = trigger_request.model_provider if trigger_request else "groq"
        model_name = trigger_request.model_name if trigger_request else None
        
        updated_flow = await flow_service.start_flow(
            db, flow_id, model_provider, model_name
        )
        
        if not updated_flow:
            raise HTTPException(status_code=500, detail="Failed to start flow")
        
        return flow_to_response(updated_flow)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start flow: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start flow: {str(e)}")


@router.post(
    "/{flow_id}/stop",
    response_model=FlowResponse,
    summary="Stop continuous trading",
    description="Stop continuous trading flow - breaks the auto-loop",
)
async def stop_flow_endpoint(
    flow_id: str,
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db()),
):
    """
    Stop continuous trading flow.
    
    This will:
    1. Set flow status to PAUSED
    2. Break the auto-loop (next cycle will not execute)
    
    Note: Any currently running execution will complete, but no new cycles will start.
    Use POST /flows/{flow_id}/start to restart the continuous loop.
    """
    flow = await flow_service.get_flow_by_id(db, flow_id)
    
    if not flow:
        raise HTTPException(status_code=404, detail=f"Flow not found: {flow_id}")
    
    try:
        updated_flow = await flow_service.stop_flow(db, flow_id)
        
        if not updated_flow:
            raise HTTPException(status_code=500, detail="Failed to stop flow")
        
        return flow_to_response(updated_flow)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop flow: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to stop flow: {str(e)}")


@router.post(
    "/{flow_id}/trigger",
    response_model=ExecutionResponse,
    summary="Trigger flow",
    description="Trigger a single flow execution with AI analysis (does not start continuous loop)",
)
async def trigger_flow(
    flow_id: str,
    trigger_request: Optional[TriggerFlowRequest] = None,
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db()),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """Trigger a single flow execution (use /start for continuous trading)"""
    flow = await flow_service.get_flow_by_id(db, flow_id)
    
    if not flow:
        raise HTTPException(status_code=404, detail=f"Flow not found: {flow_id}")
    
    if flow.status != FlowStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail=f"Flow is not active. Current status: {flow.status.value}"
        )
    
    try:
        # Set user_id in flow config if authenticated user and not already set
        if current_user and not (flow.config or {}).get("user_id"):
            if not flow.config:
                flow.config = {}
            flow.config["user_id"] = str(current_user["_id"])
            # Update flow document
            await db[flow_service.FLOWS_COLLECTION].update_one(
                {"_id": ObjectId(flow.id)},
                {"$set": {"config.user_id": str(current_user["_id"])}}
            )
            logger.info(f"Set user_id in flow config: {current_user['_id']}")
            # Refresh flow to get updated config
            flow = await flow_service.get_flow_by_id(db, flow_id)
        
        model_provider = trigger_request.model_provider if trigger_request else "groq"
        model_name = trigger_request.model_name if trigger_request else None
        
        execution = await flow_service.execute_flow(
            flow, model_provider, model_name
        )
        
        return execution_to_response(execution)
    except Exception as e:
        logger.error(f"Failed to execute flow: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Flow execution failed: {str(e)}")


@router.get(
    "/{flow_id}/executions",
    response_model=ExecutionListResponse,
    summary="Get flow executions",
    description="Get execution history for a flow",
)
async def get_flow_executions(
    flow_id: str,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db()),
):
    """Get executions for a flow"""
    flow = await flow_service.get_flow_by_id(db, flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail=f"Flow not found: {flow_id}")
    
    executions, total = await flow_service.get_executions(db, flow_id, limit, offset)
    
    return ExecutionListResponse(
        items=[execution_to_response(e) for e in executions],
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(executions) < total,
    )


# ==================== EXECUTIONS ====================

@router.get(
    "/executions/all",
    response_model=ExecutionListResponse,
    summary="List all executions",
    description="Get all executions across all flows",
)
async def list_all_executions(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db()),
):
    """List all executions"""
    executions, total = await flow_service.get_executions(db, None, limit, offset)
    
    return ExecutionListResponse(
        items=[execution_to_response(e) for e in executions],
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(executions) < total,
    )


@router.delete(
    "/executions/{execution_id}",
    status_code=204,
    summary="Delete execution",
    description="Delete a specific execution by ID",
)
async def delete_execution(
    execution_id: str,
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db()),
):
    """Delete execution by ID"""
    existing = await flow_service.get_execution_by_id(db, execution_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
    
    success = await flow_service.delete_execution(db, execution_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete execution")


@router.get(
    "/executions/{execution_id}",
    response_model=ExecutionResponse,
    summary="Get execution",
    description="Get a specific execution by ID",
)
async def get_execution(
    execution_id: str,
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db()),
):
    """Get execution by ID"""
    execution = await flow_service.get_execution_by_id(db, execution_id)
    
    if not execution:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
    
    return execution_to_response(execution)


@router.delete(
    "/executions",
    status_code=204,
    summary="Delete all executions",
    description="Delete all executions across all flows",
)
async def delete_all_executions(
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db()),
):
    """Delete all executions"""
    await flow_service.delete_all_executions(db)


# ==================== AGENT DECISIONS ====================

@router.get(
    "/agent-decisions/all",
    response_model=list[AgentDecisionResponse],
    summary="List agent decisions",
    description="Get all agent decisions",
)
async def list_agent_decisions(
    execution_id: Optional[str] = Query(None, description="Filter by execution ID"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db()),
):
    """List agent decisions"""
    decisions = await flow_service.get_agent_decisions(db, execution_id, limit)
    
    return [
        AgentDecisionResponse(
            id=str(d.id),
            executionId=d.execution_id,
            agentRole=d.agent_role,
            action=d.action,
            confidence=d.confidence,
            reasoning=d.reasoning,
            data=d.data,
            timestamp=d.timestamp,
        )
        for d in decisions
    ]


# ==================== SAFETY ENDPOINTS ====================

@router.post(
    "/emergency-stop",
    summary="Emergency Stop",
    description="Halt all active trading flows immediately",
)
async def emergency_stop(
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db()),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """
    Emergency stop all trading.
    
    This will:
    - Stop all active flows for the user
    - Set emergency_stop flag to prevent new trades
    - NOT close existing positions (manual action required)
    """
    from app.modules.risk_rules.circuit_breaker import get_circuit_breaker_service
    from bson import ObjectId
    from datetime import datetime, timezone
    
    try:
        user_id = str(current_user["_id"]) if current_user else None
        
        # Stop all active flows
        stopped_flows = []
        flows_collection = db.flows
        
        # Build query - filter by user if authenticated
        query = {"status": "active"}
        if user_id:
            query["$or"] = [
                {"config.user_id": user_id},
                {"config.user_id": ObjectId(user_id)},
            ]
        
        async for flow in flows_collection.find(query):
            flow_id = str(flow["_id"])
            await flow_service.stop_flow(db, flow_id)
            stopped_flows.append(flow_id)
            logger.warning(f"Emergency stop: stopped flow {flow_id}")
        
        # Set emergency stop flag in safety_status
        if user_id:
            now = datetime.now(timezone.utc)
            await db.safety_status.update_many(
                {"user_id": ObjectId(user_id)},
                {
                    "$set": {
                        "emergency_stop": True,
                        "emergency_stop_at": now,
                        "updated_at": now,
                    }
                }
            )
        
        logger.warning(
            f"Emergency stop activated: user={user_id}, "
            f"stopped_flows={len(stopped_flows)}"
        )
        
        return {
            "success": True,
            "message": "Emergency stop activated",
            "stopped_flows": stopped_flows,
            "stopped_count": len(stopped_flows),
        }
        
    except Exception as e:
        logger.error(f"Emergency stop failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Emergency stop failed: {str(e)}")


@router.post(
    "/emergency-reset",
    summary="Reset Emergency Stop",
    description="Reset emergency stop and allow trading to resume",
)
async def emergency_reset(
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db()),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """
    Reset emergency stop state.
    
    This will:
    - Clear emergency_stop flag
    - Reset circuit breaker
    - Clear cooldowns
    - Allow trading to resume
    """
    from app.modules.risk_rules.circuit_breaker import get_circuit_breaker_service
    from bson import ObjectId
    from datetime import datetime, timezone
    
    try:
        user_id = str(current_user["_id"]) if current_user else None
        
        if user_id:
            now = datetime.now(timezone.utc)
            
            # Reset all safety flags for user's wallets
            await db.safety_status.update_many(
                {"user_id": ObjectId(user_id)},
                {
                    "$set": {
                        "emergency_stop": False,
                        "emergency_stop_at": None,
                        "circuit_breaker_tripped": False,
                        "circuit_breaker_reason": None,
                        "circuit_breaker_until": None,
                        "consecutive_losses": 0,
                        "cooldown_until": None,
                        "cooldown_reason": None,
                        "updated_at": now,
                    }
                }
            )
        
        logger.info(f"Emergency stop reset: user={user_id}")
        
        return {
            "success": True,
            "message": "Emergency stop reset - trading can resume",
        }
        
    except Exception as e:
        logger.error(f"Emergency reset failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Emergency reset failed: {str(e)}")


@router.get(
    "/safety-status",
    summary="Get Safety Status",
    description="Get current safety status including circuit breaker, cooldown, and daily loss",
)
async def get_safety_status(
    wallet_id: Optional[str] = Query(None, description="Specific wallet ID (optional)"),
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db()),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """
    Get safety status for user's trading.
    
    Returns:
    - Emergency stop state
    - Circuit breaker status
    - Cooldown status
    - Daily P&L and loss limit status
    """
    from bson import ObjectId
    from datetime import datetime, timezone
    
    try:
        user_id = str(current_user["_id"]) if current_user else None
        
        # Default response for unauthenticated or no status
        default_status = {
            "emergency_stop": False,
            "emergency_stop_at": None,
            "circuit_breaker_tripped": False,
            "circuit_breaker_reason": None,
            "circuit_breaker_until": None,
            "consecutive_losses": 0,
            "cooldown_until": None,
            "cooldown_reason": None,
            "daily_pnl": 0.0,
            "daily_loss_limit": 100.0,
            "daily_loss_remaining": 100.0,
            "daily_trades": 0,
            "daily_wins": 0,
            "daily_losses": 0,
        }
        
        if not user_id:
            return default_status
        
        # Build query
        query = {"user_id": ObjectId(user_id)}
        if wallet_id:
            query["wallet_id"] = ObjectId(wallet_id)
        
        # Get first matching status (or aggregate across wallets)
        status = await db.safety_status.find_one(query)
        
        if not status:
            return default_status
        
        # Check daily reset
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        daily_reset_at = status.get("daily_reset_at")
        
        if not daily_reset_at or daily_reset_at < today_start:
            # Reset daily counters
            await db.safety_status.update_one(
                {"_id": status["_id"]},
                {
                    "$set": {
                        "daily_pnl": 0.0,
                        "daily_trades": 0,
                        "daily_wins": 0,
                        "daily_losses": 0,
                        "daily_reset_at": today_start,
                        "updated_at": now,
                    }
                }
            )
            status["daily_pnl"] = 0.0
            status["daily_trades"] = 0
            status["daily_wins"] = 0
            status["daily_losses"] = 0
        
        # Calculate daily loss remaining
        daily_pnl = status.get("daily_pnl", 0.0)
        daily_loss_limit = 100.0  # Default $100 limit
        current_loss = abs(min(0, daily_pnl))
        daily_loss_remaining = max(0, daily_loss_limit - current_loss)
        
        return {
            "emergency_stop": status.get("emergency_stop", False),
            "emergency_stop_at": status.get("emergency_stop_at"),
            "circuit_breaker_tripped": status.get("circuit_breaker_tripped", False),
            "circuit_breaker_reason": status.get("circuit_breaker_reason"),
            "circuit_breaker_until": status.get("circuit_breaker_until"),
            "consecutive_losses": status.get("consecutive_losses", 0),
            "cooldown_until": status.get("cooldown_until"),
            "cooldown_reason": status.get("cooldown_reason"),
            "daily_pnl": daily_pnl,
            "daily_loss_limit": daily_loss_limit,
            "daily_loss_remaining": daily_loss_remaining,
            "daily_trades": status.get("daily_trades", 0),
            "daily_wins": status.get("daily_wins", 0),
            "daily_losses": status.get("daily_losses", 0),
        }
        
    except Exception as e:
        logger.error(f"Get safety status failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get safety status: {str(e)}")
