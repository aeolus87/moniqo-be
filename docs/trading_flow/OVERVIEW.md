# Trading Flow Backend Overview

This folder documents the backend trading-flow system only.
Frontend is explicitly out of scope for these docs.

## What the system does

- Create trading flows (solo or swarm)
- Trigger flows (manual or scheduled)
- Run AI analysis, risk checks, and execution
- Place orders, open positions, and monitor them
- Close positions and log results

## Primary building blocks

- Flows: configuration and trigger rules
- Executions: run records for each flow trigger
- AI Agents: market analysis, risk manager, executor, monitor
- Orders + Positions: trading lifecycle objects
- Market Data: OHLCV and indicators
- Wallets + Credentials: exchange connections
- Background tasks: order/position monitoring

## Current state (backend)

- Orders, positions, wallets, credentials, AI agents exist
- Monitoring services and Celery tasks exist
- Flow and execution orchestration is missing
- Risk rule validation and market-data APIs are missing
- Order placement is stubbed in the orders router

