# Phase 5 - Market Data & Risk Services

**Status:** 🚧 PARTIAL (Market data done, sentiment & risk rules API missing)  
**Duration:** 12 days  
**Dependencies:** Phase 4 (Flow Orchestration)

---

## 🎯 Objectives

Build market data and risk management infrastructure:
- Real-time market data ingestion
- Technical indicator calculation
- Risk rule enforcement
- Market crash detection
- Sentiment data integration (Reddit, Polymarket)
- Signal aggregation from multiple sources

---

## 🗄️ Database Collections

### market_data (with TTL)
```python
{
    "_id": ObjectId,
    "symbol": str,
    "exchange": str,
    "timeframe": str,
    
    "bars": [
        {
            "timestamp": datetime,
            "open": float,
            "high": float,
            "low": float,
            "close": float,
            "volume": float,
            "indicators": {
                "sma_20": float,
                "sma_50": float,
                "rsi_14": float,
                "macd": dict,
                "atr_14": float,
                "bollinger": dict
            }
        }
    ],
    
    "current": {
        "price": float,
        "change_24h": float,
        "volume_24h": float,
        "high_24h": float,
        "low_24h": float
    },
    
    "health": {
        "volatility": float,
        "trend": str,              # "bullish" | "bearish" | "sideways"
        "strength": int,           # 0-100
        "liquidations_24h": float,
        "funding_rate": float
    },
    
    "last_updated_at": datetime,
    "expires_at": datetime         # TTL index for auto-deletion
}
```

### risk_rules
```python
{
    "_id": ObjectId,
    "user_id": ObjectId,           # null = platform default
    
    "position": {
        "max_size": float,
        "max_leverage": int,
        "max_concurrent": int,
        "symbol_limits": [
            {
                "symbol": str,
                "max_size": float,
                "max_leverage": int
            }
        ]
    },
    
    "daily": {
        "max_loss": float,
        "max_trades": int,
        "current_loss": float,
        "current_trades": int,
        "reset_at": datetime
    },
    
    "account": {
        "min_balance": float,
        "stop_loss_default": float,
        "circuit_breaker": {
            "enabled": bool,
            "consecutive_losses": int,
            "pause_duration": int   # minutes
        }
    },
    
    "market": {
        "max_volatility": float,
        "stop_on_crash": bool,
        "crash_threshold": float    # % drop
    },
    
    "allowed_symbols": [str],
    "blocked_symbols": [str],
    
    "is_active": bool,
    "created_at": datetime,
    "updated_at": datetime
}
```

---

## 🔌 API Endpoints

```
GET    /api/market-data/{symbol}         # Get market data
GET    /api/market-data/{symbol}/health  # Get market health

GET    /api/risk-rules                   # Get user's rules
POST   /api/risk-rules                   # Create rules
PATCH  /api/risk-rules/{id}              # Update rules
GET    /api/risk-rules/validate          # Validate decision
```

---

## 🧪 TDD Plan

### Tests to Write First
- Fetch OHLCV data
- Calculate indicators
- Check risk rules
- Detect market crash
- Enforce position limits
- Circuit breaker logic

---

## ✅ Success Criteria

- [x] Market data cached ✅
- [x] Indicators calculated ✅
- [ ] Risk checks working ⚠️ (AI risk manager exists, rules API missing)
- [ ] Crash detection functional ❌
- [ ] **Reddit sentiment integration** ⚠️ (client exists, not integrated)
- [ ] **Polymarket odds integration** ⚠️ (client exists, not integrated)
- [ ] **Signal aggregator used in flows** ❌
- [ ] All tests passing

---

## 🚀 Next Phase

**Phase 6 - Position Management**
- See [phase-6-positions.md](phase-6-positions.md)



