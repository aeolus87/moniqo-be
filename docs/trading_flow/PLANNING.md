# Demo Planning Notes (Backend + Frontend)

This plan uses the existing backend codebase but **disables auth** for demo.
Be critical: build only what is needed for a working simulation.

## Goal (Demo)

Deliver a demo where a user can:
- Create a flow (solo/swarm, manual/schedule)
- Trigger executions manually
- Watch AI decisions and risk checks
- See simulated orders, positions, and P&L
- View charts and execution logs in the UI

## Non-Negotiables

- No auth, no RBAC, no JWT
- No real funds or real order placement
- Real market data is allowed
- Keep API and UI minimal and fast

## Backend Plan (Use Existing Backend)

### Phase 1: Make Backend Demo-Friendly

Actions:
- Add a **demo mode flag** in settings (e.g., `DEMO_MODE=true`)
- Bypass `get_current_user` dependency when demo mode is on
- Provide a fixed demo user ID for ownership checks

Critical note:
- Without this, every endpoint that depends on auth will fail.

### Phase 2: Demo Flow + Execution (Real Models)

Create missing modules (real DB-backed):
- `flows`: flow config + status
- `executions`: execution records + status

Endpoints:
- `POST /api/v1/flows`
- `GET /api/v1/flows`
- `POST /api/v1/flows/{id}/trigger`

Execution pipeline (simulation):
1) Fetch market data (real or simulated)
2) Generate AI decision
3) Validate risk rules
4) Create **simulated** order record
5) Create **simulated** position record
6) Mark execution status

### Phase 3: Market Data

Use real market data (Polygon) for charts:
- `GET /api/v1/market-data/{symbol}`
- Include OHLCV + indicators (SMA/RSI/MACD)

### Phase 4: Risk Rules (Minimal)

Add a single endpoint:
- `POST /api/v1/risk-rules/validate`

Rules source:
- Use `user_wallets.risk_limits` or static demo defaults

### Phase 5: Monitoring Loop

Use polling:
- Update simulated position prices
- Recalculate P&L
- Close when stop/take thresholds hit

## Frontend Plan (React + TS + Tailwind + HChart)

### Phase 1: Base UI

Pages:
- `Dashboard`
- `Flows`
- `Executions`
- `Positions`
- `Transactions`

### Phase 2: Flow Builder

Actions:
- `Create Flow`
- `Trigger Flow`
- `Pause/Resume Flow`

### Phase 3: Charts + Logs

Charts:
- OHLCV chart for symbol
- P&L chart for positions

Panels:
- Agent decision log
- Execution status list

### Phase 4: Data Handling

- Poll data every N seconds
- Store in local state or a lightweight store

## Execution Checklist (Do in order)

Backend:
1) Add demo mode + auth bypass
2) Implement flows + executions
3) Implement market data endpoint
4) Implement risk validation endpoint
5) Add simulated orders + positions
6) Add monitoring loop

Frontend:
1) Add pages + layout
2) Implement flow create/trigger
3) Wire charts to market data
4) Display executions + positions + P&L


