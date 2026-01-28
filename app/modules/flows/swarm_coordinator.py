"""
Swarm Coordinator Service

Handles AI agent coordination, parallel analysis, and swarm voting.

Author: Moniqo Team
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import asyncio
import time
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.flows.models import Flow, Execution, AgentDecision, StepName
from app.modules.ai_agents.market_analyst_agent import MarketAnalystAgent
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Collection names
AI_CONVERSATIONS_COLLECTION = "ai_conversations"
AI_DECISIONS_LOG_COLLECTION = "ai_decisions_log"


def usage_delta(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    """Compute per-call token usage deltas from model info snapshots."""
    return {
        "input_tokens": max(0, int(after.get("total_input_tokens", 0)) - int(before.get("total_input_tokens", 0))),
        "output_tokens": max(0, int(after.get("total_output_tokens", 0)) - int(before.get("total_output_tokens", 0))),
        "cost_usd": max(0.0, float(after.get("total_cost_usd", 0.0)) - float(before.get("total_cost_usd", 0.0))),
        "model_provider": after.get("provider") or before.get("provider"),
        "model_name": after.get("model_name") or before.get("model_name"),
    }


def aggregate_usage(usages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate token usage across multiple agent calls."""
    if not usages:
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
            "model_provider": None,
            "model_name": None,
        }

    return {
        "input_tokens": sum(u.get("input_tokens", 0) for u in usages),
        "output_tokens": sum(u.get("output_tokens", 0) for u in usages),
        "cost_usd": sum(u.get("cost_usd", 0.0) for u in usages),
        "model_provider": usages[0].get("model_provider"),
        "model_name": usages[0].get("model_name"),
    }


def aggregate_swarm_results(
    results: List[Dict[str, Any]],
    role_weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Aggregate swarm analyst results into a single decision."""
    members = []
    role_weights = role_weights or {}
    for result in results:
        if not result:
            continue
        action = result.get("action") or "hold"
        confidence = float(result.get("confidence") or 0)
        role = result.get("role") or "market_analyst"
        weight = float(role_weights.get(role, 1.0)) * confidence
        members.append({
            "action": action,
            "confidence": confidence,
            "reasoning": result.get("reasoning", ""),
            "role": role,
            "weight": weight,
            "raw": result,
        })

    if not members:
        return {
            "action": "hold",
            "confidence": 0.0,
            "reasoning": "No valid swarm results.",
            "members": [],
            "votes": {},
            "agreement": 0,
            "is_unanimous": False,
        }

    counts: Dict[str, int] = {}
    confidence_map: Dict[str, List[float]] = {}
    weighted_confidence: Dict[str, float] = {}
    for member in members:
        action = member["action"]
        counts[action] = counts.get(action, 0) + 1
        confidence_map.setdefault(action, []).append(member["confidence"])
        weighted_confidence[action] = weighted_confidence.get(action, 0.0) + member["weight"]

    ranked = sorted(
        counts.items(),
        key=lambda item: (item[1], weighted_confidence.get(item[0], 0.0)),
        reverse=True,
    )
    top_action = ranked[0][0]
    total_weight = sum(weighted_confidence.values()) or 1.0
    avg_confidence = weighted_confidence[top_action] / total_weight
    total_votes = len(members)
    agreement = int((counts[top_action] / total_votes) * 100)
    reasoning = (
        f"Swarm consensus: {top_action} "
        f"({counts[top_action]}/{len(members)}) with avg confidence {avg_confidence:.2f}."
    )

    return {
        "action": top_action,
        "confidence": round(avg_confidence, 4),
        "reasoning": reasoning,
        "members": members,
        "votes": {
            action: {
                "count": counts[action],
                "total_confidence": sum(confidence_map[action]),
                "weighted_confidence": weighted_confidence.get(action, 0.0),
            }
            for action in counts
        },
        "agreement": agreement,
        "is_unanimous": counts[top_action] == total_votes,
    }


async def run_solo_analysis(
    analysis_context: Dict[str, Any],
    model_provider: str,
    model_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run single agent market analysis.
    
    Returns:
        Analysis result dict with action, confidence, reasoning, and usage
    """
    market_analyst = MarketAnalystAgent(
        model_provider=model_provider,
        model_name=model_name,
    )
    before = market_analyst.model.get_model_info()
    start = time.perf_counter()
    result = await market_analyst.process(analysis_context)
    duration_ms = int((time.perf_counter() - start) * 1000)
    after = market_analyst.model.get_model_info()
    usage = usage_delta(before, after)
    
    return {
        "result": result,
        "usage": usage,
        "duration_ms": duration_ms,
        "agent": market_analyst,
    }


async def run_swarm_analysis(
    analysis_context: Dict[str, Any],
    swarm_runs: int,
    model_provider: str,
    model_name: Optional[str] = None,
    role_weights: Optional[Dict[str, float]] = None,
    min_agreement: int = 50,
) -> Dict[str, Any]:
    """
    Run parallel swarm market analysis with voting.
    
    Args:
        analysis_context: Market data and indicators
        swarm_runs: Number of parallel agents to run
        model_provider: AI model provider
        model_name: Specific model name
        role_weights: Weight per agent role for voting
        min_agreement: Minimum agreement percentage for consensus
        
    Returns:
        Aggregated swarm result with consensus decision
    """
    role_weights = role_weights or {"market_analyst": 1.0}
    
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
        usage = usage_delta(before, after)
        return {
            "result": result,
            "role": "market_analyst",
            "usage": usage,
            "duration_ms": duration_ms,
        }

    swarm_results = await asyncio.gather(*[run_swarm_member() for _ in range(swarm_runs)])
    swarm_usage = aggregate_usage([r["usage"] for r in swarm_results])
    swarm_aggregate = aggregate_swarm_results(
        [
            {**r["result"], "role": r["role"]}
            for r in swarm_results
        ],
        role_weights=role_weights,
    )
    
    # Check agreement threshold
    if swarm_aggregate["agreement"] < min_agreement:
        swarm_aggregate["action"] = "hold"
        swarm_aggregate["reasoning"] = (
            f"Swarm agreement {swarm_aggregate['agreement']}% below "
            f"minimum {min_agreement}%."
        )
    
    return {
        "results": swarm_results,
        "aggregate": swarm_aggregate,
        "usage": swarm_usage,
        "avg_duration_ms": int(sum(r["duration_ms"] for r in swarm_results) / swarm_runs),
    }


async def create_conversation_log(
    db: AsyncIOMotorDatabase,
    flow: Flow,
    execution: Execution,
    swarm_results: List[Dict[str, Any]],
    swarm_aggregate: Dict[str, Any],
    usage: Dict[str, Any],
    role_weights: Dict[str, float],
) -> str:
    """
    Create AI conversation log for swarm analysis.
    
    Returns:
        Inserted conversation ID
    """
    result = await db[AI_CONVERSATIONS_COLLECTION].insert_one({
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
                "ai_model": usage.get("model_name"),
                "message_type": "vote",
                "content": {
                    "text": r["result"].get("reasoning", ""),
                    "confidence": int((r["result"].get("confidence") or 0) * 100),
                    "sentiment": "bullish" if r["result"].get("action") == "buy" else (
                        "bearish" if r["result"].get("action") == "sell" else "neutral"
                    ),
                    "data": r["result"],
                },
                "vote": {
                    "action": r["result"].get("action"),
                    "confidence": int((r["result"].get("confidence") or 0) * 100),
                    "weight": int((r["result"].get("confidence") or 0) * 100 * role_weights.get("market_analyst", 1.0)),
                },
                "timestamp": datetime.now(timezone.utc),
                "ui": {
                    "tone": "neutral",
                    "icon": "activity",
                    "color": "blue",
                },
            }
            for idx, r in enumerate(swarm_results)
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
    
    return str(result.inserted_id)


async def log_agent_decision(
    db: AsyncIOMotorDatabase,
    flow: Flow,
    execution: Execution,
    agent_role: str,
    result: Dict[str, Any],
    usage: Dict[str, Any],
    duration_ms: int,
    context: Dict[str, Any],
    decision_type: str = "market_analysis",
    step: str = None,
) -> str:
    """
    Log agent decision to AI decisions log.
    
    Returns:
        Inserted log ID
    """
    step = step or StepName.MARKET_ANALYSIS.value
    
    log_result = await db[AI_DECISIONS_LOG_COLLECTION].insert_one({
        "user_id": (flow.config or {}).get("user_id"),
        "flow_id": execution.flow_id,
        "agent_role": agent_role,
        "model_provider": usage.get("model_provider"),
        "model_name": usage.get("model_name"),
        "decision_type": decision_type,
        "step": step,
        "input_context": context,
        "ai_response": result,
        "prompt_used": None,
        "system_prompt_used": None,
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "cost_usd": usage.get("cost_usd", 0.0),
        "success": True,
        "error_message": None,
        "timestamp": datetime.now(timezone.utc),
        "execution_time_ms": duration_ms,
        "metadata": {
            "execution_id": execution.id,
        },
    })
    
    return str(log_result.inserted_id)
