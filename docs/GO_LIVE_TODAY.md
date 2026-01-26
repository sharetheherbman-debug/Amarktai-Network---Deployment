# GO LIVE TODAY - Production Deployment Checklist

## ✅ Pre-Deployment Validation

### 1. Environment Configuration
- [ ] `.env` file created and configured (copy from `.env.example`)
- [ ] `JWT_SECRET` changed to a secure random value (min 32 chars)
- [ ] `ENCRYPTION_KEY` or `API_KEY_ENCRYPTION_KEY` set for API key storage
- [ ] `MONGO_URL` configured and tested
- [ ] `DB_NAME` set correctly
- [ ] System mode flags configured:
  - [ ] `ENABLE_TRADING` set appropriately (false for initial deployment)
  - [ ] `ENABLE_AUTOPILOT` set appropriately (false for initial deployment)
  - [ ] `ENABLE_CCXT=true` for price data

### 2. Database Setup
- [ ] MongoDB is running and accessible
- [ ] Database connection tested (`mongosh` or connection string)
- [ ] Run migration script: `python backend/migrations/add_capital_tracking.py`
- [ ] Verify migration completed successfully
- [ ] Bootstrap admin user: `python scripts/bootstrap_admin.py`

### 3. Capital Allocation Integrity
- [ ] User balance fields added (balance, allocated_balance, reserved_balance)
- [ ] Bot allocated_capital field added
- [ ] Capital validator service integrated
- [ ] Bot creation enforces fund allocation checks
- [ ] Test bot creation with insufficient funds (should fail with clear error)

### 4. Paper Trading Realism
- [ ] Order validation service integrated
- [ ] Exchange rules configured (precision, min notional, step size)
- [ ] Validation wired into paper trading engine
- [ ] Test order with invalid precision (should fail with clear error)

### 5. System Gating
- [ ] System gate service integrated
- [ ] Trading scheduler checks gate before running
- [ ] `/api/system/status` endpoint returns correct status
- [ ] Emergency stop functionality tested
- [ ] Test trading with ENABLE_TRADING=false (should not execute)

## ✅ Deployment Steps

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Run Pre-Flight Checks
```bash
# Backend preflight
python backend/preflight.py

# Production verification
python scripts/verify_production_ready.py
```

### 3. Start the Backend
```bash
# Option 1: Direct run
cd backend
python server.py

# Option 2: With systemd (recommended for production)
sudo systemctl start amarktai-backend
sudo systemctl status amarktai-backend
```

### 4. Verify Backend is Running
```bash
curl http://localhost:8000/api/health
# Expected: {"status": "healthy", ...}
```

### 5. Start the Frontend
```bash
cd frontend
npm install
npm run build  # For production
npm start      # Or serve build directory
```

## ✅ Post-Deployment Validation

### 1. Run Smoke Tests
```bash
# Comprehensive smoke check
python scripts/smoke_check.py

# Expected: All checks pass with ✓
```

### 2. Test Critical Flows

#### Authentication
- [ ] Register new user
- [ ] Login with credentials
- [ ] JWT token issued and validated
- [ ] Protected endpoints require valid token

#### System Status
- [ ] GET `/api/system/status` returns correct trading mode
- [ ] GET `/api/system/mode` returns user modes
- [ ] System gate shows trading disabled if ENABLE_TRADING=false

#### Capital Allocation
- [ ] Create bot with valid capital (should succeed)
- [ ] Create bot with insufficient capital (should fail with error code)
- [ ] Delete bot releases capital back to user
- [ ] GET `/api/system/status` shows correct capital breakdown

#### API Keys
- [ ] Save OpenAI API key
- [ ] Save Luno API key (with secret)
- [ ] Save KuCoin API key (with secret and passphrase)
- [ ] Keys are masked when retrieved
- [ ] Test API key connection
- [ ] Delete API key

#### Dashboard
- [ ] Overview shows correct metrics
- [ ] Live trades display with timestamps
- [ ] Training & Quarantine section loads
- [ ] Bot creation works
- [ ] System modes toggle correctly

#### WebSocket Real-Time
- [ ] Connect to `/api/ws` with token
- [ ] Receive connection confirmation
- [ ] Create a bot → receive bot_status_changed event
- [ ] Execute trade → receive trade_executed event
- [ ] No disconnects or reconnect loops

### 3. Performance Checks
- [ ] Backend responds to requests < 500ms
- [ ] Database queries execute < 200ms
- [ ] WebSocket messages delivered < 100ms
- [ ] No memory leaks (monitor for 10 minutes)
- [ ] CPU usage < 30% under normal load

### 4. Error Handling
- [ ] Invalid API requests return proper error codes
- [ ] Missing authentication returns 401
- [ ] Validation errors return 400 with clear messages
- [ ] Server errors return 500 with safe error messages (no stack traces to client)
- [ ] Frontend shows user-friendly error messages

## ✅ Security Checklist

- [ ] No sensitive data in logs
- [ ] API keys encrypted in database
- [ ] JWT tokens use secure secret
- [ ] CORS configured correctly
- [ ] Rate limiting enabled (if applicable)
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (using parameterized queries)
- [ ] XSS prevention (React escapes by default)

## ✅ Monitoring Setup

### Logs
- [ ] Backend logs to file or stdout
- [ ] Log level set appropriately (INFO for production)
- [ ] Error tracking configured (if using external service)

### Metrics
- [ ] `/api/metrics` endpoint accessible
- [ ] Prometheus metrics exported (if enabled)
- [ ] System health dashboard accessible

### Alerts
- [ ] Email alerts configured (optional)
- [ ] Emergency stop trigger tested
- [ ] High error rate detection working

## ✅ Backup & Recovery

- [ ] Database backup strategy in place
- [ ] Backup script tested and scheduled
- [ ] Recovery procedure documented
- [ ] `.env` file backed up securely (outside repo)

## ✅ Trading Activation (After 24h Stable Operation)

### Safe Trading Activation Path

1. **Verify 24h Stability**
   - [ ] Backend uptime > 24 hours
   - [ ] No crashes or restarts
   - [ ] Error rate < 1%
   - [ ] All smoke tests pass

2. **Enable Paper Trading First**
   ```bash
   # In .env
   ENABLE_TRADING=true
   ENABLE_AUTOPILOT=false  # Keep off initially
   ```
   - [ ] Restart backend
   - [ ] Verify system status shows `trading_allowed: true`
   - [ ] Create paper trading bot
   - [ ] Verify bot executes paper trades
   - [ ] Monitor for 48 hours

3. **Enable Autopilot (After 48h Paper Trading)**
   ```bash
   # In .env
   ENABLE_TRADING=true
   ENABLE_AUTOPILOT=true
   ```
   - [ ] Restart backend
   - [ ] Verify autopilot runs daily cycle
   - [ ] Monitor profit reinvestment
   - [ ] Monitor bot spawning respects capital limits

4. **Live Trading (Only After 7+ Days Successful Paper Trading)**
   - [ ] Minimum 7 days paper trading completed
   - [ ] Win rate > 52%
   - [ ] Positive paper profit
   - [ ] No critical errors
   - [ ] User manually switches mode to live in UI
   - [ ] Confirm live trading activation
   - [ ] Monitor closely for first 24 hours

## ✅ Emergency Procedures

### Emergency Stop
```bash
# Via API
curl -X POST http://localhost:8000/api/system/emergency-stop \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"enabled": true}'

# Or via UI
# Dashboard → System Modes → Emergency Stop
```

### Rollback
```bash
# Stop services
sudo systemctl stop amarktai-backend

# Restore previous version
git checkout <previous-commit>

# Restart
sudo systemctl start amarktai-backend
```

### Database Restore
```bash
# Restore from backup
mongorestore --uri="$MONGO_URL" --drop dump/
```

## 📊 Success Criteria

- ✅ All smoke tests pass
- ✅ No critical errors in logs for 24 hours
- ✅ Authentication flow works end-to-end
- ✅ Capital allocation prevents unfunded bots
- ✅ Order validation rejects invalid orders
- ✅ System gate prevents trading when disabled
- ✅ Real-time updates working via WebSocket
- ✅ Dashboard loads and displays correct data
- ✅ API keys saved and encrypted
- ✅ Profit series shows correct period boundaries

## 🚨 Blockers (Do Not Go Live Until Resolved)

- ❌ Migration script fails
- ❌ Database connection issues
- ❌ Authentication not working
- ❌ Bots can be created without capital
- ❌ System gate allows trading when ENABLE_TRADING=false
- ❌ WebSocket not connecting
- ❌ Critical errors in logs
- ❌ Encryption key not set (API keys fail)

## 📝 Post-Go-Live

- [ ] Monitor logs for first 24 hours
- [ ] Check error rates hourly
- [ ] Verify no memory leaks
- [ ] Document any issues encountered
- [ ] Update this checklist based on experience

---

**Last Updated:** 2026-01-26  
**Maintained By:** Production Team  
**Contact:** [Insert contact information]
