# Phase 4 - Flow Orchestration

**Status:** ⏳ PENDING  
**Duration:** 10 days  
**Dependencies:** Phase 2 (Wallets), Phase 3 (AI Agents)

---

## 🎯 Objectives

Build workflow system for combining AI agents:
- Solo and swarm flow modes
- Manual and scheduled triggers
- Execution logging
- Cost tracking

---

## 🗄️ Database Collections

### flows
```python
{
    "_id": ObjectId,
    "user_id": ObjectId,
    "name": str,
    "description": str,
    
    "agents": [
        {
            "user_node_id": ObjectId,
            "role": str,              # "analyzer" | "risk_manager" | "executor"
            "execution_order": int
        }
    ],
    
    "mode": str,                      # "solo" | "swarm"
    
    "coordination": {
        "decision_model": str,        # "consensus" | "sequential"
        "conflict_resolution": str,   # "majority_vote" | "priority"
        "min_confidence": int,        # 0-100
        "min_agreement": int          # 0-100 (swarm only)
    },
    
    "trigger": {
        "type": str,                  # "manual" | "schedule"
        "schedule": str,              # Cron expression
        "is_active": bool
    },
    
    "stats": {
        "total_executions": int,
        "successful_executions": int,
        "failed_executions": int,
        "avg_execution_time": float,
        "last_executed_at": datetime
    },
    
    "status": str,                    # "draft" | "active" | "paused"
    "created_at": datetime,
    "updated_at": datetime
}
```

### executions
```python
{
    "_id": ObjectId,
    "user_id": ObjectId,
    "flow_id": ObjectId,
    
    "status": str,                    # "running" | "completed" | "failed"
    "started_at": datetime,
    "completed_at": datetime,
    "duration": int,                  # milliseconds
    
    "ai_decisions": [
        {
            "node_id": str,
            "user_node_id": ObjectId,
            "ai_agent": str,
            
            "input": dict,
            "output": dict,
            "decision": {
                "action": str,
                "confidence": int,
                "reasoning": str
            },
            
            "ai_usage": {
                "tokens_input": int,
                "tokens_output": int,
                "cost": float
            }
        }
    ],
    
    "total_cost": float,
    "created_at": datetime
}
```

---

## 🔌 API Endpoints

```
POST   /api/flows                    # Create flow
GET    /api/flows                    # List user's flows
GET    /api/flows/{id}               # Get details
PATCH  /api/flows/{id}               # Update
DELETE /api/flows/{id}               # Delete
POST   /api/flows/{id}/trigger       # Manual trigger
GET    /api/flows/{id}/executions    # List executions
```

---

## 🧪 TDD Plan

### Tests to Write First
- Create solo flow
- Create swarm flow
- Validate agent compatibility
- Trigger flow manually
- Log execution details
- Track costs

---

## ✅ Success Criteria

- [ ] Solo and swarm flows work
- [ ] Manual trigger functional
- [ ] Executions logged
- [ ] Costs tracked
- [ ] All tests passing

---

## 🚀 Next Phase

**Phase 5 - Market Data & Risk**
- See [phase-5-market-risk.md](phase-5-market-risk.md)



