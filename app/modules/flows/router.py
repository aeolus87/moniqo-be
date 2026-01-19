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

from app.config.database import get_database
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


def _to_response_payload(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _to_response_payload(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_response_payload(item) for item in value]
    return value


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
    
    steps = [
        ExecutionStepResponse(
            name=s.name,
            status=s.status,
            started_at=s.started_at,
            completed_at=s.completed_at,
            data=_to_response_payload(s.data),
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
    db: AsyncIOMotorDatabase = Depends(get_database),
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
    db: AsyncIOMotorDatabase = Depends(get_database),
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
    db: AsyncIOMotorDatabase = Depends(get_database),
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
    db: AsyncIOMotorDatabase = Depends(get_database),
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
    db: AsyncIOMotorDatabase = Depends(get_database),
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
    db: AsyncIOMotorDatabase = Depends(get_database),
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
    db: AsyncIOMotorDatabase = Depends(get_database),
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
    db: AsyncIOMotorDatabase = Depends(get_database),
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
            db, flow, model_provider, model_name
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
    db: AsyncIOMotorDatabase = Depends(get_database),
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
    db: AsyncIOMotorDatabase = Depends(get_database),
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
    db: AsyncIOMotorDatabase = Depends(get_database),
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
    db: AsyncIOMotorDatabase = Depends(get_database),
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
    db: AsyncIOMotorDatabase = Depends(get_database),
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
    db: AsyncIOMotorDatabase = Depends(get_database),
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
