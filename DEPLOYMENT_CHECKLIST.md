# Production Go-Live Deployment Checklist

## Pre-Deployment Verification

### 1. Code Compilation Check
```bash
cd /home/runner/work/Amarktai-Network---Deployment/Amarktai-Network---Deployment
python3 -m py_compile backend/database.py backend/routes/system.py backend/routes/api_key_management.py backend/server.py
```
Expected: No syntax errors

### 2. Config Import Test
```bash
cd /path/to/Amarktai-Network---Deployment
python3 -c "import sys; sys.path.insert(0, 'backend'); from config import PAPER_TRAINING_DAYS; print('✅ Config OK')"
```
Expected: `✅ Config OK`

### 3. Server Startup Test
```bash
cd backend
python3 server.py
```
Expected: Server starts without import errors. Look for:
- ✅ MongoDB connection successful
- ✅ All collection references initialized
- ✅ Core routers mounted (system, trades, health, profits)
- ⚠️ Note: Some optional routers may fail to mount - this is OK if core routers are mounted

### 4. Run Production Verifiers
```bash
# Local test (ensure backend is running on port 8000)
python3 scripts/verify_production_ready.py http://127.0.0.1:8000

# Or against VPS
python3 scripts/verify_production_ready.py http://your-vps-ip:8000
python3 scripts/verify_go_live.py http://your-vps-ip:8000
```
Expected: All tests pass

## Critical Endpoints to Test

### System Endpoints (Protected)
```bash
# Get live eligibility - MUST return stable schema
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/system/live-eligibility
# Expected: {"live_allowed": false, "reasons": ["..."]}

# Get emergency stop status - MUST return stable schema
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/system/emergency-stop/status
# Expected: {"is_emergency_stop_active": false, "reason": null, "updated_at": null}

# Get system mode - MUST never 500
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/system/mode
# Expected: {"paperTrading": false, "liveTrading": false, ...}

# Get platforms (should return only 3: luno, binance, kucoin)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/system/platforms
```

### API Keys (Protected)
```bash
# Save API key - MUST return {"success": true}
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"provider":"luno","api_key":"test123","api_secret":"test456"}' \
  http://localhost:8000/api/keys/save
# Expected: {"success": true, "message": "...", ...}

# Test API key endpoint
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"provider":"luno","api_key":"test123","api_secret":"test456"}' \
  http://localhost:8000/api/keys/test

# Delete should work even if not found
curl -X DELETE -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/keys/openai
```

## Expected Behavior

### 1. No 500 Errors
All endpoints MUST return 200 (or 401/403 for auth) even if:
- No data available
- Config missing
- Service not initialized
- Emergency stop collection doesn't exist

### 2. Stable Schemas
These endpoints MUST return consistent schema shapes:
- `/api/system/emergency-stop/status` → `{"is_emergency_stop_active": bool, "reason": str|null, "updated_at": str|null}`
- `/api/system/live-eligibility` → `{"live_allowed": bool, "reasons": [str]}`
- `/api/keys/save` → `{"success": bool, "message": str, ...}`

### 3. Backward Compatibility
API key storage accepts both old and new field names:
- Read: `api_key_encrypted`, `apiKeyEncrypted`, `api_key_ciphertext`, `key_encrypted`
- Write: Always use `api_key_encrypted` and `api_secret_encrypted`

### 4. Frontend "Add Exchange Keys" Button
Open Wallet Hub and verify:
- Clicking "+ Add Exchange Keys" button navigates to API key setup section
- Button works on both hash-based and pathname-based routing

## Environment Variables

Ensure these are set on VPS:
```bash
ENABLE_LIVE_TRADING=false  # Keep false until ready
ENABLE_TRADING=true        # For paper trading
ENABLE_CCXT=true          # For price data
ENABLE_SCHEDULERS=false   # Optional schedulers
ENABLE_AUTOPILOT=false    # Optional autopilot
MONGO_URL=mongodb://...
JWT_SECRET=...
API_KEY_ENCRYPTION_KEY=... # For API key encryption
```

## Go-Live Safety Rules

### Paper Training Requirements (7 days minimum):
- Minimum 7 days of paper trading
- Win rate > 52%
- Total profit > 3%
- Minimum 25 trades
- Max drawdown < 15%

### Live Trading Gate:
- `ENABLE_LIVE_TRADING=true` in env
- Emergency stop NOT active
- User has API keys configured
- User has completed paper training
- No excessive drawdown on bots

## Success Criteria

- ✅ Server starts without errors
- ✅ All critical endpoints return 200 (not 500)
- ✅ `verify_production_ready.py` passes all tests
- ✅ `verify_go_live.py` passes all tests
- ✅ No 404s in browser console for critical APIs
- ✅ API key save returns `{"success": true}`
- ✅ Emergency stop endpoint returns stable schema
- ✅ Live eligibility endpoint returns stable schema
- ✅ Wallet Hub button navigates correctly

## Rollback Plan

If issues occur:
1. Stop server: `sudo systemctl stop amarktai-api`
2. Check logs: `tail -f /var/log/amarktai/server.log`
3. If needed, revert: `git revert HEAD && sudo systemctl restart amarktai-api`

## Support Commands

### Check what's running
```bash
ps aux | grep python3
netstat -tlnp | grep 8000
```

### View logs
```bash
tail -f /var/log/amarktai/server.log
journalctl -u amarktai-api -f
```

### Quick health check
```bash
curl http://localhost:8000/api/health/ping
curl http://localhost:8000/api/system/ping
```

### Test emergency stop collection
```bash
# Connect to MongoDB
mongo amarktai_trading
# Check if collection exists
db.emergency_stop.findOne()
```

## Troubleshooting

### "module 'database' has no attribute 'emergency_stop_collection'"
- Fixed by adding `emergency_stop_collection` to database.py exports
- Restart server after pulling latest changes

### "API keys save works with token: Success not true"
- Fixed by ensuring `/api/keys/save` returns `{"success": true}`
- Update verifier script expectations if needed

### "Auth register endpoint requires first_name/last_name"
- Fixed in verifier scripts: now include both `first_name` and `last_name`
- Update any custom scripts to match new contract

### Wallet Hub button does nothing
- Fixed: button now correctly routes to API key setup
- Works with both hash-based (#api) and pathname-based routing
