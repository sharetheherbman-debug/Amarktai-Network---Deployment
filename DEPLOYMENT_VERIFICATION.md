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

## Contact

If issues persist after following this guide, collect:
1. Output of `curl http://localhost:8000/api/health/preflight | jq`
2. Last 200 lines of service logs: `sudo journalctl -u amarktai-api -n 200`
3. Systemd environment config: `sudo systemctl show amarktai-api | grep Environment`
