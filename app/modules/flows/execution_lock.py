"""
Execution Lock Service

Manages execution locks to prevent duplicate flow executions.

Author: Moniqo Team
"""

from typing import Dict, Any
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.flows.models import ExecutionStatus
from app.modules.flows.utils import to_object_id
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Collection names
EXECUTIONS_COLLECTION = "executions"
LOCK_COLLECTION = "execution_locks"


async def acquire_execution_lock(
    db: AsyncIOMotorDatabase,
    flow_id: str,
    execution_id: str
) -> bool:
    """
    Atomically acquire execution lock using find_one_and_update.
    
    Returns:
        True if lock acquired, False if already locked
    """
    lock_id = f"flow_lock_{flow_id}"
    
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=30)
    
    # Check if lock exists and is not expired
    existing_lock = await db[LOCK_COLLECTION].find_one({"_id": lock_id})
    if existing_lock:
        lock_expires = existing_lock.get("expires_at")
        if lock_expires and isinstance(lock_expires, datetime):
            # Ensure timezone-aware comparison
            if lock_expires.tzinfo is None:
                lock_expires = lock_expires.replace(tzinfo=timezone.utc)
            if lock_expires >= now:
                # Lock exists and is not expired
                logger.debug(f"Lock {lock_id} exists and is not expired (expires at {lock_expires})")
                return False
    
    # Lock doesn't exist or is expired - try to acquire it
    if existing_lock:
        # Update expired lock
        update_result = await db[LOCK_COLLECTION].update_one(
            {
                "_id": lock_id,
                "$or": [
                    {"expires_at": {"$lt": now}},
                    {"expires_at": {"$exists": False}}
                ]
            },
            {
                "$set": {
                    "flow_id": to_object_id(flow_id) or flow_id,
                    "execution_id": execution_id,
                    "acquired_at": now,
                    "expires_at": expires_at,
                    "last_heartbeat": now
                }
            }
        )
        if update_result.modified_count > 0:
            return True
    else:
        # Lock doesn't exist - create it
        try:
            await db[LOCK_COLLECTION].insert_one({
                "_id": lock_id,
                "flow_id": to_object_id(flow_id) or flow_id,
                "execution_id": execution_id,
                "acquired_at": now,
                "expires_at": expires_at,
                "last_heartbeat": now
            })
            return True
        except Exception as e:
            # Another process created the lock between our check and insert
            if "duplicate key" in str(e).lower() or "E11000" in str(e):
                logger.debug(f"Lock {lock_id} was created by another process")
                return False
            raise
    
    # If we get here, lock exists but update didn't match (race condition)
    # Check again if it's still expired
    final_check = await db[LOCK_COLLECTION].find_one({"_id": lock_id})
    if final_check:
        lock_expires = final_check.get("expires_at")
        if lock_expires and isinstance(lock_expires, datetime):
            if lock_expires.tzinfo is None:
                lock_expires = lock_expires.replace(tzinfo=timezone.utc)
            if lock_expires >= now:
                return False
    
    return False


async def release_execution_lock(
    db: AsyncIOMotorDatabase,
    flow_id: str,
    execution_id: str
) -> bool:
    """
    Release execution lock.
    
    Returns:
        True if lock released, False if lock doesn't match execution_id
    """
    lock_id = f"flow_lock_{flow_id}"
    
    # Only delete if lock matches this execution_id
    result = await db[LOCK_COLLECTION].delete_one({
        "_id": lock_id,
        "execution_id": execution_id
    })
    
    return result.deleted_count > 0


async def heartbeat_execution_lock(
    db: AsyncIOMotorDatabase,
    flow_id: str,
    execution_id: str
) -> bool:
    """
    Update lock expiration time (heartbeat).
    
    Returns:
        True if heartbeat successful, False if lock doesn't match execution_id
    """
    lock_id = f"flow_lock_{flow_id}"
    
    now = datetime.now(timezone.utc)
    new_expires_at = now + timedelta(minutes=30)
    
    # Only update if lock matches this execution_id (prevents stealing)
    result = await db[LOCK_COLLECTION].update_one(
        {
            "_id": lock_id,
            "execution_id": execution_id  # Critical: verify ownership
        },
        {
            "$set": {
                "expires_at": new_expires_at,
                "last_heartbeat": now
            }
        }
    )
    
    return result.modified_count > 0


async def recover_stuck_executions(db: AsyncIOMotorDatabase) -> Dict[str, Any]:
    """
    Recover stuck executions on system startup.
    
    Finds executions in RUNNING status with expired locks
    and marks them as FAILED.
    
    Returns:
        Dict with recovery statistics
    """
    now = datetime.now(timezone.utc)
    
    # Find all expired locks
    expired_locks = await db[LOCK_COLLECTION].find({
        "expires_at": {"$lt": now}
    }).to_list(length=None)
    
    recovered_count = 0
    
    for lock in expired_locks:
        flow_id = lock.get("flow_id")
        execution_id = lock.get("execution_id")
        
        if execution_id:
            # Check if execution is still RUNNING
            execution = await db[EXECUTIONS_COLLECTION].find_one({
                "_id": ObjectId(execution_id),
                "status": ExecutionStatus.RUNNING.value
            })
            
            if execution:
                # Mark execution as failed
                await db[EXECUTIONS_COLLECTION].update_one(
                    {"_id": ObjectId(execution_id)},
                    {
                        "$set": {
                            "status": ExecutionStatus.FAILED.value,
                            "completed_at": now,
                            "error": "Execution marked as stuck: Lock expired (System Restart/Stall)"
                        }
                    }
                )
                
                # Clean up lock
                await db[LOCK_COLLECTION].delete_one({"_id": lock["_id"]})
                recovered_count += 1
                logger.info(f"Recovered stuck execution {execution_id} for flow {flow_id}")
    
    # Also check for RUNNING executions without locks (orphaned)
    running_executions = await db[EXECUTIONS_COLLECTION].find({
        "status": ExecutionStatus.RUNNING.value,
        "deleted_at": None
    }).to_list(length=None)
    
    orphaned_count = 0
    for exec_doc in running_executions:
        flow_id = exec_doc.get("flow_id")
        execution_id = str(exec_doc.get("_id"))
        lock_id = f"flow_lock_{flow_id}"
        
        # Check if lock exists
        lock = await db[LOCK_COLLECTION].find_one({"_id": lock_id})
        
        if not lock:
            # Orphaned execution - mark as failed
            await db[EXECUTIONS_COLLECTION].update_one(
                {"_id": ObjectId(execution_id)},
                {
                    "$set": {
                        "status": ExecutionStatus.FAILED.value,
                        "completed_at": now,
                        "error": "Execution marked as stuck: No lock found (Orphaned execution)"
                    }
                }
            )
            orphaned_count += 1
            logger.info(f"Recovered orphaned execution {execution_id} for flow {flow_id}")
    
    return {
        "recovered_expired": recovered_count,
        "recovered_orphaned": orphaned_count,
        "total_recovered": recovered_count + orphaned_count
    }
