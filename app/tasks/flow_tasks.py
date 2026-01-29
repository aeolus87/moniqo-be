"""
Flow Tasks

Celery tasks for scheduled flow execution.

Author: Moniqo Team
Last Updated: 2026-01-17
"""

import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any

from celery import shared_task, Task
from croniter import croniter

from app.utils.logger import get_logger

logger = get_logger(__name__)


def _should_run_now(cron_expression: str) -> bool:
    """
    Check if a cron expression should trigger now (within the current minute).
    
    Args:
        cron_expression: Cron expression string (e.g., "*/5 * * * *")
        
    Returns:
        True if should run now, False otherwise
    """
    try:
        now = datetime.now(timezone.utc)
        cron = croniter(cron_expression, now)
        prev_run = cron.get_prev(datetime)
        
        # Ensure prev_run is timezone-aware and in UTC
        if prev_run.tzinfo is None:
            prev_run = prev_run.replace(tzinfo=timezone.utc)
        else:
            prev_run = prev_run.astimezone(timezone.utc)
        
        # Check if previous scheduled time is within the last 60 seconds
        diff = (now - prev_run).total_seconds()
        return diff < 60
    except Exception as e:
        logger.error(f"Invalid cron expression '{cron_expression}': {e}")
        return False


async def _get_scheduled_flows():
    """Get all active flows with schedule trigger type."""
    from app.config.database import get_database
    from app.modules.flows.models import FlowStatus, FlowTrigger
    
    db = get_database()
    
    cursor = db["flows"].find({
        "status": FlowStatus.ACTIVE.value,
        "trigger": FlowTrigger.SCHEDULE.value,
        "schedule": {"$ne": None, "$ne": ""}
    })
    
    flows = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        flows.append(doc)
    
    return flows


async def _trigger_flow(flow_id: str, model_provider: str = "groq"):
    """Trigger a single flow execution."""
    from app.config.database import get_database
    from app.modules.flows import service as flow_service
    
    db = get_database()
    
    flow = await flow_service.get_flow_by_id(db, flow_id)
    if not flow:
        logger.error(f"Flow not found: {flow_id}")
        return None
    
    logger.info(f"Triggering scheduled flow: {flow.name} ({flow_id})")
    
    try:
        execution = await flow_service.execute_flow(db, flow, model_provider)
        logger.info(f"Scheduled flow execution completed: {execution.id}")
        return execution
    except Exception as e:
        logger.error(f"Scheduled flow execution failed: {flow_id} - {e}")
        return None


@shared_task(name="app.tasks.flow_tasks.trigger_scheduled_flows_task")
def trigger_scheduled_flows_task():
    """
    Check and trigger all scheduled flows that should run now.
    
    This task runs every minute via Celery beat.
    """
    logger.info("Checking scheduled flows...")
    
    async def run():
        flows = await _get_scheduled_flows()
        triggered_count = 0
        
        for flow_doc in flows:
            flow_id = flow_doc["_id"]
            schedule = flow_doc.get("schedule")
            
            if not schedule:
                continue
            
            if _should_run_now(schedule):
                logger.info(f"Triggering flow {flow_doc.get('name')} - schedule: {schedule}")
                await _trigger_flow(flow_id)
                triggered_count += 1
        
        logger.info(f"Scheduled flows check complete. Triggered: {triggered_count}")
        return triggered_count
    
    # Run async code in sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(run())
    finally:
        loop.close()


@shared_task(name="app.tasks.flow_tasks.execute_flow_task")
def execute_flow_task(flow_id: str, model_provider: str = "groq", model_name: str = None):
    """
    Execute a single flow (can be triggered manually or by scheduler).
    
    Args:
        flow_id: Flow ID to execute
        model_provider: AI model provider
        model_name: Specific model name (optional)
    """
    logger.info(f"Executing flow task: {flow_id}")
    
    async def run():
        from app.config.database import get_database
        from app.modules.flows import service as flow_service
        
        db = get_database()
        flow = await flow_service.get_flow_by_id(db, flow_id)
        
        if not flow:
            logger.error(f"Flow not found: {flow_id}")
            return None
        
        execution = await flow_service.execute_flow(db, flow, model_provider, model_name)
        return str(execution.id) if execution else None
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(run())
    finally:
        loop.close()


@shared_task(name="app.tasks.flow_tasks.heartbeat_running_executions_task", bind=True)
def heartbeat_running_executions_task(self: Task) -> Dict[str, Any]:
    """
    Periodic task to send heartbeat for all running executions.
    
    Runs every 5 minutes via Celery beat.
    Updates lock expiration for active executions.
    """
    async def heartbeat_all():
        from app.config.database import get_database
        from app.modules.flows.models import ExecutionStatus
        from app.modules.flows.service import heartbeat_execution_lock
        
        db = get_database()
        
        # Find all running executions
        running_executions = await db["executions"].find({
            "status": ExecutionStatus.RUNNING.value,
            "deleted_at": None
        }).to_list(length=None)
        
        heartbeat_count = 0
        failed_count = 0
        
        for exec_doc in running_executions:
            flow_id = exec_doc.get("flow_id")
            execution_id = str(exec_doc.get("_id"))
            
            if flow_id:
                success = await heartbeat_execution_lock(db, str(flow_id), execution_id)
                if success:
                    heartbeat_count += 1
                else:
                    failed_count += 1
        
        return {
            "success": True,
            "heartbeat_count": heartbeat_count,
            "failed_count": failed_count,
            "total_running": len(running_executions)
        }
    
    # Run async code
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(heartbeat_all())
    finally:
        loop.close()
