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
    risk_manager_veto: Optional[Dict[str, Any]] = None,
    min_confidence_threshold: float = 0.70,
) -> Dict[str, Any]:
    """
    Aggregate swarm analyst results into a single decision.
    
    INSTITUTIONAL GRADE: Role-Based Consensus with Risk Manager Veto Power
    
    Args:
        results: List of agent results
        role_weights: Weight per role (default: market_analyst=1.0, risk_manager=2.0 for veto)
        risk_manager_veto: Risk manager assessment dict with 'approved' boolean
        min_confidence_threshold: Minimum weighted confidence to execute (default: 0.70)
        
    Returns:
        Aggregated decision with veto status and full trace
    """
    members = []
    role_weights = role_weights or {}
    
    # Default role weights (Risk Manager has higher weight for veto power)
    default_weights = {
        "market_analyst": 1.0,
        "sentiment_analyst": 1.0,
        "risk_manager": 2.0,  # Veto power through higher weight
        "executor": 0.5,  # Executor follows consensus
    }
    
    # Merge with provided weights
    for role, weight in default_weights.items():
        if role not in role_weights:
            role_weights[role] = weight
    
    # Process all results
    risk_manager_result = None
    leverage_values = []  # Collect leverage values for aggregation
    position_size_usd_values = []  # Collect position size values for aggregation
    position_size_percent_values = []  # Collect position size percent values for aggregation
    
    for result in results:
        if not result:
            continue
        action = result.get("action") or "hold"
        confidence = float(result.get("confidence") or 0)
        role = result.get("role") or "market_analyst"
        
        # Track Risk Manager separately for veto logic
        if role == "risk_manager":
            risk_manager_result = result
            # Risk Manager doesn't vote on action, it approves/rejects
            continue
        
        weight = float(role_weights.get(role, 1.0)) * confidence
        members.append({
            "action": action,
            "confidence": confidence,
            "reasoning": result.get("reasoning", ""),
            "role": role,
            "weight": weight,
            "raw": result,
        })
        
        # Collect AI-provided leverage and position sizing (for aggregation)
        if result.get("leverage") is not None:
            leverage_values.append((result.get("leverage"), confidence))
        if result.get("position_size_usd") is not None:
            position_size_usd_values.append((result.get("position_size_usd"), confidence))
        if result.get("position_size_percent") is not None:
            position_size_percent_values.append((result.get("position_size_percent"), confidence))
    
    # If no valid members, return hold
    if not members:
        return {
            "action": "hold",
            "confidence": 0.0,
            "reasoning": "No valid swarm results.",
            "members": [],
            "votes": {},
            "agreement": 0,
            "is_unanimous": False,
            "risk_manager_veto": risk_manager_result is not None,
            "risk_manager_approved": risk_manager_result.get("approved", False) if risk_manager_result else None,
            "decision_trace": [],
        }

    # Count votes and calculate weighted confidence
    counts: Dict[str, int] = {}
    confidence_map: Dict[str, List[float]] = {}
    weighted_confidence: Dict[str, float] = {}
    decision_trace: List[str] = []
    
    for member in members:
        action = member["action"]
        counts[action] = counts.get(action, 0) + 1
        confidence_map.setdefault(action, []).append(member["confidence"])
        weighted_confidence[action] = weighted_confidence.get(action, 0.0) + member["weight"]
        
        # Build decision trace
        decision_trace.append(
            f"{member['role'].upper()}: {action.upper()} "
            f"(confidence: {member['confidence']:.2f}, weight: {member['weight']:.2f}) - "
            f"{member['reasoning'][:100]}"
        )

    # Rank actions by vote count and weighted confidence
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
    
    # RISK MANAGER VETO LOGIC (INSTITUTIONAL GRADE)
    risk_manager_approved = True
    risk_manager_reason = None
    if risk_manager_result:
        risk_manager_approved = risk_manager_result.get("approved", False)
        risk_manager_reason = risk_manager_result.get("reason", "")
        decision_trace.append(
            f"RISK_MANAGER: {'APPROVED' if risk_manager_approved else 'VETO'} "
            f"(risk_score: {risk_manager_result.get('risk_score', 0):.2f}) - {risk_manager_reason}"
        )
        
        # VETO: If Risk Manager rejects, force HOLD regardless of other votes
        if not risk_manager_approved:
            top_action = "hold"
            avg_confidence = 0.0
            decision_trace.append(
                "VETO APPLIED: Risk Manager rejected trade. Forcing HOLD."
            )
    
    # CONFIDENCE THRESHOLD CHECK (INSTITUTIONAL GRADE)
    if avg_confidence < min_confidence_threshold and top_action != "hold":
        decision_trace.append(
            f"CONFIDENCE THRESHOLD: Weighted confidence {avg_confidence:.2f} "
            f"below minimum {min_confidence_threshold:.2f}. Forcing HOLD."
        )
        top_action = "hold"
        avg_confidence = 0.0
    
    # Build final reasoning with full trace
    reasoning_parts = [
        f"Swarm consensus: {top_action} ({counts[top_action]}/{len(members)}) "
        f"with avg confidence {avg_confidence:.2f}."
    ]
    
    if risk_manager_result:
        reasoning_parts.append(
            f"Risk Manager: {'APPROVED' if risk_manager_approved else 'VETO'} "
            f"(risk_score: {risk_manager_result.get('risk_score', 0):.2f})"
        )
    
    if avg_confidence < min_confidence_threshold and top_action == "hold":
        reasoning_parts.append(
            f"Confidence threshold not met ({avg_confidence:.2f} < {min_confidence_threshold:.2f})"
        )
    
    reasoning = " ".join(reasoning_parts)

    # Aggregate AI-provided leverage (weighted average by confidence)
    aggregated_leverage = None
    if leverage_values:
        total_weight = sum(conf for _, conf in leverage_values)
        if total_weight > 0:
            weighted_sum = sum(lev * conf for lev, conf in leverage_values)
            aggregated_leverage = round(weighted_sum / total_weight)
            decision_trace.append(f"SWARM_LEVERAGE: Aggregated {len(leverage_values)} leverage recommendations to {aggregated_leverage}x (weighted by confidence)")
    
    # Aggregate AI-provided position size USD (weighted average by confidence)
    aggregated_position_size_usd = None
    if position_size_usd_values:
        total_weight = sum(conf for _, conf in position_size_usd_values)
        if total_weight > 0:
            weighted_sum = sum(size * conf for size, conf in position_size_usd_values)
            aggregated_position_size_usd = round(weighted_sum / total_weight, 2)
            decision_trace.append(f"SWARM_POSITION_SIZE_USD: Aggregated {len(position_size_usd_values)} size recommendations to ${aggregated_position_size_usd} (weighted by confidence)")
    
    # Aggregate AI-provided position size percent (weighted average by confidence)
    aggregated_position_size_percent = None
    if position_size_percent_values:
        total_weight = sum(conf for _, conf in position_size_percent_values)
        if total_weight > 0:
            weighted_sum = sum(size * conf for size, conf in position_size_percent_values)
            aggregated_position_size_percent = round(weighted_sum / total_weight, 2)
            decision_trace.append(f"SWARM_POSITION_SIZE_PERCENT: Aggregated {len(position_size_percent_values)} size recommendations to {aggregated_position_size_percent}% (weighted by confidence)")

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
        "is_unanimous": counts[top_action] == total_votes if top_action in counts else False,
        "risk_manager_veto": risk_manager_result is not None,
        "risk_manager_approved": risk_manager_approved,
        "risk_manager_reason": risk_manager_reason,
        "decision_trace": decision_trace,  # Full trace for "Why did we lose money?" audit
        "min_confidence_threshold": min_confidence_threshold,
        "confidence_threshold_met": avg_confidence >= min_confidence_threshold,
        "leverage": aggregated_leverage,  # AI-provided leverage (aggregated from swarm)
        "position_size_usd": aggregated_position_size_usd,  # AI-provided position size USD
        "position_size_percent": aggregated_position_size_percent,  # AI-provided position size percent
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
    min_confidence_threshold: float = 0.70,
    risk_manager_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Run parallel swarm market analysis with voting.
    
    INSTITUTIONAL GRADE: Role-Based Consensus with Risk Manager Veto
    
    Args:
        analysis_context: Market data and indicators
        swarm_runs: Number of parallel agents to run
        model_provider: AI model provider
        model_name: Specific model name
        role_weights: Weight per agent role for voting
        min_agreement: Minimum agreement percentage for consensus
        min_confidence_threshold: Minimum weighted confidence to execute (default: 0.70)
        risk_manager_context: Context for Risk Manager agent (order_request, positions, risk_limits, balance)
        
    Returns:
        Aggregated swarm result with consensus decision and full trace
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

    # Run market analyst swarm in parallel
    swarm_results = await asyncio.gather(*[run_swarm_member() for _ in range(swarm_runs)])
    swarm_usage = aggregate_usage([r["usage"] for r in swarm_results])
    
    # Run Risk Manager if context provided (INSTITUTIONAL GRADE: Veto Power)
    risk_manager_result = None
    if risk_manager_context:
        try:
            from app.modules.ai_agents.risk_manager_agent import RiskManagerAgent
            risk_manager = RiskManagerAgent(
                model_provider=model_provider,
                model_name=model_name,
            )
            before_rm = risk_manager.model.get_model_info()
            start_rm = time.perf_counter()
            rm_result = await risk_manager.process(risk_manager_context)
            duration_rm_ms = int((time.perf_counter() - start_rm) * 1000)
            after_rm = risk_manager.model.get_model_info()
            usage_rm = usage_delta(before_rm, after_rm)
            
            risk_manager_result = {
                "result": rm_result,
                "role": "risk_manager",
                "usage": usage_rm,
                "duration_ms": duration_rm_ms,
            }
            
            # Add Risk Manager usage to swarm usage
            swarm_usage["input_tokens"] += usage_rm.get("input_tokens", 0)
            swarm_usage["output_tokens"] += usage_rm.get("output_tokens", 0)
            swarm_usage["cost_usd"] += usage_rm.get("cost_usd", 0.0)
        except Exception as e:
            logger.error(f"Risk Manager execution failed: {e}")
            # Continue without Risk Manager - log but don't fail
    
    # Aggregate results with Risk Manager veto
    swarm_aggregate = aggregate_swarm_results(
        [
            {**r["result"], "role": r["role"]}
            for r in swarm_results
        ],
        role_weights=role_weights,
        risk_manager_veto=risk_manager_result["result"] if risk_manager_result else None,
        min_confidence_threshold=min_confidence_threshold,
    )
    
    # Check agreement threshold (secondary check)
    if swarm_aggregate["agreement"] < min_agreement and swarm_aggregate["action"] != "hold":
        swarm_aggregate["action"] = "hold"
        swarm_aggregate["reasoning"] = (
            f"Swarm agreement {swarm_aggregate['agreement']}% below "
            f"minimum {min_agreement}%. " + swarm_aggregate.get("reasoning", "")
        )
        swarm_aggregate["decision_trace"].append(
            f"AGREEMENT THRESHOLD: Agreement {swarm_aggregate['agreement']}% "
            f"below minimum {min_agreement}%. Forcing HOLD."
        )
    
    return {
        "results": swarm_results,
        "risk_manager": risk_manager_result,
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
