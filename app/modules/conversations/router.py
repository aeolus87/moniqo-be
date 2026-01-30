"""
Conversations Router

API endpoints for swarm conversation logs.
No authentication required for demo.
"""

from typing import Optional, Dict, Set, Any
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timezone

from app.core.database import db_provider
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/conversations", tags=["Conversations"])
_subscribers: Dict[str, Set[WebSocket]] = {}


def _serialize_value(value: Any) -> Any:
    """Recursively serialize MongoDB types to JSON-compatible types"""
    if isinstance(value, ObjectId):
        return str(value)
    elif isinstance(value, datetime):
        return value.isoformat()
    elif isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_serialize_value(item) for item in value]
    return value


def _serialize_conversation(doc: dict) -> dict:
    """Serialize a conversation document for JSON response"""
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return _serialize_value(doc)


@router.get("/{execution_id}")
async def get_conversation(
    execution_id: str,
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db()),
):
    """Get conversation by execution id"""
    # Try string first, then ObjectId (for backward compatibility)
    doc = await db["ai_conversations"].find_one({"execution_id": execution_id})
    if not doc:
        try:
            doc = await db["ai_conversations"].find_one({"execution_id": ObjectId(execution_id)})
        except Exception:
            pass
    if not doc:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _serialize_conversation(doc)


@router.websocket("/ws/{execution_id}")
async def stream_conversation(websocket: WebSocket, execution_id: str):
    await websocket.accept()
    _subscribers.setdefault(execution_id, set()).add(websocket)
    logger.info(f"[Conversations WS] Client connected for execution: {execution_id}")

    try:
        db = db_provider.get_db()
        # Try string first, then ObjectId (for backward compatibility)
        doc = await db["ai_conversations"].find_one({"execution_id": execution_id})
        if not doc:
            try:
                doc = await db["ai_conversations"].find_one({"execution_id": ObjectId(execution_id)})
            except Exception:
                pass
        
        if doc:
            logger.info(f"[Conversations WS] Found conversation with {len(doc.get('messages', []))} messages")
            serialized = _serialize_conversation(doc)
            await websocket.send_json(serialized)
        else:
            logger.info(f"[Conversations WS] No conversation found, sending empty state")
            await websocket.send_json({"messages": [], "swarm_vote": None})

        # Keep connection alive
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info(f"[Conversations WS] Client disconnected: {execution_id}")
    except Exception as e:
        logger.error(f"[Conversations WS] Error: {e}")
        try:
            await websocket.close(code=1011, reason=str(e)[:120])
        except Exception:
            pass
    finally:
        _subscribers.get(execution_id, set()).discard(websocket)


@router.get("/{conversation_id}/voting")
async def get_voting_results(
    conversation_id: str,
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db()),
):
    """Get voting results for a conversation"""
    doc = await db["ai_conversations"].find_one({"_id": ObjectId(conversation_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {
        "id": str(doc["_id"]),
        "swarm_vote": doc.get("swarm_vote"),
    }


@router.post("/{conversation_id}/add-message")
async def add_message(
    conversation_id: str,
    agent_name: str,
    agent_role: str,
    content: dict,
    message_type: str = "analysis",
    vote: Optional[dict] = None,
    db: AsyncIOMotorDatabase = Depends(lambda: db_provider.get_db()),
):
    """Add a message to a conversation"""
    message = {
        "agent_name": agent_name,
        "agent_role": agent_role,
        "message_type": message_type,
        "content": content,
        "vote": vote or {},
        "timestamp": datetime.now(timezone.utc),
    }

    result = await db["ai_conversations"].update_one(
        {"_id": ObjectId(conversation_id)},
        {"$push": {"messages": message}, "$set": {"updated_at": datetime.now(timezone.utc)}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")

    doc = await db["ai_conversations"].find_one({"_id": ObjectId(conversation_id)})
    if doc:
        execution_id = doc.get("execution_id")
        # Also check string version of execution_id in subscribers
        exec_id_str = str(execution_id) if isinstance(execution_id, ObjectId) else execution_id
        subscriber_key = exec_id_str if exec_id_str in _subscribers else execution_id
        
        if subscriber_key and subscriber_key in _subscribers:
            serialized_message = _serialize_value(message)
            for ws in list(_subscribers[subscriber_key]):
                try:
                    await ws.send_json({"type": "message", "data": serialized_message})
                except Exception:
                    _subscribers[subscriber_key].discard(ws)
    return {"success": True}
