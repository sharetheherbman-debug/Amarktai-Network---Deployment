# Quick Deployment Checklist - VPS Bundle3 Fixes

## Pre-Deployment Verification

### 1. Config Import Test
```bash
cd /path/to/Amarktai-Network---Deployment
python3 -c "import sys; sys.path.insert(0, 'backend'); from config import PAPER_TRAINING_DAYS; print('✅ Config OK')"
```
Expected: `✅ Config OK`

### 2. Server Startup Test
```bash
cd backend
python3 server.py
```
Expected: Server starts without import errors

### 3. Check OpenAPI Spec
After server starts:
```bash
curl http://localhost:8001/openapi.json | jq '.paths | keys' | grep -E 'live-eligibility|emergency-stop/status|profits'
```
Expected: All three endpoints appear

## Critical Endpoints to Test

### System Endpoints (Protected)
```bash
# Get live eligibility
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/system/live-eligibility

# Get emergency stop status  
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/system/emergency-stop/status

# Get platforms (should return only 3: luno, binance, kucoin)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/system/platforms
```

### Profits Endpoints (Protected)
```bash
# Get profits
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/profits?period=daily

# Test reinvest (POST)
curl -X POST -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/profits/reinvest
```

### API Keys (Protected)
```bash
# Delete should return 200 even if not found
curl -X DELETE -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/api-keys/openai
```

### Wallet Endpoints (Protected)
```bash
# These should already work
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/wallet/balances
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/wallet/requirements
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/wallet/funding-plans
```

### Bot Promotion (Protected)
```bash
# Should never return 500, always returns 200 with empty list or bots
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/bots/eligible-for-promotion
```

## Expected Behavior

### 1. No 500 Errors
All endpoints should return 200 even if:
- No data available
- Config missing
- Service not initialized

### 2. No 404 Errors
Frontend should not see 404 on:
- /api/profits
- /api/profits/reinvest
- /api/system/live-eligibility
- /api/system/emergency-stop/status
- /api/wallet/* endpoints
- /api/api-keys/{provider} delete

### 3. Supported Exchanges Only
`/api/system/platforms` returns exactly 3 exchanges:
- Luno
- Binance
- KuCoin

### 4. Live Trading Gate
Check the gate is working:
```bash
# Should return eligible: false if ENABLE_LIVE_TRADING not set
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/system/live-eligibility
```

Expected response structure:
```json
{
  "eligible": false,
  "reasons": ["list", "of", "reasons"],
  "flags": {
    "enable_live_trading": false,
    "emergency_stop": false,
    "paper_trained_bots": 0,
    "api_keys_configured": false
  }
}
```

## Browser Console Check

After deploying, open the dashboard in browser and check console:
- ❌ BEFORE: Multiple 404 errors for missing endpoints
- ✅ AFTER: No 404 errors on API calls

## Environment Variables

Ensure these are set on VPS:
```bash
ENABLE_LIVE_TRADING=false  # Keep false until ready
ENABLE_TRADING=true        # For paper trading
ENABLE_CCXT=true          # For price data
MONGO_URL=mongodb://...
JWT_SECRET=...
```

## Rollback Plan

If issues occur:
1. Stop server
2. Check logs for errors
3. If needed, revert to previous commit:
   ```bash
   git revert HEAD
   ```

## Success Criteria

- ✅ Server starts without errors
- ✅ All endpoints in OpenAPI spec
- ✅ No 404s in browser console
- ✅ No 500 errors on API calls
- ✅ verify_production_ready.py passes
- ✅ verify_go_live.py passes
- ✅ Real-time functionality works
- ✅ Live trading properly gated

## Post-Deployment

1. Monitor logs for any import errors
2. Check browser console for 404s
3. Test chat functionality
4. Verify bot promotion endpoint
5. Test API key management
6. Confirm emergency stop works

## Support Commands

### Check what's running
```bash
ps aux | grep python3
netstat -tlnp | grep 8001
```

### View logs
```bash
tail -f /var/log/amarktai/server.log
journalctl -u amarktai -f
```

### Quick health check
```bash
curl http://localhost:8001/api/health/ping
curl http://localhost:8001/api/system/ping
```
