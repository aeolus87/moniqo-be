# Phase 7 - Swarm Coordination

**Status:** ⏳ PENDING  
**Duration:** 14 days  
**Dependencies:** Phase 5 (Market Data), Phase 6 (Positions)

---

## 🎯 Objectives

Build multi-agent swarm system:
- Agent conversation logging
- Voting and consensus
- Learning from outcomes
- Real-time UI streaming
- Learning outcome recording (success, P&L, lessons)
- Agent performance tracking
- Parameter adjustment based on outcomes

---

## 🗄️ Database Collections

### ai_conversations
```python
{
    "_id": ObjectId,
    "user_id": ObjectId,
    "execution_id": ObjectId,
    "flow_id": ObjectId,
    
    "context": {
        "symbol": str,
        "action": str,             # "analyzing" | "voting" | "executing"
        "phase": str               # "market_analysis" | "risk_check" | "trade_decision"
    },
    
    "messages": [
        {
            "_id": ObjectId,
            "agent_name": str,
            "agent_role": str,
            "ai_model": str,
            
            "message_type": str,   # "thought" | "analysis" | "vote" | "decision"
            
            "content": {
                "text": str,
                "confidence": int,
                "sentiment": str,  # "bullish" | "bearish" | "neutral"
                "data": dict
            },
            
            "vote": {
                "action": str,     # "buy" | "sell" | "hold"
                "confidence": int,
                "weight": int
            },
            
            "timestamp": datetime,
            
            "ui": {
                "tone": str,       # "neutral" | "urgent" | "calm" | "excited"
                "icon": str,
                "color": str
            }
        }
    ],
    
    "swarm_vote": {
        "total_agents": int,
        "votes": [dict],
        "results": {
            "buy": {"votes": int, "total_confidence": float},
            "sell": {"votes": int, "total_confidence": float},
            "hold": {"votes": int, "total_confidence": float}
        },
        "consensus": {
            "action": str,
            "confidence": int,
            "agreement": int,
            "is_unanimous": bool
        },
        "voting_completed": datetime
    },
    
    "outcome": {
        "executed": bool,
        "action": str,
        "reasoning": str,
        "timestamp": datetime
    },
    
    "status": str,                 # "in_progress" | "voting" | "completed"
    "created_at": datetime,
    "updated_at": datetime
}
```

### ai_decisions_log (Learning Database)
```python
{
    "_id": ObjectId,
    "user_id": ObjectId,
    "user_node_id": ObjectId,
    
    "decision": {
        "type": str,               # "trade" | "risk_adjustment" | "pause"
        "action": str,
        "symbol": str,
        "confidence": int
    },
    
    "context": {
        "market_conditions": dict,
        "portfolio_state": dict,
        "risk_metrics": dict
    },
    
    "outcome": {
        "success": bool,
        "pnl": float,
        "time_held": int,          # seconds
        "exit_reason": str
    },
    
    "learning": {
        "was_correct": bool,
        "confidence_accuracy": float,
        "lessons_learned": [str],
        "parameters_to_adjust": dict
    },
    
    "timestamp": datetime
}
```

---

## 🔌 API Endpoints

```
GET    /api/conversations/{execution_id}           # Get conversation
WS     /ws/conversations/{execution_id}            # Stream real-time

GET    /api/conversations/{id}/voting              # Get voting results
POST   /api/conversations/{id}/add-message         # Add AI message

GET    /api/learning/{user_node_id}/stats          # Learning statistics
POST   /api/learning/{user_node_id}/feedback       # Record outcome
```

---

## 🧪 TDD Plan

### Tests to Write First
- Create conversation log
- Add agent messages
- Calculate voting consensus
- Stream messages via WebSocket
- Record learning outcomes
- Update agent performance

---

## ✅ Success Criteria

- [ ] Conversations logged ❌
- [ ] Voting works correctly ❌
- [ ] Consensus calculated ❌
- [ ] WebSocket streaming works ❌
- [ ] **Learning data recorded** ❌
- [ ] **Agent performance metrics updated** ❌
- [ ] **Lessons learned stored** ❌
- [ ] **Parameter adjustment based on outcomes** ❌
- [ ] All tests passing

---

## 🚀 Next Phase

**Phase 8 - Testing & Hardening**
- See [phase-8-testing.md](phase-8-testing.md)



