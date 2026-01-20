# Go-Live Deployment Verification

## Pre-Deployment Checklist

### 1. Local Verification (MUST PASS BEFORE VPS DEPLOYMENT)

```bash
# All files compile cleanly
cd /path/to/Amarktai-Network---Deployment
python3 -m py_compile backend/server.py backend/autopilot_engine.py backend/routes/system_status.py

# Full backend compilation check
python3 - <<'PY'
import os, py_compile
errs=[]
for root,_,files in os.walk("backend"):
    if any(x in root for x in (".git","__pycache__","venv",".venv")): 
        continue
    for f in files:
        if f.endswith(".py"):
            p=os.path.join(root,f)
            try: py_compile.compile(p, doraise=True)
            except Exception as e: errs.append((p,str(e)))
print("ERRS",len(errs))
raise SystemExit(1 if errs else 0)
PY
# Expected: ERRS 0

# Server import test
cd backend
python3 -c "import server; print('IMPORT_OK')"
# Expected: IMPORT_OK
```

### 2. VPS Environment Setup

**Required Environment Variables:**

```bash
# Database (REQUIRED)
MONGO_URL=mongodb://localhost:27017
DB_NAME=amarktai_trading

# Security (REQUIRED - MUST CHANGE FROM DEFAULT)
JWT_SECRET=<generate-with-openssl-rand-hex-32>

# Feature Flags (defaults shown, customize as needed)
ENABLE_TRADING=false         # Set to 'true' when ready for trading
ENABLE_AUTOPILOT=false       # Set to 'true' for autonomous management
ENABLE_SCHEDULERS=false      # Set to 'true' for scheduled tasks
ENABLE_CCXT=true            # Keep 'true' for exchange connections
ENABLE_REALTIME=true        # Keep 'true' for WebSocket/SSE
```

**Generate Secure JWT Secret:**
```bash
openssl rand -hex 32
```

## VPS Deployment Procedure

### Step 1: Stop Service

```bash
sudo systemctl stop amarktai-api
```

### Step 2: Backup Current Deployment

```bash
cd /var/amarktai/app
sudo cp -r backend backend.backup.$(date +%Y%m%d_%H%M%S)
```

### Step 3: Deploy New Code

```bash
# Pull latest from fix branch
git fetch origin
git checkout copilot/fix-router-mounting-errors
git pull origin copilot/fix-router-mounting-errors

# Verify files are present
ls -la backend/utils/env_utils.py
ls -la backend/routes/health.py
```

### Step 4: Verify Systemd Configuration

```bash
sudo systemctl cat amarktai-api
```

**Expected Configuration:**
```ini
[Unit]
Description=Amarktai Trading API
After=network.target mongodb.service

[Service]
Type=simple
User=amarktai
WorkingDirectory=/var/amarktai/app/backend
ExecStart=/var/amarktai/venv/bin/uvicorn server:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=10

# REQUIRED Environment Variables
Environment="MONGO_URL=mongodb://localhost:27017"
Environment="DB_NAME=amarktai_trading"
Environment="JWT_SECRET=YOUR-SECRET-HERE"

# Feature Flags
Environment="ENABLE_CCXT=true"
Environment="ENABLE_REALTIME=true"
Environment="ENABLE_TRADING=false"
Environment="ENABLE_AUTOPILOT=false"
Environment="ENABLE_SCHEDULERS=false"

[Install]
WantedBy=multi-user.target
```

### Step 5: Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl start amarktai-api
sudo systemctl status amarktai-api
```

**Expected Status:**
- Active: active (running)
- No error messages in recent logs

### Step 6: Verify Preflight Endpoint

```bash
# Check preflight (no auth required)
curl http://localhost:8000/api/health/preflight | jq
```

**Expected Response:**
```json
{
  "ok": true,
  "timestamp": "2024-01-19T...",
  "flags": {
    "ENABLE_TRADING": false,
    "ENABLE_AUTOPILOT": false,
    "ENABLE_SCHEDULERS": false,
    "ENABLE_CCXT": true,
    "ENABLE_REALTIME": true
  },
  "routers": {
    "mounted": [
      "System",
      "Trades",
      "Health",
      "Profits",
      "System Status",
      "Realtime Events",
      ...
    ],
    "failed": []
  },
  "services": {
    "db": "ok",
    "redis": "skipped",
    "ccxt": "ok"
  },
  "auth": {
    "jwt_secret_present": true,
    "algorithm": "HS256"
  }
}
```

**CRITICAL CHECKS:**
- ✅ `ok` must be `true`
- ✅ `routers.failed` must be empty `[]`
- ✅ `services.db` must be `"ok"`
- ✅ `auth.jwt_secret_present` must be `true`
- ✅ If `flags.ENABLE_REALTIME` is `true`, "Realtime Events" must be in `routers.mounted`

### Step 7: Verify Critical Endpoints

```bash
# Health check
curl http://localhost:8000/api/health/ping
# Expected: {"status":"healthy","db":"connected",...}

# System status (requires auth token)
# First login to get token
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"your@email.com","password":"yourpassword"}' \
  | jq -r '.access_token')

# Check system status
curl http://localhost:8000/api/system/status \
  -H "Authorization: Bearer $TOKEN" | jq

# Root endpoint
curl http://localhost:8000/
# Expected: {"message":"Amarktai Network API","version":"2.0.0",...}
```

### Step 8: Verify Through Nginx

```bash
# If using nginx reverse proxy
curl https://yourdomain.com/api/health/preflight | jq
curl https://yourdomain.com/api/health/ping
```

### Step 9: Check Service Logs

```bash
# Recent logs
sudo journalctl -u amarktai-api -n 100 --no-pager

# Follow logs in real-time
sudo journalctl -u amarktai-api -f
```

**Look for:**
- ✅ "📊 Router mounting complete: 34 mounted, 1 failed" (or similar)
- ✅ "✅ Mounted: Realtime Events"
- ✅ No errors about double /api/api/ prefixes
- ✅ No "router not found" or AttributeError messages

## Troubleshooting

### Issue: ok=false in Preflight

**Check `issues` array in response:**

```json
{
  "ok": false,
  "issues": [
    "Router mount failures: 5",
    "Database not available"
  ]
}
```

**Resolution:**
1. Check `routers.failed` - install missing dependencies if needed
2. Verify MongoDB is running: `sudo systemctl status mongodb`
3. Check database connection: `mongo --eval "db.adminCommand('ping')"`

### Issue: JWT Secret Warning

**Symptom:**
```json
{
  "auth": {
    "jwt_secret_present": false
  }
}
```

**Resolution:**
```bash
# Generate new secret
openssl rand -hex 32

# Update systemd service
sudo systemctl edit amarktai-api
# Add: Environment="JWT_SECRET=<your-new-secret>"

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart amarktai-api
```

### Issue: Realtime Router Not Mounted

**Symptom:**
- `ENABLE_REALTIME=true` but "Realtime Events" not in mounted list

**Resolution:**
```bash
# Check if routes/realtime.py exists
ls -la /var/amarktai/app/backend/routes/realtime.py

# Check service logs for import errors
sudo journalctl -u amarktai-api | grep -i realtime

# Verify environment variable
sudo systemctl show amarktai-api | grep ENABLE_REALTIME
```

### Issue: /api/api/ Double Prefix

**This should NOT happen after this fix.**

If you see it:
```bash
# Verify you're on correct branch
git branch
git log -1

# Re-pull the fix branch
git fetch origin
git reset --hard origin/copilot/fix-router-mounting-errors
sudo systemctl restart amarktai-api
```

## Post-Deployment Validation

### Automated Health Check

```bash
#!/bin/bash
# save as check_deployment.sh

ENDPOINT="http://localhost:8000/api/health/preflight"

echo "Checking deployment health..."
RESPONSE=$(curl -s "$ENDPOINT")

OK=$(echo "$RESPONSE" | jq -r '.ok')
ISSUES=$(echo "$RESPONSE" | jq -r '.issues // []')

if [ "$OK" = "true" ]; then
    echo "✅ Deployment is healthy"
    echo "$RESPONSE" | jq '.'
    exit 0
else
    echo "❌ Deployment has issues:"
    echo "$ISSUES" | jq '.'
    echo
    echo "Full response:"
    echo "$RESPONSE" | jq '.'
    exit 1
fi
```

### Continuous Monitoring

Add to monitoring system (e.g., Prometheus, Grafana, or simple cron):

```bash
# Add to crontab
*/5 * * * * curl -sf http://localhost:8000/api/health/preflight | jq -e '.ok == true' || /usr/local/bin/alert_ops.sh
```

## Success Criteria

✅ Preflight returns `ok: true`  
✅ No router mount failures  
✅ Database connection successful  
✅ JWT secret configured  
✅ All critical endpoints accessible  
✅ Realtime/WebSocket working  
✅ No /api/api/ double prefixes  
✅ Service starts cleanly  
✅ Service logs show no errors  
✅ Nginx reverse proxy works (if configured)  

## Rollback Procedure

If deployment fails:

```bash
# Stop service
sudo systemctl stop amarktai-api

# Restore backup
cd /var/amarktai/app
sudo rm -rf backend
sudo cp -r backend.backup.YYYYMMDD_HHMMSS backend

# Restart service
sudo systemctl start amarktai-api
sudo systemctl status amarktai-api
```

## Go-Live Runtime Verification

After deployment, verify that critical runtime features are working correctly using the automated test script.

### Prerequisites

1. Server must be running (either locally or on VPS)
2. At least one user account created
3. User credentials (email/password)

### Running the Go-Live Verifier (ALL GATES)

```bash
# Set credentials via environment variables
export EMAIL='your-email@example.com'
export PASSWORD='your-password'
export OPENAI_API_KEY='sk-...'  # Optional: for testing OpenAI key save
export LUNO_API_KEY='...'  # Optional: for testing Luno key save
export LUNO_API_SECRET='...'  # Optional: for testing Luno key save

# Run the verifier (against local server)
python3 verify_go_live_runtime.py

# Or against a remote server
export BASE_URL='https://your-vps-domain.com'
python3 verify_go_live_runtime.py

# Or pass credentials as arguments
python3 verify_go_live_runtime.py your-email@example.com your-password
```

### Manual Gate-by-Gate Verification

#### Gate A: Keys (OpenAI + Luno) ✅

Test model fallback with saved user keys:

```bash
# Login and get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"your@email.com","password":"yourpassword"}' \
  | jq -r '.access_token')

# Save OpenAI key
curl -s -X POST http://localhost:8000/api/keys/save \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"provider":"openai","api_key":"sk-..."}' | jq '.'
# Expected: {"success":true,"message":"Saved OPENAI API key",...}

# Test OpenAI key with model fallback (should auto-fallback if model forbidden)
curl -s -X POST http://localhost:8000/api/keys/test \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"provider":"openai"}' | jq '.'
# Expected: {"ok":true,"model_used":"gpt-4o-mini","key_source":"user",...}

# List saved keys
curl -s http://localhost:8000/api/keys/list \
  -H "Authorization: Bearer $TOKEN" | jq '.keys'
# Expected: Array with openai key showing last_test_ok=true

# Save Luno key
curl -s -X POST http://localhost:8000/api/keys/save \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"provider":"luno","api_key":"...","api_secret":"..."}' | jq '.'
# Expected: {"success":true,"message":"Saved LUNO API key",...}

# Test Luno key
curl -s -X POST http://localhost:8000/api/keys/test \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"provider":"luno"}' | jq '.'
# Expected: {"ok":true,"provider":"luno","test_data":{...}}
```

#### Gate B: AI Features ✅

Test AI chat with canonical key retrieval:

```bash
# AI chat (uses saved OpenAI key from Gate A)
curl -s -X POST http://localhost:8000/api/ai/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"What is my total profit?"}' | jq '.'
# Expected: {"content":"...","key_source":"user","model_used":"gpt-4o-mini",...}

# AI chat without key (should return deterministic error)
curl -s -X POST http://localhost:8000/api/ai/chat \
  -H "Authorization: Bearer $INVALID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"test"}' | jq '.'
# Expected: {"error":"no_api_key","guidance":"Save your OpenAI API key...",...}
```

#### Gate C: Realtime Updates ✅

Test realtime event stream:

```bash
# Subscribe to SSE events (run in background)
curl -N -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/realtime/events &

# In another terminal, trigger events:
# 1. Save a key
curl -s -X POST http://localhost:8000/api/keys/save \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"provider":"test","api_key":"test123"}' | jq '.'

# 2. Toggle system mode
curl -s -X POST http://localhost:8000/system/mode/toggle \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mode":"paperTrading","enabled":true}' | jq '.'

# Events should appear in SSE stream within 10s:
# event: bot_update
# event: system_mode_update
# event: api_key_update
```

#### Gate D: Bot Management Controls ✅

Test bot status and controls:

```bash
# Get bot status (shows all 5 exchanges)
curl -s http://localhost:8000/api/bots/status \
  -H "Authorization: Bearer $TOKEN" | jq '.exchange_counts'
# Expected: {"luno":X,"binance":Y,"kucoin":Z,"ovex":A,"valr":B}
# Also verify: ".all_exchanges" shows ["luno","binance","kucoin","ovex","valr"]

# Get a bot ID
BOT_ID=$(curl -s http://localhost:8000/api/bots/status \
  -H "Authorization: Bearer $TOKEN" | jq -r '.bots[0].id')

# Pause bot
curl -s -X POST http://localhost:8000/api/bots/$BOT_ID/pause \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason":"Testing pause"}' | jq '.bot.state'
# Expected: "paused"

# Unpause bot
curl -s -X POST http://localhost:8000/api/bots/$BOT_ID/unpause \
  -H "Authorization: Bearer $TOKEN" | jq '.bot.state'
# Expected: "active"

# Stop bot
curl -s -X POST http://localhost:8000/api/bots/$BOT_ID/stop \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason":"Testing stop"}' | jq '.bot.state'
# Expected: "stopped"
```

#### Gate E: Mode Truth (Paper vs Live) ✅

Test mutual exclusion:

```bash
# Get current modes
curl -s http://localhost:8000/system/mode \
  -H "Authorization: Bearer $TOKEN" | jq '.'

# Enable paper trading (should disable live)
curl -s -X POST http://localhost:8000/system/mode/toggle \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mode":"paperTrading","enabled":true}' | jq '.modes'
# Expected: {"paperTrading":true,"liveTrading":false,...}

# Try to enable live trading (should disable paper)
curl -s -X POST http://localhost:8000/system/mode/toggle \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mode":"liveTrading","enabled":true}' | jq '.modes'
# Expected: {"paperTrading":false,"liveTrading":true,...}
# Also verify: ".mutual_exclusion_applied":true
```

#### Gate F: Admin Override UX ✅

Test admin bot promotion dropdown (requires admin token):

```bash
# Login as admin
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@email.com","password":"adminpass"}' \
  | jq -r '.access_token')

# Get eligible bots for live promotion (dropdown selector)
curl -s http://localhost:8000/api/admin/bots/eligible-for-live \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.eligible_bots'
# Expected: Array of bots with training_complete=true OR active paper bots
# Should NOT include: stopped, training_failed, already live bots

# Promote a bot to live (requires confirmation in UI)
ELIGIBLE_BOT_ID=$(curl -s http://localhost:8000/api/admin/bots/eligible-for-live \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.eligible_bots[0].id')

curl -s -X POST http://localhost:8000/api/admin/bots/$ELIGIBLE_BOT_ID/override-live \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.'
# Expected: {"success":true,"message":"Bot ... promoted to live trading (admin override)",...}
```

#### Gate G: Training Pipeline ✅

Test training queue and promotion:

```bash
# Get training queue
curl -s http://localhost:8000/api/training/queue \
  -H "Authorization: Bearer $TOKEN" | jq '.'
# Expected: {"training_bots":[...],"ready_for_promotion":N}

# Get a training bot that passed evaluation
TRAINING_BOT_ID=$(curl -s http://localhost:8000/api/training/queue \
  -H "Authorization: Bearer $TOKEN" | jq -r '.training_bots[] | select(.evaluation.passed==true) | .id' | head -1)

# Promote bot from training to paused_ready
curl -s -X POST http://localhost:8000/api/training/$TRAINING_BOT_ID/promote \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mode":"paper"}' | jq '.'
# Expected: {"success":true,"message":"Bot ... training complete - ready for activation",...}

# Verify bot is now in paused_ready state
curl -s http://localhost:8000/api/bots/status \
  -H "Authorization: Bearer $TOKEN" | jq ".bots[] | select(.id==\"$TRAINING_BOT_ID\") | .state"
# Expected: "paused_ready" or "paused" with training_complete=true

# Verify new bots never start live automatically
# (this is enforced in bot creation - new bots must go through training first)
```

### Expected Output (ALL GATES PASS)

```
============================================================
🚀 GO-LIVE GATES VERIFICATION
============================================================

Gate A: Keys (OpenAI + Luno) ✅
  - Model fallback: ✅ (gpt-4o-mini used)
  - Key source: user ✅
  - Luno save/test: ✅

Gate B: AI Features ✅
  - Canonical key retrieval: ✅
  - Model fallback: ✅
  - Deterministic errors: ✅

Gate C: Realtime Updates ✅
  - SSE stream active: ✅
  - Events emitted within 10s: ✅
  - Bot updates, mode changes, key saves: ✅

Gate D: Bot Management ✅
  - All 5 exchanges shown: ✅
  - pause/unpause/stop work: ✅
  - Status endpoint shows states: ✅

Gate E: Mode Truth ✅
  - Paper vs Live mutual exclusion: ✅
  - Mode toggle enforced: ✅

Gate F: Admin Override ✅
  - Eligible bots dropdown: ✅
  - Only paused_ready + active paper shown: ✅
  - Override requires admin: ✅

Gate G: Training Pipeline ✅
  - Training queue shows bots: ✅
  - Graduation criteria evaluated: ✅
  - Promote to paused_ready works: ✅
  - New bots never auto-start live: ✅

============================================================
🎉 ALL GO-LIVE GATES PASSED!
============================================================
```

### Troubleshooting

If tests fail:

1. **Login Failed** - Check credentials are correct
2. **No OpenAI Keys** - Save an OpenAI key in Dashboard under API Keys
3. **Key Test Failed** - Verify the saved key is valid on OpenAI platform
4. **AI Chat Error** - Check server logs for OpenAI API errors

## Contact

If issues persist after following this guide, collect:
1. Output of `curl http://localhost:8000/api/health/preflight | jq`
2. Last 200 lines of service logs: `sudo journalctl -u amarktai-api -n 200`
3. Systemd environment config: `sudo systemctl show amarktai-api | grep Environment`
