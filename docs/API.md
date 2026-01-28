# Moniqo Trading API Documentation

Complete API reference for the Moniqo Trading Platform backend.

## Overview

- **Base URL**: `http://localhost:8000/api/v1`
- **Authentication**: JWT Bearer tokens
- **Content-Type**: `application/json`

### Authentication

Most endpoints require authentication via JWT tokens. Include the token in the `Authorization` header:

```
Authorization: Bearer <your_jwt_token>
```

### Error Responses

All endpoints return errors in a standard format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

Common HTTP status codes:
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Validation Error
- `500` - Internal Server Error

### Pagination

List endpoints support pagination with:
- `limit` (int, default: 10) - Maximum items to return
- `offset` (int, default: 0) - Number of items to skip

---

## Authentication `/auth`

### Register User
```
POST /auth/register
```

Create a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Response:** `201 Created`
```json
{
  "id": "user_id",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe"
}
```

### Login
```
POST /auth/login
```

Authenticate and receive JWT tokens.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJI...",
  "refresh_token": "eyJhbGciOiJI...",
  "token_type": "bearer"
}
```

### Refresh Token
```
POST /auth/refresh
```

Get a new access token using a refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJI..."
}
```

### Verify Email
```
GET /auth/verify-email?token=<verification_token>
```

### Forgot Password
```
POST /auth/forgot-password
```

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

### Reset Password
```
POST /auth/reset-password
```

**Request Body:**
```json
{
  "token": "reset_token",
  "password": "new_password"
}
```

---

## Users `/users`

### Get Current User
```
GET /users/me
```

Get authenticated user's profile.

### Update Current User
```
PUT /users/me
```

**Request Body:**
```json
{
  "first_name": "Updated",
  "last_name": "Name"
}
```

### Delete Current User
```
DELETE /users/me
```

### List Users (Admin)
```
GET /users?limit=10&offset=0
```
*Requires: `users:read` permission*

### Get User by ID (Admin)
```
GET /users/{user_id}
```
*Requires: `users:read` permission*

### Update User (Admin)
```
PUT /users/{user_id}
```
*Requires: `users:write` permission*

### Delete User (Admin)
```
DELETE /users/{user_id}
```
*Requires: `users:delete` permission*

---

## Trading Flows `/flows`

### Create Flow
```
POST /flows
```

Create a new trading automation flow.

**Request Body:**
```json
{
  "name": "BTC Swing Trade",
  "symbol": "BTC/USDT",
  "mode": "swarm",
  "trigger": "manual",
  "agents": ["market_analyst", "risk_manager"],
  "config": {
    "order_size_usd": 100,
    "swarm_runs": 3,
    "swarm_min_agreement": 60
  }
}
```

**Response:** `201 Created`

### List Flows
```
GET /flows?status=active&limit=10&offset=0
```

**Query Parameters:**
- `status` - Filter by status (`active`, `paused`, `draft`)

### Get Flow
```
GET /flows/{flow_id}
```

### Update Flow
```
PATCH /flows/{flow_id}
```

### Delete Flow
```
DELETE /flows/{flow_id}
```

### Start Flow
```
POST /flows/{flow_id}/start
```

Start continuous trading loop.

**Request Body:**
```json
{
  "model_provider": "groq",
  "model_name": "llama-3.3-70b-versatile"
}
```

### Stop Flow
```
POST /flows/{flow_id}/stop
```

Stop continuous trading loop.

### Trigger Single Execution
```
POST /flows/{flow_id}/trigger
```

Run a single flow execution without continuous loop.

**Request Body:**
```json
{
  "model_provider": "groq",
  "model_name": "llama-3.3-70b-versatile",
  "order_quantity_override": 0.01,
  "order_size_usd_override": 100
}
```

### Get Flow Executions
```
GET /flows/{flow_id}/executions?limit=10&offset=0
```

### Get All Executions
```
GET /flows/executions/all?limit=10&offset=0
```

### Get Execution by ID
```
GET /flows/executions/{execution_id}
```

### Delete Execution
```
DELETE /flows/executions/{execution_id}
```

### Delete All Executions
```
DELETE /flows/executions
```

### Get Agent Decisions
```
GET /flows/agent-decisions/all?limit=50
```

---

## Positions `/positions`

### List Positions
```
GET /positions?status=open&symbol=BTC/USDT&limit=10&offset=0
```

**Query Parameters:**
- `status` - Filter by status (`open`, `closed`, `liquidated`)
- `symbol` - Filter by trading pair

### Get Position
```
GET /positions/{position_id}
```

### Update Position
```
PATCH /positions/{position_id}
```

**Request Body:**
```json
{
  "stop_loss": 85000,
  "take_profit": 95000
}
```

### Close Position
```
POST /positions/{position_id}/close
```

Manually close an open position at market price.

### Monitor Position
```
POST /positions/{position_id}/monitor
```

Manually trigger position monitoring/update.

---

## Orders `/orders`

### Create Order
```
POST /orders
```

**Request Body:**
```json
{
  "symbol": "BTC/USDT",
  "side": "buy",
  "order_type": "limit",
  "quantity": 0.001,
  "price": 88000,
  "time_in_force": "GTC"
}
```

### List Orders
```
GET /orders?status=open&symbol=BTC/USDT&limit=10&offset=0
```

### Get Order
```
GET /orders/{order_id}
```

### Cancel Order
```
POST /orders/{order_id}/cancel
```

### Monitor Order
```
POST /orders/{order_id}/monitor
```

---

## AI Agents `/ai-agents`

### List Providers
```
GET /ai-agents/providers
```

Get available AI model providers and their models.

### Test Connection
```
POST /ai-agents/test-connection
```

**Request Body:**
```json
{
  "provider": "groq",
  "model_name": "llama-3.3-70b-versatile"
}
```

### Analyze Market
```
POST /ai-agents/analyze-market
```

Get AI trading recommendation for a symbol.

**Request Body:**
```json
{
  "symbol": "BTC/USDT",
  "provider": "groq",
  "model_name": "llama-3.3-70b-versatile",
  "include_sentiment": true
}
```

### Get Prompts
```
GET /ai-agents/prompts
```

Get AI agent system prompts and configurations.

### Health Check
```
GET /ai-agents/health
```

---

## Conversations `/conversations`

### Get Conversation
```
GET /conversations/{execution_id}
```

Get conversation (AI agent discussion) for an execution.

### Stream Conversation (WebSocket)
```
WebSocket /conversations/ws/{execution_id}
```

Connect to receive real-time conversation updates including agent messages and swarm votes.

**Message Types:**
- `initial` - Full conversation state on connect
- `message` - New agent message
- `swarm_vote` - Voting results update

### Get Voting Results
```
GET /conversations/{conversation_id}/voting
```

### Add Message
```
POST /conversations/{conversation_id}/add-message
```

---

## Market Data `/market`

### Get OHLCV Data
```
GET /market/ohlc/{symbol}?interval=1h&limit=100
```

**Query Parameters:**
- `interval` - Candlestick interval (`1m`, `5m`, `15m`, `1h`, `4h`, `1d`)
- `limit` - Number of candles

### Get Market Data
```
GET /market/market-data/{symbol}
```

Combined market data including candles, indicators, health metrics, and signals.

### Get Market Health
```
GET /market/market-data/{symbol}/health
```

### Get 24h Ticker
```
GET /market/ticker/{symbol}
```

### Get Current Price
```
GET /market/price/{symbol}
```

### Get Multiple Tickers
```
GET /market/tickers?symbols=BTC/USDT,ETH/USDT
```

### Get Global Stats
```
GET /market/global-stats
```

Global cryptocurrency market statistics.

### Get Top Coins
```
GET /market/top-coins?limit=10
```

### Get Coin Info
```
GET /market/coin/{symbol}
```

### Calculate Indicators
```
GET /market/indicators/{symbol}?interval=1h
```

Technical indicators (RSI, MACD, Bollinger Bands, etc.)

### Health Check
```
GET /market/health
```

---

## Wallets `/wallets`

### Create Wallet Definition (Admin)
```
POST /wallets/definitions
```
*Requires: `wallets:write` permission*

### List Wallet Definitions
```
GET /wallets/definitions?type=exchange&is_active=true
```

### Get Wallet Definition
```
GET /wallets/definitions/{slug}
```

### Update Wallet Definition (Admin)
```
PATCH /wallets/definitions/{slug}
```
*Requires: `wallets:write` permission*

### Delete Wallet Definition (Admin)
```
DELETE /wallets/definitions/{slug}
```
*Requires: `wallets:write` permission*

---

## User Wallets

### List User Wallets
```
GET /user-wallets
```

### Create User Wallet
```
POST /user-wallets
```

**Request Body:**
```json
{
  "wallet_slug": "binance",
  "credentials_id": "cred_id",
  "nickname": "My Binance"
}
```

### Get User Wallet
```
GET /user-wallets/{wallet_id}
```

### Update User Wallet
```
PUT /user-wallets/{wallet_id}
```

### Delete User Wallet
```
DELETE /user-wallets/{wallet_id}
```

### Test Connection
```
POST /user-wallets/{wallet_id}/test-connection
```

### Sync Balance
```
POST /user-wallets/{wallet_id}/sync-balance
```

### Get Sync Logs
```
GET /user-wallets/{wallet_id}/sync-logs
```

---

## Credentials `/wallets/credentials`

### Create Credentials
```
POST /wallets/credentials
```

**Request Body:**
```json
{
  "name": "Binance API",
  "wallet_slug": "binance",
  "api_key": "your_api_key",
  "api_secret": "your_api_secret",
  "additional_config": {}
}
```

### List Credentials
```
GET /wallets/credentials?wallet_id=xxx&is_active=true
```

### Get Credentials
```
GET /wallets/credentials/{credentials_id}
```

### Update Credentials
```
PATCH /wallets/credentials/{credentials_id}
```

### Delete Credentials
```
DELETE /wallets/credentials/{credentials_id}
```

### Test Credentials
```
POST /wallets/credentials/{credentials_id}/test
```

---

## Risk Rules `/risk-rules`

### Create Risk Rule
```
POST /risk-rules
```

**Request Body:**
```json
{
  "name": "Max Position Size",
  "rule_type": "max_position_size",
  "condition": {
    "max_usd": 1000
  },
  "action": "reject",
  "is_active": true
}
```

### List Risk Rules
```
GET /risk-rules?is_active=true&limit=10&offset=0
```

### Get Risk Rule
```
GET /risk-rules/{rule_id}
```

### Validate Trade
```
GET /risk-rules/validate?symbol=BTC/USDT&side=buy&quantity=0.01&price=90000
```

### Update Risk Rule
```
PATCH /risk-rules/{rule_id}
```

### Delete Risk Rule
```
DELETE /risk-rules/{rule_id}
```

---

## Plans `/plans`

### Create Plan (Admin)
```
POST /plans
```
*Requires: `plans:write` permission*

### List Plans
```
GET /plans?limit=10&offset=0
```

### Get Plan
```
GET /plans/{plan_id}
```
*Requires: `plans:read` permission*

### Update Plan (Admin)
```
PUT /plans/{plan_id}
```
*Requires: `plans:write` permission*

### Delete Plan (Admin)
```
DELETE /plans/{plan_id}
```
*Requires: `plans:write` permission*

---

## User Plans (Subscriptions) `/user-plans`

### Create Subscription
```
POST /user-plans
```
*Requires: `user_plans:write` permission*

### Get Current Subscription
```
GET /user-plans/current
```
*Requires: `user_plans:read` permission*

### List Subscriptions
```
GET /user-plans
```
*Requires: `user_plans:read` permission*

### Get Subscription
```
GET /user-plans/{subscription_id}
```
*Requires: `user_plans:read` permission*

### Update Subscription
```
PUT /user-plans/{subscription_id}
```
*Requires: `user_plans:write` permission*

### Cancel Subscription
```
POST /user-plans/{subscription_id}/cancel
```
*Requires: `user_plans:write` permission*

### Renew Subscription
```
POST /user-plans/{subscription_id}/renew
```
*Requires: `user_plans:write` permission*

---

## Notifications `/notifications`

### Create Notification
```
POST /notifications
```
*Requires: `notifications:write` permission*

### List Notifications
```
GET /notifications?limit=10&offset=0
```
*Requires: `notifications:read` permission*

### Get Unread Count
```
GET /notifications/unread-count
```
*Requires: `notifications:read` permission*

### Get Notification
```
GET /notifications/{notification_id}
```
*Requires: `notifications:read` permission*

### Mark as Read
```
POST /notifications/{notification_id}/read
```
*Requires: `notifications:write` permission*

### Mark All as Read
```
POST /notifications/read-all
```
*Requires: `notifications:write` permission*

### Delete Notification
```
DELETE /notifications/{notification_id}
```
*Requires: `notifications:write` permission*

---

## Roles `/roles` (Superuser Only)

### Create Role
```
POST /roles
```

### List Roles
```
GET /roles?limit=10&offset=0
```

### Get Role
```
GET /roles/{role_id}
```

### Update Role
```
PUT /roles/{role_id}
```

### Delete Role
```
DELETE /roles/{role_id}
```

---

## Permissions `/permissions` (Superuser Only)

### Create Permission
```
POST /permissions
```

### List Permissions
```
GET /permissions?limit=10&offset=0
```

### Get Permission
```
GET /permissions/{permission_id}
```

### Update Permission
```
PUT /permissions/{permission_id}
```

### Delete Permission
```
DELETE /permissions/{permission_id}
```

---

## WebSocket Events

### Socket.IO Connection
```
ws://localhost:8000/socket.io
```

**Authentication:**
```javascript
const socket = io('http://localhost:8000', {
  auth: { token: 'your_jwt_token' }
});
```

### Events

#### `execution_update`
Emitted during flow execution with progress updates.

```json
{
  "execution_id": "exec_123",
  "flow_id": "flow_456",
  "status": "RUNNING",
  "current_step": 1,
  "step_name": "AI Swarm Analyzing",
  "progress_percent": 30,
  "message": "Running market analysis with AI agents..."
}
```

#### `position_update`
Emitted when position data changes.

```json
{
  "position_id": "pos_123",
  "status": "open",
  "current_price": 89500,
  "unrealized_pnl": 125.50,
  "unrealized_pnl_percent": 1.4
}
```

#### `market_update`
Real-time price updates (when subscribed).

### Rooms

Join rooms to receive specific updates:
- `positions:{user_id}` - User's position updates
- `executions:{execution_id}` - Specific execution updates

---

## Data Models

### Flow
```json
{
  "id": "flow_123",
  "name": "BTC Swing Trade",
  "symbol": "BTC/USDT",
  "mode": "swarm",
  "status": "active",
  "trigger": "manual",
  "agents": ["market_analyst", "risk_manager"],
  "config": {
    "order_size_usd": 100,
    "swarm_runs": 3,
    "swarm_min_agreement": 60,
    "auto_loop_enabled": true,
    "auto_loop_delay_seconds": 30
  },
  "total_executions": 10,
  "successful_executions": 8,
  "total_pnl_usd": 150.25,
  "win_rate": 62.5,
  "created_at": "2026-01-15T10:00:00Z",
  "updated_at": "2026-01-28T15:30:00Z"
}
```

### Execution
```json
{
  "id": "exec_123",
  "flow_id": "flow_456",
  "flow_name": "BTC Swing Trade",
  "status": "completed",
  "started_at": "2026-01-28T15:30:00Z",
  "completed_at": "2026-01-28T15:30:45Z",
  "duration": 45000,
  "steps": [
    {
      "name": "data_fetch",
      "status": "completed",
      "started_at": "...",
      "completed_at": "...",
      "data": {}
    }
  ],
  "result": {
    "action": "buy",
    "confidence": 0.75,
    "reasoning": "Strong bullish signals..."
  }
}
```

### Position
```json
{
  "id": "pos_123",
  "user_id": "user_456",
  "symbol": "BTC/USDT",
  "side": "long",
  "status": "open",
  "entry": {
    "quantity": 0.01,
    "price": 88500,
    "value_usd": 885,
    "timestamp": "2026-01-28T15:30:45Z"
  },
  "current": {
    "price": 89500,
    "value": 895,
    "unrealized_pnl": 10,
    "unrealized_pnl_percent": 1.13
  },
  "risk_management": {
    "stop_loss": 86000,
    "take_profit": 95000
  }
}
```

### Order
```json
{
  "id": "order_123",
  "user_id": "user_456",
  "symbol": "BTC/USDT",
  "side": "buy",
  "order_type": "limit",
  "status": "filled",
  "requested_amount": 0.01,
  "filled_amount": 0.01,
  "limit_price": 88500,
  "average_fill_price": 88495,
  "total_fees": 0.85,
  "created_at": "2026-01-28T15:30:00Z"
}
```

---

## Rate Limits

API rate limits are applied per user:
- **Standard**: 60 requests/minute
- **Premium**: 300 requests/minute

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1706450400
```

---

## Changelog

### v1.0.0 (2026-01-28)
- Initial API documentation
- Refactored flows module for better maintainability
- WebSocket support for real-time updates
- Swarm consensus voting for AI trading decisions
