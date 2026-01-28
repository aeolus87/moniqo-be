"""
Flow Statistics Service

Handles flow statistics updates including P&L, win rate, and execution counts.

Author: Moniqo Team
"""

from typing import Optional
from datetime import datetime, timezone
from decimal import Decimal
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Collection names
FLOWS_COLLECTION = "flows"
POSITIONS_COLLECTION = "positions"


async def update_flow_statistics(
    db: AsyncIOMotorDatabase,
    flow_id: str,
    position_id: Optional[str] = None,
    execution_completed: bool = True,
    completed_at: Optional[datetime] = None,
    increment_executions: bool = True,
) -> None:
    """
    Update flow statistics with P&L analytics.
    
    This function implements the UpdateFlowStats step from the flowchart.
    It atomically updates flow statistics including:
    - total_executions count (if increment_executions=True)
    - successful_executions count (if increment_executions=True)
    - total_pnl_usd (from closed positions)
    - total_pnl_percent (average P&L percentage)
    - win_rate (percentage of profitable trades)
    
    Args:
        db: Database instance
        flow_id: Flow ID
        position_id: Optional position ID to fetch realized P&L from
        execution_completed: Whether execution completed successfully
        completed_at: Completion timestamp
        increment_executions: Whether to increment execution counts (False when called from position close)
    """
    try:
        completed_at = completed_at or datetime.now(timezone.utc)
        flow_obj_id = ObjectId(flow_id)
        
        # Fetch realized P&L from position if provided
        realized_pnl_usd = Decimal("0")
        realized_pnl_percent = Decimal("0")
        is_profitable = False
        
        if position_id:
            try:
                position_doc = await db[POSITIONS_COLLECTION].find_one({
                    "_id": ObjectId(position_id),
                    "flow_id": flow_obj_id,
                })
                
                if position_doc and position_doc.get("exit"):
                    exit_data = position_doc.get("exit", {})
                    realized_pnl_usd = Decimal(str(exit_data.get("realized_pnl", 0)))
                    realized_pnl_percent = Decimal(str(exit_data.get("realized_pnl_percent", 0)))
                    is_profitable = float(realized_pnl_usd) > 0
                    logger.debug(f"Fetched P&L from position {position_id}: ${realized_pnl_usd}, {realized_pnl_percent}%")
            except Exception as e:
                logger.warning(f"Failed to fetch P&L from position {position_id}: {e}")
        
        # Get current flow stats for win_rate calculation
        flow_doc = await db[FLOWS_COLLECTION].find_one({"_id": flow_obj_id})
        if not flow_doc:
            logger.warning(f"Flow {flow_id} not found for stats update")
            return
        
        current_total_executions = flow_doc.get("total_executions", 0)
        current_successful_executions = flow_doc.get("successful_executions", 0)
        current_total_pnl_usd = Decimal(str(flow_doc.get("total_pnl_usd", 0)))
        current_winning_trades = flow_doc.get("winning_trades", 0)
        
        # Prepare update operations
        update_ops = {
            "$set": {
                "last_run_at": completed_at,
                "updated_at": completed_at,
            }
        }
        
        # Only increment execution counts if requested (not when called from position close)
        if increment_executions:
            update_ops["$inc"] = {
                "total_executions": 1,
            }
            if execution_completed:
                update_ops["$inc"]["successful_executions"] = 1
        else:
            update_ops["$inc"] = {}
        
        # Add P&L if position was closed
        if position_id and realized_pnl_usd != 0:
            update_ops["$inc"]["total_pnl_usd"] = float(realized_pnl_usd)
            
            # Track winning trades for win_rate calculation
            if is_profitable:
                update_ops["$inc"]["winning_trades"] = 1
            
            # Calculate new total P&L percent (weighted average)
            new_total_pnl_usd = current_total_pnl_usd + realized_pnl_usd
            new_total_executions = current_total_executions + 1
            
            if new_total_executions > 0:
                # For now, use the latest position's P&L percent as a proxy
                update_ops["$set"]["total_pnl_percent"] = float(realized_pnl_percent)
        
        # Calculate win_rate
        if increment_executions:
            new_successful_executions = current_successful_executions + (1 if execution_completed else 0)
            new_winning_trades = current_winning_trades + (1 if (is_profitable and execution_completed) else 0)
        else:
            # Position close: execution was already counted, just update winning trades if profitable
            new_successful_executions = current_successful_executions
            new_winning_trades = current_winning_trades + (1 if is_profitable else 0)
            if is_profitable:
                update_ops["$inc"]["winning_trades"] = 1
        
        if new_successful_executions > 0:
            win_rate = (new_winning_trades / new_successful_executions) * 100.0
            update_ops["$set"]["win_rate"] = round(win_rate, 2)
        else:
            update_ops["$set"]["win_rate"] = 0.0
        
        # Atomic update
        await db[FLOWS_COLLECTION].update_one(
            {"_id": flow_obj_id},
            update_ops
        )
        
        new_total_executions = current_total_executions + (1 if increment_executions else 0)
        new_total_pnl = current_total_pnl_usd + realized_pnl_usd
        
        logger.info(
            f"Updated flow {flow_id} stats: "
            f"executions={new_total_executions}, "
            f"successful={new_successful_executions}, "
            f"PnL=${float(new_total_pnl):.2f}, "
            f"win_rate={update_ops['$set'].get('win_rate', 0):.2f}%"
        )
        
    except Exception as e:
        logger.error(f"Failed to update flow statistics for {flow_id}: {e}")
