"""
Conversations Router

API endpoints for swarm conversation logs.
No authentication required for demo.
"""

from typing import Optional, Dict, Set
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timezone

from app.config.database import get_database
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/conversations", tags=["Conversations"])
_subscribers: Dict[str, Set[WebSocket]] = {}


def _serialize_conversation(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


@router.get("/{execution_id}")
async def get_conversation(
    execution_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Get conversation by execution id"""
    doc = await db["ai_conversations"].find_one({"execution_id": execution_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _serialize_conversation(doc)


@router.websocket("/ws/{execution_id}")
async def stream_conversation(websocket: WebSocket, execution_id: str):
    await websocket.accept()
    _subscribers.setdefault(execution_id, set()).add(websocket)

    try:
        db = await get_database()
        doc = await db["ai_conversations"].find_one({"execution_id": execution_id})
        if doc:
            await websocket.send_json(_serialize_conversation(doc))

        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _subscribers.get(execution_id, set()).discard(websocket)


@router.get("/{conversation_id}/voting")
async def get_voting_results(
    conversation_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
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
    db: AsyncIOMotorDatabase = Depends(get_database),
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
        if execution_id and execution_id in _subscribers:
            for ws in list(_subscribers[execution_id]):
                try:
                    await ws.send_json({"type": "message", "data": message})
                except Exception:
                    _subscribers[execution_id].discard(ws)
    return {"success": True}
