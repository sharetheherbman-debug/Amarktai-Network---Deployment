# WebSocket Message Schemas

This document defines all WebSocket message types and their data structures for real-time communication between backend and frontend.

---

## Connection

### Connection URL
```
wss://your-domain.com/api/ws?token=<JWT_TOKEN>
```

**Authentication:** JWT token passed as query parameter

---

## Message Structure

All messages follow this base structure:

```json
{
  "type": "message_type",
  "data": { ... },
  "ts": "2026-01-14T16:30:00.000Z"
}
```

- **type**: String - Message type identifier
- **data**: Object - Message payload (structure varies by type)
- **ts**: String - ISO 8601 timestamp

---

## Message Types

### 1. Connection Status

#### `connection`
Sent when connection state changes.

```json
{
  "type": "connection",
  "data": {
    "status": "connected",
    "mode": "ws"
  },
  "ts": "2026-01-14T16:30:00.000Z"
}
```

**data fields:**
- `status`: "connected" | "disconnected" | "error"
- `mode`: "ws" | "polling"

---

### 2. Keepalive

#### `ping`
Server → Client ping to keep connection alive.

```json
{
  "type": "ping",
  "timestamp": 1705251000000
}
```

#### `pong`
Client → Server response to ping.

```json
{
  "type": "pong",
  "timestamp": 1705251000000
}
```

---

### 3. Trades

#### `trades`
New trade executed or trade status updated.

```json
{
  "type": "trades",
  "data": {
    "id": "trade_12345",
    "bot_id": "bot_abc",
    "platform": "luno",
    "symbol": "BTC-ZAR",
    "side": "buy",
    "quantity": 0.001,
    "price": 850000,
    "total": 850,
    "fee": 2.55,
    "status": "filled",
    "pnl": null,
    "timestamp": "2026-01-14T16:30:00.000Z"
  },
  "ts": "2026-01-14T16:30:00.000Z"
}
```

**data fields:**
- `id`: Trade unique identifier
- `bot_id`: Bot that executed trade
- `platform`: Exchange name (luno, binance, kucoin, kraken, valr)
- `symbol`: Trading pair
- `side`: "buy" | "sell"
- `quantity`: Amount traded
- `price`: Execution price
- `total`: Total value (quantity * price)
- `fee`: Trading fee
- `status`: "pending" | "filled" | "cancelled" | "failed"
- `pnl`: Profit/loss if closing position
- `timestamp`: Trade execution time

---

### 4. Bots

#### `bots`
Bot status or configuration changed.

```json
{
  "type": "bots",
  "data": {
    "id": "bot_abc",
    "name": "BTC Scalper",
    "platform": "luno",
    "symbol": "BTC-ZAR",
    "status": "running",
    "trading_mode": "paper",
    "risk_mode": "conservative",
    "capital": 5000,
    "pnl": 150.50,
    "trades_count": 42,
    "win_rate": 0.68,
    "last_trade": "2026-01-14T16:25:00.000Z"
  },
  "ts": "2026-01-14T16:30:00.000Z"
}
```

**data fields:**
- `id`: Bot unique identifier
- `name`: Bot display name
- `platform`: Exchange name
- `symbol`: Trading pair
- `status`: "running" | "stopped" | "paused" | "error"
- `trading_mode`: "paper" | "live"
- `risk_mode`: "conservative" | "moderate" | "aggressive"
- `capital`: Allocated capital
- `pnl`: Total profit/loss
- `trades_count`: Number of trades executed
- `win_rate`: Percentage of winning trades (0-1)
- `last_trade`: Last trade timestamp

---

### 5. Balances

#### `balances`
Wallet balance updated.

```json
{
  "type": "balances",
  "data": {
    "platform": "luno",
    "balances": {
      "ZAR": {
        "free": 10000.00,
        "locked": 500.00,
        "total": 10500.00
      },
      "BTC": {
        "free": 0.025,
        "locked": 0.001,
        "total": 0.026
      }
    },
    "total_value_zar": 32500.00
  },
  "ts": "2026-01-14T16:30:00.000Z"
}
```

**data fields:**
- `platform`: Exchange name or "all" for aggregated
- `balances`: Object mapping asset → balance details
  - `free`: Available balance
  - `locked`: Balance in open orders
  - `total`: Total balance
- `total_value_zar`: Total portfolio value in ZAR

---

### 6. Decisions

#### `decisions`
AI trading decision made.

```json
{
  "type": "decisions",
  "data": {
    "id": "decision_xyz",
    "bot_id": "bot_abc",
    "symbol": "BTC-ZAR",
    "platform": "luno",
    "decision": "buy",
    "confidence": 0.85,
    "reasoning": "Strong bullish momentum, RSI oversold",
    "market_data": {
      "price": 850000,
      "volume_24h": 125000000,
      "rsi": 35,
      "macd": "bullish"
    },
    "regime_state": "trending_up",
    "component_scores": {
      "technical": 0.82,
      "sentiment": 0.78,
      "risk": 0.90
    },
    "sizing": {
      "quantity": 0.001,
      "capital": 850,
      "risk_per_trade": 0.02
    },
    "stops": {
      "stop_loss": 825000,
      "take_profit": 875000
    },
    "timestamp": "2026-01-14T16:30:00.000Z"
  },
  "ts": "2026-01-14T16:30:00.000Z"
}
```

**data fields:**
- `id`: Decision unique identifier
- `bot_id`: Bot making decision
- `symbol`: Trading pair
- `platform`: Exchange name
- `decision`: "buy" | "sell" | "hold"
- `confidence`: Confidence score (0-1)
- `reasoning`: Human-readable explanation
- `market_data`: Current market snapshot
- `regime_state`: Market regime
- `component_scores`: Breakdown by analysis component
- `sizing`: Position sizing details
- `stops`: Stop loss and take profit levels
- `timestamp`: Decision timestamp

---

### 7. Metrics

#### `metrics`
System performance metrics updated.

```json
{
  "type": "metrics",
  "data": {
    "total_pnl": 1250.50,
    "total_pnl_percent": 12.5,
    "active_bots": 5,
    "total_bots": 8,
    "total_trades": 342,
    "win_rate": 0.68,
    "exposure": 0.45,
    "risk_level": "moderate",
    "uptime_seconds": 86400,
    "trades_per_hour": 2.5
  },
  "ts": "2026-01-14T16:30:00.000Z"
}
```

---

### 8. Whale Activity

#### `whale`
Large whale transaction detected.

```json
{
  "type": "whale",
  "data": {
    "coin": "BTC",
    "platform": "binance",
    "flow_type": "inflow",
    "amount": 150.5,
    "value_usd": 6500000,
    "timestamp": "2026-01-14T16:30:00.000Z",
    "signal": "bullish"
  },
  "ts": "2026-01-14T16:30:00.000Z"
}
```

---

### 9. Alerts

#### `alerts`
System alert triggered.

```json
{
  "type": "alerts",
  "data": {
    "id": "alert_123",
    "severity": "warning",
    "category": "risk",
    "title": "High Exposure Detected",
    "message": "Total exposure at 75% - consider reducing positions",
    "bot_id": "bot_abc",
    "platform": "luno",
    "action_required": true,
    "timestamp": "2026-01-14T16:30:00.000Z"
  },
  "ts": "2026-01-14T16:30:00.000Z"
}
```

**severity levels:** "info" | "warning" | "error" | "critical"

---

### 10. System Health

#### `system_health`
System health status update.

```json
{
  "type": "system_health",
  "data": {
    "status": "healthy",
    "uptime": 86400,
    "cpu_percent": 45.5,
    "memory_percent": 62.3,
    "disk_percent": 35.0,
    "database": "connected",
    "redis": "connected",
    "exchange_connections": {
      "luno": "connected",
      "binance": "connected",
      "kucoin": "connected",
      "kraken": "connected",
      "valr": "connected"
    },
    "last_trade": "2026-01-14T16:25:00.000Z",
    "error_rate": 0.01
  },
  "ts": "2026-01-14T16:30:00.000Z"
}
```

---

### 11. Wallet

#### `wallet`
Wallet event (deposit, withdrawal, etc.)

```json
{
  "type": "wallet",
  "data": {
    "event": "deposit_confirmed",
    "platform": "luno",
    "asset": "BTC",
    "amount": 0.01,
    "address": "bc1q...",
    "txid": "abc123...",
    "confirmations": 3,
    "status": "confirmed"
  },
  "ts": "2026-01-14T16:30:00.000Z"
}
```

---

### 12. AI Tasks

#### `ai_tasks`
AI tool task status update.

```json
{
  "type": "ai_tasks",
  "data": {
    "task_id": "task_xyz",
    "task_type": "bodyguard_check",
    "status": "completed",
    "progress": 1.0,
    "result": {
      "checks_passed": 15,
      "checks_failed": 0,
      "issues": []
    },
    "started_at": "2026-01-14T16:28:00.000Z",
    "completed_at": "2026-01-14T16:30:00.000Z"
  },
  "ts": "2026-01-14T16:30:00.000Z"
}
```

**task_type options:**
- `bodyguard_check`
- `learning_run`
- `bot_evolution`
- `insights_generation`
- `prediction`
- `profit_reinvestment`

**status options:** "queued" | "running" | "completed" | "failed"

---

## Error Handling

### Error Message

```json
{
  "type": "error",
  "data": {
    "code": "INTERNAL_ERROR",
    "message": "Failed to process request",
    "details": "..."
  },
  "ts": "2026-01-14T16:30:00.000Z"
}
```

---

## Frontend Usage Example

```javascript
import realtimeClient from './lib/realtime';

// Connect
const token = localStorage.getItem('token');
realtimeClient.connect(token);

// Subscribe to trades
realtimeClient.on('trades', (trade) => {
  console.log('New trade:', trade);
  // Update UI
});

// Subscribe to bots
realtimeClient.on('bots', (bot) => {
  console.log('Bot updated:', bot);
  // Update bot list
});

// Get connection status
const status = realtimeClient.getStatus();
console.log('Connection:', status.mode, status.connected);

// Disconnect
realtimeClient.disconnect();
```

---

## Backend Implementation Notes

1. **Authentication**: Validate JWT token before accepting WebSocket connection
2. **User Isolation**: Only send user's own data (except admin users)
3. **Rate Limiting**: Limit message frequency to prevent spam
4. **Ping/Pong**: Send ping every 30s, expect pong within 10s
5. **Graceful Degradation**: If WebSocket fails, frontend should fall back to polling
6. **Message Ordering**: Include timestamp for proper ordering
7. **Reconnection**: Frontend should reconnect with exponential backoff

---

## Testing WebSocket

### Using `websocat` (CLI tool)
```bash
websocat "ws://localhost:8000/api/ws?token=YOUR_JWT_TOKEN"
```

### Using Browser Console
```javascript
const ws = new WebSocket('ws://localhost:8000/api/ws?token=YOUR_JWT_TOKEN');
ws.onmessage = (e) => console.log(JSON.parse(e.data));
ws.onopen = () => console.log('Connected');
ws.onerror = (e) => console.error('Error:', e);
```

---

## Version History

- **v1.0** (2026-01-14): Initial schema definition
