# Phase 3 - AI Agent Foundations

**Status:** ⏳ PENDING  
**Duration:** 8 days  
**Dependencies:** Phase 2 (Wallet Foundations)

---

## 🎯 Objectives

Build the AI agent management system with:
- Platform agent template registry
- User agent instance configuration
- AI provider abstraction layer
- Performance tracking for learning

---

## 🗄️ Database Collections

### ai_agents (Platform Agent Templates)
```python
{
    "_id": ObjectId,
    "name": str,                    # "Risk Guardian Agent"
    "slug": str,                    # "risk-guardian" (unique)
    "category": str,                # "trading" | "risk" | "analysis" | "monitoring"
    "description": str,
    "icon": str,
    
    "authority": {
        "can_trade": bool,
        "can_adjust_risk": bool,
        "can_close_positions": bool,
        "can_pause_trading": bool,
        "priority": int            # Higher = more authority
    },
    
    "decision_scope": {
        "analyzes_market": bool,
        "manages_risk": bool,
        "executes_trades": bool,
        "monitors_portfolio": bool
    },
    
    "default_prompt": str,         # System prompt template
    "pricing_tier": str,           # "free" | "pro" | "enterprise"
    "is_active": bool,
    "order": int,
    
    "created_at": datetime,
    "updated_at": datetime,
    "created_by": ObjectId         # null for system agents
}
```

### user_nodes (User Agent Instances)
```python
{
    "_id": ObjectId,
    "user_id": ObjectId,
    "ai_agent_id": ObjectId,       # Reference to ai_agents
    "user_wallet_id": ObjectId,    # Reference to user_wallets
    
    "name": str,
    "description": str,
    
    "basic_config": {
        "symbols": [str],          # Must be subset of wallet allowed_symbols
        "ai_provider": str,        # "anthropic" | "openai" | "groq"
        "ai_model": str,           # "claude-3-5-sonnet" | "gpt-4"
        "personality": str,        # "conservative" | "balanced" | "aggressive"
        "temperature": float,      # 0.0-1.0
        "max_tokens": int
    },
    
    "prompts": {
        "system_prompt": str,      # Override default
        "user_prompt": str         # Template with {{variables}}
    },
    
    "ai_learning": {
        "success_rate": float,     # % profitable decisions
        "avg_pnl": float,
        "best_timeframes": [str],
        "best_symbols": [str],
        "adapted_parameters": dict,
        "learning_history": [
            {
                "date": datetime,
                "lesson": str,
                "adjustment": dict
            }
        ]
    },
    
    "is_active": bool,
    "created_at": datetime,
    "updated_at": datetime
}
```

---

## 🔌 API Endpoints

```
GET    /api/ai-agents                      # List templates
POST   /api/ai-agents                      # Create (admin)
GET    /api/ai-agents/{slug}               # Get details
PATCH  /api/ai-agents/{slug}               # Update (admin)

POST   /api/user-nodes                     # Create instance
GET    /api/user-nodes                     # List user's nodes
GET    /api/user-nodes/{id}                # Get details
PATCH  /api/user-nodes/{id}                # Update config
DELETE /api/user-nodes/{id}                # Delete
GET    /api/user-nodes/{id}/performance    # Learning stats
```

---

## 🧪 TDD Plan

### Tests to Write First
- Create agent template with valid data
- List agents filtered by category
- Create user node with valid config
- Validate symbols against wallet limits
- Update node configuration
- Track performance metrics

### Implementation Order
1. Write all tests
2. Implement ai_agents models
3. Implement user_nodes models
4. Implement services
5. Implement routers
6. Run tests

---

## 🎯 Seed Data

**Core Agent Templates:**
1. **Risk Guardian** - Enforces limits, pauses on breach
2. **Market Intelligence** - Analyzes market conditions
3. **Trade Executor** - Executes orders
4. **Position Monitor** - Tracks open positions

---

## ✅ Success Criteria

- [ ] Agent templates seeded
- [ ] User can list available agents
- [ ] User can create agent instances
- [ ] Symbols validated against wallet
- [ ] Performance tracking placeholders
- [ ] All tests passing
- [ ] API documented

---

## 🚀 Next Phase

**Phase 4 - Flow Orchestration**
- See [phase-4-flows.md](phase-4-flows.md)

