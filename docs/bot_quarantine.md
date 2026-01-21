# Bot Quarantine & Auto-Retraining System

## Overview

The Bot Quarantine system ensures **no bots remain paused indefinitely** by implementing a progressive quarantine policy with automatic retraining and regeneration. When bots pause repeatedly due to errors or poor performance, they enter quarantine for progressively longer periods, eventually being deleted and replaced if they continue to fail.

### Key Features

- **Progressive Quarantine**: 1h → 3h → 24h → delete & regenerate
- **Auto-Retraining**: Bots automatically redeploy after quarantine timeout
- **Bot Regeneration**: Failed bots replaced with new instances
- **Real-time Monitoring**: Track quarantine status via API
- **Audit Trail**: Complete history of quarantine events

---

## Quarantine Policy

### 4-Strike System

| Strike | Duration | Action | Auto-Resume |
|--------|----------|--------|-------------|
| **1st Pause** | 1 hour | Quarantine + retrain | ✓ Yes |
| **2nd Pause** | 3 hours | Quarantine + retrain | ✓ Yes |
| **3rd Pause** | 24 hours | Quarantine + retrain | ✓ Yes |
| **4th Pause** | N/A | **Delete & regenerate** | ✓ New bot created |

### Duration Configuration

Located in `backend/services/bot_quarantine.py`:

```python
QUARANTINE_DURATIONS = {
    1: 3600,      # 1st pause: 1 hour (3600 seconds)
    2: 10800,     # 2nd pause: 3 hours (10800 seconds)
    3: 86400,     # 3rd pause: 24 hours (86400 seconds)
    4: None       # 4th pause: delete & regenerate
}
```

### Customizing Durations

To adjust quarantine timeouts:

```python
# Edit backend/services/bot_quarantine.py
QUARANTINE_DURATIONS = {
    1: 1800,      # 30 minutes
    2: 7200,      # 2 hours
    3: 43200,     # 12 hours
    4: None       # delete & regenerate
}
```

---

## When Bots Enter Quarantine

### Automatic Triggers

Bots enter quarantine automatically when paused for:

1. **Circuit Breaker Triggers**
   - Daily loss exceeds threshold (default: 10%)
   - Max drawdown exceeded (default: 15%)
   - Consecutive losses (5+ in a row)

2. **Exchange Errors**
   - API rate limit exceeded
   - Authentication failures
   - Order rejection errors

3. **Risk Violations**
   - Position size exceeds limit
   - Insufficient balance
   - Trade validation failures

4. **AI Service Failures**
   - AI prediction errors
   - Model loading failures
   - Timeout errors

### Manual Triggers

Admins can manually quarantine bots:

```bash
curl -X POST http://localhost:8000/api/admin/bots/{bot_id}/quarantine \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Manual admin intervention - suspicious activity"
  }'
```

---

## Auto-Retraining Process

### Quarantine Flow

```
Bot Paused
    ↓
Increment quarantine_count
    ↓
Is count >= 4?
    ├─ Yes → Mark for deletion
    │         Create replacement bot
    │         Delete old bot + trades
    │
    └─ No → Calculate quarantine duration
            Set retraining_until timestamp
            Update status to "quarantined"
            ↓
            Wait for timeout
            ↓
            Change status to "active"
            Clear quarantine fields
            Emit realtime event
```

### Database Fields During Quarantine

```javascript
// Bot in quarantine (1st pause)
{
  "id": "bot_uuid",
  "user_id": "user_uuid",
  "name": "BTC Trader",
  "status": "quarantined",
  "quarantine_count": 1,
  "quarantine_reason": "CIRCUIT_BREAKER_DAILY_LOSS",
  "quarantined_at": "2024-01-15T10:30:00Z",
  "retraining_until": "2024-01-15T11:30:00Z",  // 1 hour later
  "quarantine_duration_seconds": 3600
}
```

### After Retraining Completes

```javascript
// Bot auto-resumed after quarantine
{
  "id": "bot_uuid",
  "user_id": "user_uuid",
  "name": "BTC Trader",
  "status": "active",  // Changed from "quarantined"
  "quarantine_count": 1,  // Preserved for tracking
  "redeployed_at": "2024-01-15T11:30:00Z"
  // quarantine_reason, quarantined_at, retraining_until removed
}
```

---

## Bot Regeneration (4th Pause)

### Deletion Process

When a bot reaches its 4th pause:

1. **Mark for Deletion**
   ```javascript
   {
     "status": "marked_for_deletion",
     "quarantine_count": 4,
     "deletion_scheduled_at": "2024-01-15T10:30:00Z",
     "deletion_reason": "Exceeded max quarantine attempts"
   }
   ```

2. **Delete Bot & Trades**
   ```python
   # Delete bot document
   await db.bots_collection.delete_one({"id": bot_id})
   
   # Delete all trades
   await db.trades_collection.delete_many({"bot_id": bot_id})
   ```

3. **Create Replacement Bot**
   ```python
   new_bot = {
       "id": new_bot_id,
       "user_id": user_id,
       "name": original_name + " (Auto-Regenerated)",
       "exchange": original_exchange,
       "mode": "paper",  # Always start in paper mode
       "status": "active",
       "initial_capital": original_initial_capital,
       "current_capital": original_initial_capital,
       "quarantine_count": 0,  # Reset counter
       "created_at": now,
       "auto_generated": True,
       "replaced_bot_id": bot_id
   }
   ```

### Replacement Bot Properties

| Property | Value | Reason |
|----------|-------|--------|
| Name | Original + "(Auto-Regenerated)" | Clear identification |
| Mode | Paper | Safe restart |
| Capital | Original initial_capital | Fresh start |
| Quarantine Count | 0 | Clean slate |
| Status | Active | Ready to trade |
| auto_generated | True | Tracking flag |
| replaced_bot_id | Original bot ID | Audit trail |

---

## API Endpoints

### Get Quarantine Status

```bash
GET /api/quarantine/status/{bot_id}
```

**Response:**
```json
{
  "bot_id": "abc123",
  "name": "BTC Trader",
  "status": "quarantined",
  "quarantine_count": 2,
  "quarantine_reason": "CIRCUIT_BREAKER_DAILY_LOSS",
  "quarantined_at": "2024-01-15T10:30:00Z",
  "retraining_until": "2024-01-15T13:30:00Z",
  "time_remaining_seconds": 7200,
  "time_remaining_human": "2 hours",
  "next_action": "auto_resume"
}
```

### Get Quarantine History

```bash
GET /api/quarantine/history?user_id={user_id}&limit=50
```

**Response:**
```json
{
  "history": [
    {
      "bot_id": "abc123",
      "bot_name": "BTC Trader",
      "event": "quarantined",
      "quarantine_count": 2,
      "reason": "CIRCUIT_BREAKER_DAILY_LOSS",
      "timestamp": "2024-01-15T10:30:00Z",
      "duration_seconds": 10800
    },
    {
      "bot_id": "abc123",
      "bot_name": "BTC Trader",
      "event": "redeployed",
      "timestamp": "2024-01-15T13:30:00Z"
    }
  ],
  "total": 2
}
```

### Get Quarantine Configuration

```bash
GET /api/quarantine/config
```

**Response:**
```json
{
  "quarantine_durations": {
    "1": 3600,
    "2": 10800,
    "3": 86400,
    "4": null
  },
  "check_interval_seconds": 60,
  "max_strikes": 4,
  "policy": "progressive"
}
```

### Manually Quarantine Bot (Admin)

```bash
POST /api/admin/bots/{bot_id}/quarantine
Content-Type: application/json
Authorization: Bearer {admin_token}

{
  "reason": "Manual intervention - suspicious behavior"
}
```

**Response:**
```json
{
  "success": true,
  "bot_id": "abc123",
  "quarantine_count": 2,
  "quarantine_duration_seconds": 10800,
  "retraining_until": "2024-01-15T13:30:00Z",
  "action": "retraining",
  "message": "Bot in retraining for 3.0 hours"
}
```

---

## Frontend UI Guide

### Viewing Quarantined Bots

Display quarantine status in bot list:

```javascript
// React component example
const BotStatusBadge = ({ bot }) => {
  if (bot.status === 'quarantined') {
    return (
      <Badge color="orange">
        🔒 Quarantined ({bot.quarantine_count}/4)
      </Badge>
    );
  }
  if (bot.status === 'marked_for_deletion') {
    return <Badge color="red">🗑️ Deleting...</Badge>;
  }
  return <Badge color="green">✓ Active</Badge>;
};
```

### Countdown Timer

Show time remaining until retraining completes:

```javascript
import { useEffect, useState } from 'react';

const QuarantineCountdown = ({ retrainingUntil }) => {
  const [timeLeft, setTimeLeft] = useState('');
  
  useEffect(() => {
    const interval = setInterval(() => {
      const now = new Date();
      const target = new Date(retrainingUntil);
      const diff = target - now;
      
      if (diff <= 0) {
        setTimeLeft('Retraining complete');
        clearInterval(interval);
        return;
      }
      
      const hours = Math.floor(diff / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diff % (1000 * 60)) / 1000);
      
      setTimeLeft(`${hours}h ${minutes}m ${seconds}s`);
    }, 1000);
    
    return () => clearInterval(interval);
  }, [retrainingUntil]);
  
  return <span>{timeLeft}</span>;
};
```

### Quarantine Progress Bar

Visual indicator of quarantine strikes:

```javascript
const QuarantineProgress = ({ quarantineCount }) => {
  const maxStrikes = 4;
  const percentage = (quarantineCount / maxStrikes) * 100;
  
  const getColor = () => {
    if (quarantineCount === 1) return 'yellow';
    if (quarantineCount === 2) return 'orange';
    if (quarantineCount === 3) return 'red';
    return 'darkred';
  };
  
  return (
    <div>
      <div className="progress-bar">
        <div 
          className="progress-fill" 
          style={{ 
            width: `${percentage}%`,
            backgroundColor: getColor()
          }}
        />
      </div>
      <p>Strike {quarantineCount}/{maxStrikes}</p>
    </div>
  );
};
```

---

## Database Fields

### Bot Document During Quarantine

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `status` | string | Current bot status | "quarantined" |
| `quarantine_count` | int | Number of quarantine events | 2 |
| `quarantine_reason` | string | Why bot was quarantined | "CIRCUIT_BREAKER_DAILY_LOSS" |
| `quarantined_at` | ISO8601 | When quarantine started | "2024-01-15T10:30:00Z" |
| `retraining_until` | ISO8601 | When retraining completes | "2024-01-15T13:30:00Z" |
| `quarantine_duration_seconds` | int | Duration in seconds | 10800 |

### Bot Document Marked for Deletion

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `status` | string | Bot status | "marked_for_deletion" |
| `quarantine_count` | int | Strike count | 4 |
| `deletion_scheduled_at` | ISO8601 | When deletion was scheduled | "2024-01-15T10:30:00Z" |
| `deletion_reason` | string | Why bot is being deleted | "Exceeded max quarantine attempts" |

### Replacement Bot Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `auto_generated` | bool | Bot was auto-created | true |
| `replaced_bot_id` | string | Original bot ID | "old_bot_uuid" |
| `name` | string | Bot name with suffix | "BTC Trader (Auto-Regenerated)" |
| `quarantine_count` | int | Reset to 0 | 0 |

---

## Configuration

### Service Configuration

Edit `backend/services/bot_quarantine.py`:

```python
class BotQuarantineService:
    def __init__(self):
        self.running = False
        self.check_interval = 60  # Check every 60 seconds (1 minute)
```

### Change Check Interval

```python
# Check more frequently (every 30 seconds)
self.check_interval = 30

# Check less frequently (every 5 minutes)
self.check_interval = 300
```

### Environment Variables

```bash
# .env file
QUARANTINE_CHECK_INTERVAL=60  # seconds
QUARANTINE_ENABLED=true
QUARANTINE_MAX_STRIKES=4
```

---

## Manual Intervention

### Manually Resume Quarantined Bot

```bash
# Admin override - resume bot immediately
curl -X POST http://localhost:8000/api/admin/bots/{bot_id}/resume \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "force": true,
    "reason": "Admin override - bot fixed"
  }'
```

### Reset Quarantine Counter

```bash
# Admin action - reset strikes to 0
curl -X POST http://localhost:8000/api/admin/bots/{bot_id}/reset-quarantine \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Python:**
```python
# Direct database update
await db.bots_collection.update_one(
    {"id": bot_id},
    {
        "$set": {
            "quarantine_count": 0,
            "status": "active"
        },
        "$unset": {
            "quarantine_reason": "",
            "quarantined_at": "",
            "retraining_until": "",
            "quarantine_duration_seconds": ""
        }
    }
)
```

### Prevent Bot Deletion

```bash
# Stop bot from being deleted (downgrade to 3rd strike)
curl -X POST http://localhost:8000/api/admin/bots/{bot_id}/prevent-deletion \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Python:**
```python
await db.bots_collection.update_one(
    {"id": bot_id, "status": "marked_for_deletion"},
    {
        "$set": {
            "status": "quarantined",
            "quarantine_count": 3,
            "retraining_until": (datetime.now() + timedelta(hours=24)).isoformat()
        },
        "$unset": {
            "deletion_scheduled_at": "",
            "deletion_reason": ""
        }
    }
)
```

---

## Monitoring Quarantine Activity

### Get All Quarantined Bots

```bash
curl http://localhost:8000/api/admin/bots/quarantined \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Response:**
```json
{
  "quarantined_bots": [
    {
      "bot_id": "abc123",
      "name": "BTC Trader",
      "user_id": "user123",
      "quarantine_count": 2,
      "quarantined_at": "2024-01-15T10:30:00Z",
      "retraining_until": "2024-01-15T13:30:00Z",
      "time_remaining_seconds": 7200
    }
  ],
  "total": 1
}
```

### Monitor Service Status

```bash
curl http://localhost:8000/api/admin/services/quarantine/status \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Response:**
```json
{
  "service": "bot_quarantine",
  "status": "running",
  "check_interval_seconds": 60,
  "last_check": "2024-01-15T10:29:00Z",
  "bots_checked": 45,
  "bots_redeployed": 2,
  "bots_deleted": 1
}
```

### Realtime Events

Subscribe to quarantine events via WebSocket:

```javascript
// Frontend WebSocket subscription
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.event === 'bot_quarantined') {
    console.log(`Bot ${data.bot_id} quarantined (strike ${data.quarantine_count})`);
    updateUI(data);
  }
  
  if (data.event === 'bot_redeployed') {
    console.log(`Bot ${data.bot_id} retraining complete - redeployed`);
    updateUI(data);
  }
  
  if (data.event === 'bot_regenerated') {
    console.log(`Bot ${data.old_bot_id} replaced with ${data.new_bot_id}`);
    updateUI(data);
  }
};
```

---

## Logging & Audit Trail

### Log Messages

```log
[INFO] 🔒 Bot abc123 entering quarantine #2 for 3.0 hours
[INFO] ✅ Bot abc123 completed retraining - redeploying
[WARNING] 🗑️ Bot abc123 reached 4th pause - marking for deletion
[INFO] 🤖 Auto-generating replacement bot for user user123
[INFO] ✅ Created replacement bot def456
```

### Audit Log Structure

```javascript
{
  "event_type": "bot_quarantined",
  "bot_id": "abc123",
  "user_id": "user123",
  "quarantine_count": 2,
  "reason": "CIRCUIT_BREAKER_DAILY_LOSS",
  "duration_seconds": 10800,
  "retraining_until": "2024-01-15T13:30:00Z",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## Troubleshooting

### Issue: Bot stuck in quarantine

**Symptoms**: Bot shows "quarantined" but timeout passed

**Solution**:
```python
# Check if service is running
from services.bot_quarantine import quarantine_service
print(quarantine_service.running)  # Should be True

# Manually trigger timeout check
await quarantine_service.check_quarantine_timeouts()
```

### Issue: Bot deleted but no replacement created

**Symptoms**: Bot marked for deletion but no new bot

**Solution**:
```python
# Manually trigger deletion handler
await quarantine_service.handle_bot_deletions()

# Check logs for errors
tail -f logs/backend.log | grep "Auto-generating"
```

### Issue: Quarantine counter not incrementing

**Symptoms**: Bot pauses but counter stays at 0

**Solution**:
```python
# Ensure pause goes through quarantine service
from services.bot_quarantine import quarantine_service

# Correct way to pause bot
await quarantine_service.quarantine_bot(
    bot_id=bot_id,
    reason="CIRCUIT_BREAKER_DAILY_LOSS"
)

# NOT directly updating status
# await db.bots_collection.update_one({"id": bot_id}, {"$set": {"status": "paused"}})
```

### Issue: Service not auto-starting

**Symptoms**: Bots never redeploy after timeout

**Solution**:
```python
# Check if service is started in main.py
from services.bot_quarantine import quarantine_service

@app.on_event("startup")
async def startup():
    # Should include:
    asyncio.create_task(quarantine_service.run())
```

---

## Best Practices

1. **Monitor Strike Counts**: Watch bots approaching 4th strike
2. **Investigate Patterns**: If multiple bots quarantined, check system issues
3. **Adjust Thresholds**: Tune circuit breaker limits to reduce false positives
4. **Review Regenerations**: Ensure replaced bots perform better
5. **Backup Before Deletion**: Auto-export bot config before 4th strike

---

## See Also

- [Paper Trading System](paper_trading.md)
- [Admin Panel Guide](admin_panel.md)
- [Circuit Breaker Documentation](../DEPLOYMENT_GUIDE.md#circuit-breaker)
- [Bot Lifecycle Management](../DEPLOYMENT_GUIDE.md#bot-lifecycle)
