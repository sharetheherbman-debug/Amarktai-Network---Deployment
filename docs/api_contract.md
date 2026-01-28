# API Contract Documentation

This document defines the complete API contract for the Amarktai Network Trading System including all endpoints, payloads, responses, SSE events, and WebSocket message formats.

## Table of Contents

- [Authentication](#authentication)
- [Core Endpoints](#core-endpoints)
- [Bot Management](#bot-management)
- [Trading Endpoints](#trading-endpoints)
- [AI Chat](#ai-chat)
- [System Endpoints](#system-endpoints)
- [Wallet & Fund Management](#wallet--fund-management)
- [Platform & Provider Endpoints](#platform--provider-endpoints)
- [Real-time Communication](#real-time-communication)
- [Admin Endpoints](#admin-endpoints)
- [Error Schema](#error-schema)

---

## Authentication

### POST /api/auth/register
**Description**: Register a new user account

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "first_name": "John",
  "invite_code": "optional_invite_code"
}
```

**Success Response** (200):
```json
{
  "token": "jwt_token_string",
  "user": {
    "id": "user_id",
    "email": "user@example.com",
    "first_name": "John",
    "currency": "ZAR",
    "system_mode": "testing",
    "two_factor_enabled": false
  }
}
```

### POST /api/auth/login
**Description**: Authenticate user and get JWT token

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "password",
  "totp_code": "123456"  // Optional, required if 2FA enabled
}
```

**Success Response** (200):
```json
{
  "token": "jwt_token_string",
  "user": {
    "id": "user_id",
    "email": "user@example.com",
    "first_name": "John"
  }
}
```

### POST /api/auth/2fa/enroll
**Description**: Enroll in two-factor authentication

**Headers**: `Authorization: Bearer <token>`

**Success Response** (200):
```json
{
  "success": true,
  "secret": "BASE32_SECRET",
  "provisioning_uri": "otpauth://totp/Amarktai:user@example.com?secret=SECRET&issuer=Amarktai",
  "qr_code": "data:image/png;base64,..."
}
```

### POST /api/auth/2fa/verify
**Description**: Verify and enable 2FA with TOTP code

**Headers**: `Authorization: Bearer <token>`

**Request Body**:
```json
{
  "totp_code": "123456"
}
```

**Success Response** (200):
```json
{
  "success": true,
  "message": "2FA enabled successfully"
}
```

---

## Core Endpoints

### GET /api/system/ping
**Description**: Health check endpoint

**Success Response** (200):
```json
{
  "status": "ok",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### GET /api/system/status
**Description**: Get comprehensive system status

**Headers**: `Authorization: Bearer <token>`

**Success Response** (200):
```json
{
  "success": true,
  "status": {
    "database": "connected",
    "websocket": "active",
    "sse": "active",
    "api": "operational",
    "bots_active": 5,
    "bots_total": 10
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### GET /api/system/mode
**Description**: Get current system mode for user

**Headers**: `Authorization: Bearer <token>`

**Success Response** (200):
```json
{
  "success": true,
  "mode": "live_trading",  // One of: testing, live_trading, autopilot
  "paper_trading": false,
  "live_trading": true,
  "autopilot": false
}
```

### POST /api/system/mode
**Description**: Update system mode

**Headers**: `Authorization: Bearer <token>`

**Request Body**:
```json
{
  "mode": "live_trading"
}
```

**Success Response** (200):
```json
{
  "success": true,
  "mode": "live_trading"
}
```

### GET /api/system/platforms
**Description**: Get list of all supported trading platforms

**Success Response** (200):
```json
{
  "platforms": [
    {
      "id": "luno",
      "name": "Luno",
      "display_name": "Luno",
      "enabled": true,
      "bot_limit": 5,
      "supports_paper": true,
      "supports_live": true,
      "icon": "🇿🇦",
      "color": "#3861FB",
      "region": "ZA"
    }
  ],
  "total_count": 5,
  "default": "all",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### GET /api/platforms/health
**Description**: Get health status for all platforms

**Headers**: `Authorization: Bearer <token>`

**Success Response** (200):
```json
{
  "success": true,
  "platforms": {
    "luno": {
      "status": "operational",
      "has_keys": true,
      "keys_valid": true,
      "last_check": "2024-01-01T00:00:00Z",
      "api_latency_ms": 45
    },
    "binance": {
      "status": "not_configured",
      "has_keys": false,
      "keys_valid": null,
      "last_check": null
    }
  }
}
```

---

## Bot Management

### GET /api/bots
**Description**: Get all bots for authenticated user

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `platform` (optional): Filter by platform (luno, binance, etc.)
- `status` (optional): Filter by status (active, paused, stopped)

**Success Response** (200):
```json
{
  "success": true,
  "bots": [
    {
      "id": "bot_id",
      "name": "Alpha Trader",
      "exchange": "luno",
      "status": "active",
      "trading_mode": "paper",
      "risk_mode": "balanced",
      "initial_capital": 1000.0,
      "current_capital": 1050.0,
      "total_profit": 50.0,
      "profit_percentage": 5.0,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1
}
```

### POST /api/bots
**Description**: Create a new trading bot

**Headers**: `Authorization: Bearer <token>`

**Request Body**:
```json
{
  "name": "Alpha Trader",
  "exchange": "luno",
  "trading_mode": "paper",
  "risk_mode": "balanced",
  "initial_capital": 1000.0,
  "strategy": "momentum"
}
```

**Success Response** (201):
```json
{
  "success": true,
  "bot": {
    "id": "bot_id",
    "name": "Alpha Trader",
    "status": "created"
  }
}
```

### DELETE /api/bots/{bot_id}
**Description**: Delete a bot

**Headers**: `Authorization: Bearer <token>`

**Success Response** (200):
```json
{
  "success": true,
  "message": "Bot deleted successfully"
}
```

### POST /api/bots/{bot_id}/pause
**Description**: Pause a bot

**Headers**: `Authorization: Bearer <token>`

**Success Response** (200):
```json
{
  "success": true,
  "bot_id": "bot_id",
  "status": "paused"
}
```

### POST /api/bots/{bot_id}/resume
**Description**: Resume a paused bot

**Headers**: `Authorization: Bearer <token>`

**Success Response** (200):
```json
{
  "success": true,
  "bot_id": "bot_id",
  "status": "active"
}
```

---

## Trading Endpoints

### GET /api/trades
**Description**: Get trade history for user

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `bot_id` (optional): Filter by bot
- `limit` (optional): Max results (default 100)
- `offset` (optional): Pagination offset

**Success Response** (200):
```json
{
  "success": true,
  "trades": [
    {
      "id": "trade_id",
      "bot_id": "bot_id",
      "exchange": "luno",
      "symbol": "BTC/ZAR",
      "side": "buy",
      "amount": 0.001,
      "price": 50000.0,
      "profit_loss": 5.0,
      "timestamp": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1
}
```

### GET /api/metrics
**Description**: Get trading metrics overview

**Headers**: `Authorization: Bearer <token>`

**Success Response** (200):
```json
{
  "success": true,
  "metrics": {
    "total_profit": 500.0,
    "total_capital": 10500.0,
    "active_bots": 5,
    "total_bots": 10,
    "win_rate": 65.5,
    "exposure": 15.2,
    "risk_level": "moderate"
  }
}
```

---

## AI Chat

### POST /api/ai/chat
**Description**: Send message to AI assistant

**Headers**: `Authorization: Bearer <token>`

**Request Body**:
```json
{
  "message": "What is my current portfolio status?"
}
```

**Success Response** (200):
```json
{
  "success": true,
  "response": "Your portfolio has 5 active bots with a total profit of R500...",
  "requires_confirmation": false,
  "actions": []
}
```

### POST /api/chat/message
**Description**: Alternative chat endpoint (frontend compatibility)

**Headers**: `Authorization: Bearer <token>`

**Request Body**:
```json
{
  "message": "Check my bots"
}
```

**Success Response** (200):
```json
{
  "success": true,
  "response": "You have 5 active bots...",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### GET /api/ai/chat/history
**Description**: Get chat message history

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `limit` (optional): Max messages (default 50)

**Success Response** (200):
```json
{
  "success": true,
  "messages": [
    {
      "role": "user",
      "content": "What is my status?",
      "timestamp": "2024-01-01T00:00:00Z"
    },
    {
      "role": "assistant",
      "content": "Your portfolio is performing well...",
      "timestamp": "2024-01-01T00:00:01Z"
    }
  ]
}
```

### POST /api/ai/chat/greeting
**Description**: Get welcome message and daily report

**Headers**: `Authorization: Bearer <token>`

**Success Response** (200):
```json
{
  "success": true,
  "greeting": "Welcome back, John!",
  "daily_report": {
    "summary": "Today your bots generated R50 in profit...",
    "highlights": [
      "Alpha bot gained 5%",
      "Beta bot paused due to market volatility"
    ]
  }
}
```

### POST /api/ai/chat/clear
**Description**: Clear chat history

**Headers**: `Authorization: Bearer <token>`

**Success Response** (200):
```json
{
  "success": true,
  "message": "Chat history cleared"
}
```

---

## System Endpoints

### POST /api/keys/test
**Description**: Test exchange API keys

**Headers**: `Authorization: Bearer <token>`

**Request Body**:
```json
{
  "provider": "luno",
  "api_key": "key",
  "api_secret": "secret",
  "passphrase": ""  // Required for KuCoin only
}
```

**Success Response** (200):
```json
{
  "success": true,
  "message": "API keys are valid",
  "provider": "luno"
}
```

**Error Response** (400):
```json
{
  "success": false,
  "error": "Invalid API credentials"
}
```

---

## Wallet & Fund Management

### GET /api/wallet/balances
**Description**: Get wallet balances across all exchanges

**Headers**: `Authorization: Bearer <token>`

**Success Response** (200):
```json
{
  "success": true,
  "balances": {
    "luno": {
      "ZAR": 5000.0,
      "BTC": 0.05,
      "ETH": 0.5
    },
    "binance": {
      "USDT": 1000.0,
      "BTC": 0.01
    }
  },
  "total_value_zar": 25000.0
}
```

### GET /api/wallet/transfers
**Description**: Get fund transfer history

**Headers**: `Authorization: Bearer <token>`

**Success Response** (200):
```json
{
  "success": true,
  "transfers": [
    {
      "id": "transfer_id",
      "from_provider": "luno",
      "to_provider": "binance",
      "amount": 1000.0,
      "currency": "ZAR",
      "status": "completed",
      "reason": "autopilot_rebalance",
      "correlation_id": "correlation_id",
      "timestamp": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### POST /api/wallet/transfer
**Description**: Request a fund transfer between providers

**Headers**: `Authorization: Bearer <token>`

**Request Body**:
```json
{
  "from_provider": "luno",
  "to_provider": "binance",
  "amount": 1000.0,
  "currency": "ZAR",
  "reason": "manual_allocation"
}
```

**Success Response** (200):
```json
{
  "success": true,
  "transfer": {
    "id": "transfer_id",
    "status": "pending",
    "message": "Transfer recorded. Manual action required for real exchange transfer."
  }
}
```

---

## Platform & Provider Endpoints

### GET /api/providers
**Description**: List all provider integrations

**Success Response** (200):
```json
{
  "success": true,
  "providers": [
    {
      "id": "luno",
      "type": "exchange",
      "display_name": "Luno",
      "required_fields": ["api_key", "api_secret"],
      "icon": "luno.svg",
      "description": "Luno cryptocurrency exchange"
    }
  ]
}
```

---

## Real-time Communication

### SSE: GET /api/realtime/events
**Description**: Server-Sent Events stream for real-time updates

**Headers**: `Authorization: Bearer <token>`

**Event Types**:

#### heartbeat
```
event: heartbeat
data: {"timestamp": "2024-01-01T00:00:00Z", "counter": 1}
```

#### overview_update
```
event: overview_update
data: {
  "type": "overview",
  "active_bots": 5,
  "total_bots": 10,
  "total_profit": 500.0,
  "total_capital": 10500.0,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### bot_update
```
event: bot_update
data: {
  "type": "bot_count_changed",
  "total_bots": 11,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### trade_update
```
event: trade_update
data: {
  "type": "recent_trades",
  "trades": [...],
  "count": 3,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### WebSocket: wss://<domain>/api/ws?token=<jwt>
**Description**: WebSocket connection for bidirectional real-time communication

**Connection**: 
- URL: `wss://domain.com/api/ws?token=JWT_TOKEN`
- Alternative: Send token in `Authorization: Bearer <token>` header

**Message Format**:

#### Client → Server (Ping)
```json
{
  "type": "ping",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### Server → Client (Pong)
```json
{
  "type": "pong",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### Server → Client (Bot Update)
```json
{
  "type": "bot_update",
  "bot_id": "bot_id",
  "status": "active",
  "data": {...}
}
```

#### Server → Client (Trade Executed)
```json
{
  "type": "trade_executed",
  "trade": {
    "id": "trade_id",
    "bot_id": "bot_id",
    "symbol": "BTC/ZAR",
    "side": "buy",
    "profit": 5.0
  }
}
```

#### Server → Client (Alert)
```json
{
  "type": "alert",
  "level": "warning",
  "message": "Bot Alpha paused due to high volatility"
}
```

---

## Admin Endpoints

### GET /api/admin/users
**Description**: List all users (admin only)

**Headers**: `Authorization: Bearer <token>`

**Success Response** (200):
```json
{
  "success": true,
  "users": [
    {
      "id": "user_id",
      "email": "user@example.com",
      "first_name": "John",
      "is_admin": false,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### GET /api/admin/bots
**Description**: Get all bots across all users (admin only)

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `user_id` (optional): Filter by user

**Success Response** (200):
```json
{
  "success": true,
  "bots": [...]
}
```

### POST /api/admin/bot/{bot_id}/pause
**Description**: Admin pause specific bot

**Headers**: `Authorization: Bearer <token>`

**Success Response** (200):
```json
{
  "success": true,
  "bot_id": "bot_id",
  "status": "paused"
}
```

---

## Error Schema

All error responses follow this schema:

### Standard Error Response
```json
{
  "success": false,
  "error": "Error message describing what went wrong",
  "error_code": "ERROR_CODE",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Common HTTP Status Codes
- `200 OK`: Request succeeded
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request payload
- `401 Unauthorized`: Authentication required or failed
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error (should never happen in production)

### Error Codes
- `AUTH_REQUIRED`: Authentication token required
- `AUTH_INVALID`: Invalid or expired token
- `VALIDATION_ERROR`: Request payload validation failed
- `NOT_FOUND`: Requested resource not found
- `PERMISSION_DENIED`: User lacks required permissions
- `RATE_LIMIT`: Rate limit exceeded
- `PROVIDER_ERROR`: External provider error
- `INSUFFICIENT_FUNDS`: Not enough capital for operation

---

## Nginx Configuration

For SSE and WebSocket to work behind nginx, use this configuration:

```nginx
location /api/realtime/ {
    proxy_pass http://backend:8000;
    proxy_http_version 1.1;
    proxy_set_header Connection '';
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 24h;
    chunked_transfer_encoding off;
}

location /api/ws {
    proxy_pass http://backend:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 24h;
    proxy_send_timeout 24h;
}
```

---

## Notes

1. All authenticated endpoints require `Authorization: Bearer <token>` header
2. All timestamps are in ISO 8601 format with UTC timezone
3. All monetary values are in the user's preferred currency (default: ZAR)
4. SSE connections automatically reconnect on disconnect
5. WebSocket connections use ping/pong for keep-alive
6. Admin endpoints require `is_admin: true` flag on user
7. Chat responses may include action confirmation tokens for sensitive operations
