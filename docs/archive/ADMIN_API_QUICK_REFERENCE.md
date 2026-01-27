# Admin Panel API - Quick Reference Guide

## Authentication
All endpoints require admin authentication via Bearer token:
```bash
Authorization: Bearer <admin_jwt_token>
```

Non-admin users receive `403 Forbidden`.

---

## 👥 User Management APIs

### 1. Get All Users
```bash
GET /api/admin/users
```

**Response:**
```json
{
  "users": [
    {
      "user_id": "abc123",
      "username": "John Doe",
      "email": "john@example.com",
      "role": "admin",
      "is_active": true,
      "created_at": "2024-01-15T10:30:00Z",
      "last_seen": "2024-01-20T14:22:00Z",
      "api_keys": {
        "openai": true,
        "luno": false,
        "binance": true,
        "kucoin": false,
        "valr": false,
        "ovex": false
      },
      "bots_summary": {
        "total": 5,
        "by_exchange": {"binance": 3, "luno": 2},
        "by_mode": {"paper": 3, "live": 1, "paused": 1}
      },
      "resource_usage": {
        "trades_last_24h": 42,
        "total_trades": 1250
      }
    }
  ],
  "total_count": 1
}
```

---

### 2. Reset User Password
```bash
POST /api/admin/users/{user_id}/reset-password
```

**Response:**
```json
{
  "success": true,
  "new_password": "aB3$xY9!mN2z",
  "message": "Password reset successfully. Email sent (if configured).",
  "user_id": "abc123"
}
```

**Notes:**
- Password is auto-generated (12 characters)
- Contains uppercase, lowercase, digits, symbols
- User should change password on next login

---

### 3. Block User
```bash
POST /api/admin/users/{user_id}/block
Content-Type: application/json

{
  "reason": "Suspicious trading activity"
}
```

**Response:**
```json
{
  "success": true,
  "user_id": "abc123",
  "is_active": false,
  "message": "User blocked. 3 bots paused."
}
```

**Side Effects:**
- Sets `is_active = false`
- Pauses all active bots
- Records `blocked_reason`
- Logs to audit trail

---

### 4. Unblock User
```bash
POST /api/admin/users/{user_id}/unblock
```

**Response:**
```json
{
  "success": true,
  "user_id": "abc123",
  "is_active": true,
  "message": "User unblocked"
}
```

---

### 5. Delete User
```bash
DELETE /api/admin/users/{user_id}
Content-Type: application/json

{
  "confirm": true
}
```

**Response:**
```json
{
  "success": true,
  "deleted": {
    "user": 1,
    "bots": 5,
    "trades": 234,
    "api_keys": 3
  },
  "message": "User abc123 and all associated data deleted"
}
```

**Safety:**
- Requires `confirm: true` in request body
- Admin cannot delete themselves (returns 400)
- Cascades to: bots, trades, API keys, alerts

---

### 6. Force Logout User
```bash
POST /api/admin/users/{user_id}/logout
```

**Response:**
```json
{
  "success": true,
  "message": "User forcefully logged out",
  "user_id": "abc123",
  "sessions_deleted": 2
}
```

**Mechanism:**
- Deletes all sessions from `sessions_collection`
- Sets `force_logout` flag (checked during auth)
- User must login again

---

## 🤖 Bot Override APIs

### 1. Get All Bots
```bash
GET /api/admin/bots?mode=paper&user_id=abc123
```

**Query Params:**
- `mode` (optional): Filter by "paper" or "live"
- `user_id` (optional): Filter by user

**Response:**
```json
{
  "bots": [
    {
      "bot_id": "bot_xyz",
      "name": "Bitcoin Trader",
      "user_id": "abc123",
      "username": "John Doe",
      "email": "john@example.com",
      "exchange": "binance",
      "mode": "paper",
      "status": "running",
      "pause_reason": null,
      "paused_at": null,
      "current_capital": 1000.50,
      "profit_loss": 25.30
    }
  ],
  "total": 1
}
```

---

### 2. Change Bot Mode
```bash
POST /api/admin/bots/{bot_id}/mode
Content-Type: application/json

{
  "mode": "live"
}
```

**Response:**
```json
{
  "success": true,
  "bot_id": "bot_xyz",
  "mode": "live",
  "message": "Bot mode changed to live"
}
```

**Validation:**
- Checks `ENABLE_LIVE_TRADING` environment variable
- For live mode: Verifies user has API keys for exchange
- Returns 403 if live trading disabled globally
- Returns 400 if API keys missing

---

### 3. Pause Bot
```bash
POST /api/admin/bots/{bot_id}/pause
```

**Response:**
```json
{
  "success": true,
  "bot_id": "bot_xyz",
  "status": "paused",
  "message": "Bot paused by admin"
}
```

**Details:**
- Sets `status = "paused"`
- Sets `pause_reason = "MANUAL_ADMIN_PAUSE"`
- Records `paused_at` timestamp
- Logs to audit trail

---

### 4. Resume Bot
```bash
POST /api/admin/bots/{bot_id}/resume
```

**Response:**
```json
{
  "success": true,
  "bot_id": "bot_xyz",
  "status": "running",
  "message": "Bot resumed by admin"
}
```

**Details:**
- Sets `status = "running"`
- Clears `pause_reason` and `paused_at`
- Records `resumed_at` timestamp

---

### 5. Restart Bot
```bash
POST /api/admin/bots/{bot_id}/restart
```

**Response:**
```json
{
  "success": false,
  "message": "Auto-restart not supported. Use pause/resume instead.",
  "bot_id": "bot_xyz"
}
```

**Status:**
- Placeholder endpoint ready for scheduler integration
- Returns "not supported" message
- Logs action to audit trail

**Future Integration:**
```python
# TODO: Integrate with trading_scheduler.py
await trading_scheduler.restart_bot(bot_id)
```

---

### 6. Change Bot Exchange
```bash
POST /api/admin/bots/{bot_id}/exchange
Content-Type: application/json

{
  "exchange": "kucoin"
}
```

**Response:**
```json
{
  "success": true,
  "bot_id": "bot_xyz",
  "exchange": "kucoin",
  "message": "Bot exchange changed to kucoin"
}
```

**Validation:**
- Valid exchanges: luno, binance, kucoin, valr, ovex
- Verifies user has API keys for new exchange
- Returns 400 if invalid exchange or keys missing

---

## 🔐 Security & Error Handling

### Error Responses

**401 Unauthorized** (Missing/invalid token):
```json
{
  "detail": "Could not validate credentials"
}
```

**403 Forbidden** (Not admin):
```json
{
  "detail": "Admin access required"
}
```

**404 Not Found** (User/bot doesn't exist):
```json
{
  "detail": "User not found"
}
```

**400 Bad Request** (Validation error):
```json
{
  "detail": "User has no API keys configured for binance"
}
```

**500 Internal Server Error**:
```json
{
  "detail": "Internal server error message"
}
```

---

## 📊 Audit Trail

Every admin action is logged to `audit_logs_collection`:

```json
{
  "admin_id": "admin_user_id",
  "admin_username": "admin@example.com",
  "action": "block_user",
  "target_type": "user",
  "target_id": "abc123",
  "details": {
    "reason": "Suspicious activity",
    "bots_paused": 3
  },
  "timestamp": "2024-01-20T15:45:30Z",
  "ip_address": "192.168.1.100"
}
```

**Logged Actions:**
- reset_password
- block_user
- unblock_user
- delete_user
- force_logout
- change_bot_mode
- pause_bot
- resume_bot
- restart_bot
- change_bot_exchange

---

## 🧪 Testing Examples

### cURL Examples

```bash
# Get all users
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/admin/users

# Block user
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason":"Test block"}' \
  http://localhost:8000/api/admin/users/abc123/block

# Change bot to live
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mode":"live"}' \
  http://localhost:8000/api/admin/bots/bot_xyz/mode
```

### Python Example

```python
import requests

BASE_URL = "http://localhost:8000"
headers = {"Authorization": f"Bearer {admin_token}"}

# Get all users
response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
users = response.json()["users"]

# Reset password
response = requests.post(
    f"{BASE_URL}/api/admin/users/{user_id}/reset-password",
    headers=headers
)
new_password = response.json()["new_password"]
print(f"New password: {new_password}")

# Pause bot
response = requests.post(
    f"{BASE_URL}/api/admin/bots/{bot_id}/pause",
    headers=headers
)
print(response.json())
```

---

## 📋 Checklist for Integration

- [ ] Ensure `ENABLE_LIVE_TRADING` env var is set correctly
- [ ] Verify admin users have `is_admin=true` or `role="admin"`
- [ ] Set up `audit_logs_collection` in MongoDB
- [ ] Configure email service for password reset notifications (optional)
- [ ] Implement session storage in `sessions_collection` for logout
- [ ] Test all endpoints with admin and non-admin users
- [ ] Set up monitoring for audit logs
- [ ] Document admin procedures and policies

---

## 🎯 Best Practices

1. **Password Resets**: Share generated passwords via secure channel (not email)
2. **User Deletion**: Always confirm with team before deleting users
3. **Bot Mode Changes**: Verify exchange balance before enabling live mode
4. **Audit Logs**: Regularly review for suspicious admin activity
5. **Force Logout**: Use only when necessary (security incident, account takeover)
6. **Block/Unblock**: Document reasons for blocking in the request

---

**Implementation Complete** ✅  
For detailed implementation docs, see: `ADMIN_PANEL_IMPLEMENTATION.md`
