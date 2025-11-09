# Phase 6 - Position Management

**Status:** ⏳ PENDING  
**Duration:** 10 days  
**Dependencies:** Phase 5 (Market Data & Risk)

---

## 🎯 Objectives

Build position tracking and monitoring system:
- Position lifecycle management
- Real-time P&L tracking
- AI-managed stops/take-profits
- Position monitoring loops

---

## 🗄️ Database Collections

### positions
```python
{
    "_id": ObjectId,
    "user_id": ObjectId,
    "user_wallet_id": ObjectId,
    "flow_id": ObjectId,
    "user_node_id": ObjectId,
    
    "symbol": str,
    "side": str,                   # "long" | "short"
    
    "entry": {
        "price": float,
        "size": float,
        "leverage": int,
        "margin": float,
        "total_value": float,      # Notional
        "fee": float,
        "timestamp": datetime,
        
        "ai_reasoning": str,
        "ai_confidence": int,
        "market_conditions": dict
    },
    
    "current": {
        "price": float,
        "value": float,
        "unrealized_pnl": float,
        "unrealized_pnl_percent": float,
        "risk_level": str,         # "low" | "medium" | "high"
        "margin_level": float,     # % until liquidation
        "liquidation_price": float,
        "last_updated_at": datetime
    },
    
    "ai_management": {
        "current_stop_loss": float,
        "current_take_profit": float,
        "trailing_stop": {
            "enabled": bool,
            "distance": float,
            "adjusted_by": str
        },
        "should_close": {
            "reason": str,
            "urgency": str,        # "low" | "medium" | "high"
            "confidence": int
        }
    },
    
    "exit": {
        "price": float,
        "size": float,
        "fee": float,
        "realized_pnl": float,
        "realized_pnl_percent": float,
        "reason": str,             # "take_profit" | "stop_loss" | "manual" | "ai_signal"
        "timestamp": datetime
    },
    
    "status": str,                 # "open" | "closed" | "liquidated"
    "created_at": datetime,
    "updated_at": datetime
}
```

### transactions
```python
{
    "_id": ObjectId,
    "user_id": ObjectId,
    "execution_id": ObjectId,
    "position_id": ObjectId,
    
    "exchange": str,
    "symbol": str,
    "type": str,                   # "buy" | "sell"
    "side": str,                   # "long" | "short"
    
    "quantity": float,
    "price": float,
    "total_value": float,
    "fee": float,
    "fee_currency": str,
    
    "pnl": float,
    "pnl_percent": float,
    
    "order_id": str,               # Exchange order ID
    "status": str,                 # "pending" | "filled" | "cancelled"
    
    "reason": str,                 # AI's reasoning
    "agent_id": ObjectId,
    
    "timestamp": datetime,
    "created_at": datetime
}
```

---

## 🔌 API Endpoints

```
GET    /api/positions                    # List open positions
GET    /api/positions/{id}               # Get position details
PATCH  /api/positions/{id}/stop-loss     # Update stop loss
PATCH  /api/positions/{id}/take-profit   # Update take profit
POST   /api/positions/{id}/close         # Close position

GET    /api/transactions                 # Trade history
GET    /api/transactions/{id}            # Transaction details
```

---

## 🧪 TDD Plan

### Tests to Write First
- Create position
- Track P&L updates
- Update stop loss
- Close position
- Calculate realized P&L
- Monitor position health

---

## ✅ Success Criteria

- [ ] Positions tracked in real-time
- [ ] P&L calculated correctly
- [ ] AI updates stops/TP
- [ ] Monitoring loops work
- [ ] All tests passing

---

## 🚀 Next Phase

**Phase 7 - Swarm Coordination**
- See [phase-7-swarm.md](phase-7-swarm.md)

