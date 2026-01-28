"""
Flow Execution Orchestrator

Main orchestration logic for executing trading flows.
Coordinates data aggregation, AI analysis, risk management, and trade execution.

Author: Moniqo Team
"""

from typing import Optional, Tuple
from datetime import datetime, timezone
import asyncio
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.flows.models import (
    Flow,
    Execution,
    FlowStatus,
    FlowMode,
)
from app.utils.logger import get_logger

# Import from our refactored services
from app.modules.flows.execution_service import (
    create_execution,
    get_execution_by_id,
    update_execution,
)
from app.modules.flows.execution_lock import (
    acquire_execution_lock,
    heartbeat_execution_lock,
    release_execution_lock,
)
from app.modules.flows.statistics import update_flow_statistics

logger = get_logger(__name__)

# Collection names
FLOWS_COLLECTION = "flows"


async def emit_execution_update(
    execution_id: str,
    flow_id: str,
    status: str,
    current_step: int,
    step_name: str,
    progress_percent: int,
    message: str = "",
    user_id: str = None
):
    """Emit execution update via Socket.IO to notify frontend of progress."""
    try:
        # Import here to avoid circular imports
        from app.main import sio

        # Emit to user's positions room if user_id is provided, otherwise emit globally
        room = f'positions:{user_id}' if user_id else f'executions:{execution_id}'

        await sio.emit('execution_update', {
            'execution_id': execution_id,
            'flow_id': flow_id,
            'status': status,
            'current_step': current_step,
            'step_name': step_name,
            'progress_percent': progress_percent,
            'message': message
        }, room=room)
        logger.debug(f"Emitted execution_update for execution {execution_id}: step {current_step} ({progress_percent}%) to room {room}")
    except Exception as e:
        logger.warning(f"Failed to emit execution update: {e}")


def get_auto_loop_settings(flow: Flow) -> Tuple[bool, int, Optional[int]]:
    """Extract auto-loop configuration from flow config."""
    config = flow.config or {}
    enabled = bool(config.get("auto_loop_enabled", True))
    delay_seconds = int(config.get("auto_loop_delay_seconds", 30))
    if delay_seconds <= 0:
        delay_seconds = 5
    max_cycles = config.get("auto_loop_max_cycles")
    if max_cycles is not None:
        try:
            max_cycles = int(max_cycles)
        except (TypeError, ValueError):
            max_cycles = None
    return enabled, delay_seconds, max_cycles


async def schedule_auto_loop(
    db: AsyncIOMotorDatabase,
    flow: Flow,
    model_provider: str,
    model_name: Optional[str],
) -> None:
    """
    Schedule the next iteration of the continuous trading loop.
    
    This implements the EndCycle --> WaitTrigger loop from the flowchart.
    """
    # Import here to avoid circular imports
    from app.modules.flows.service import get_flow_by_id, execute_flow
    
    enabled, delay_seconds, max_cycles = get_auto_loop_settings(flow)
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
                    await schedule_auto_loop(db, refreshed, model_provider, model_name)
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


# Re-export functions from the main service for backward compatibility
# The actual execute_flow implementation remains in service.py for now
# due to its complexity and tight coupling with execution state management
