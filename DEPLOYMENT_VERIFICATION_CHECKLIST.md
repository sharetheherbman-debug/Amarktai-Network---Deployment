# Production Deployment Verification Checklist

## Pre-Deployment

- [ ] Review all changes in this PR
- [ ] Verify tests pass: `cd backend && python -m pytest tests/test_lifecycle.py -v`
- [ ] Review PRODUCTION_STABILIZATION_SUMMARY.md
- [ ] Backup production database
- [ ] Schedule maintenance window (if needed)

## Deployment Steps

### 1. Pull Changes
```bash
cd /var/amarktai/app
sudo git pull origin main
```

### 2. Check Git Status
```bash
git log -5 --oneline
# Should show:
# - Add comprehensive production stabilization summary
# - Fix lifecycle tests and enhance emergency stop to HARD STOP
# - Add bootstrap trading, harden self-healing, add DB migration and smoke test docs
# - Add lifecycle manager and fix systemd permissions
```

### 3. Update System Service
```bash
sudo cp deployment/systemd/amarktai-api.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### 4. Restart Service
```bash
sudo systemctl restart amarktai-api
sleep 5
sudo systemctl status amarktai-api
```

### 5. Check Logs for Errors
```bash
# Check last 50 lines for errors
sudo journalctl -u amarktai-api -n 50 --no-pager | grep -i error

# Watch live logs (Ctrl+C to exit)
sudo journalctl -u amarktai-api -f
```

## Post-Deployment Verification

### 1. Run Smoke Test
```bash
cd /var/amarktai/app
python3 scripts/smoke_check.py http://localhost:8000
```

**Expected Output**:
```
============================================================
🔥 AMARKTAI NETWORK - PRODUCTION SMOKE TEST
============================================================
✓ Base URL: OK (200)
✓ Health check: healthy
✓ System status endpoint: reachable
============================================================
✓ SMOKE TEST PASSED: 3/3 checks successful
============================================================
```

### 2. Verify Lifecycle Manager
```bash
# Check logs for lifecycle manager startup
sudo journalctl -u amarktai-api -n 200 --no-pager | grep "lifecycle\|subsystem"

# Should see:
# ✅ Started X subsystems with Y background tasks
```

### 3. Verify No Await Errors
```bash
# Check logs for NoneType await errors (should be none)
sudo journalctl -u amarktai-api --since "5 minutes ago" | grep -i "nonetype.*await"
```

### 4. Verify Bootstrap Trading
```bash
# Check logs for bootstrap mode (if any new bots exist)
sudo journalctl -u amarktai-api --since "1 hour ago" | grep -i "bootstrap"

# Should see (if new bots exist):
# 🔧 Bootstrap mode enabled: X trades < 5 threshold
```

### 5. Verify Self-Healing
```bash
# Check self-healing startup
sudo journalctl -u amarktai-api -n 200 | grep -i "self-healing"

# Should see:
# ✅ Self-Healing System started
```

### 6. Test Emergency Stop
```bash
# Get admin token first
TOKEN="your-admin-token-here"

# Activate emergency stop
curl -X POST http://localhost:8000/api/admin/emergency-stop \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"

# Expected response:
# {"success": true, "message": "Emergency stop activated...", ...}

# Check logs
sudo journalctl -u amarktai-api -n 20 | grep -i "emergency"

# Should see:
# 🚨 EMERGENCY STOP ACTIVATED - ALL TRADING HALTED

# Resume
curl -X POST http://localhost:8000/api/admin/emergency-resume \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"

# Expected response:
# {"success": true, "message": "Emergency stop lifted...", ...}
```

### 7. Check Database Migration
```bash
# Check logs for baseline field repair
sudo journalctl -u amarktai-api -n 500 | grep -i "baseline\|repair"

# Should see:
# 🔧 Running startup baseline field repair...
# Added starting_capital to X bots
# Added peak_capital to X bots
# ✅ Startup baseline field repair complete
```

### 8. Verify No Permission Errors
```bash
# Check for permission denied errors (should be none)
sudo journalctl -u amarktai-api --since "5 minutes ago" | grep -i "permission denied"
```

### 9. Check System Status
```bash
# Get system status
curl http://localhost:8000/api/system_status \
  -H "Authorization: Bearer $TOKEN"

# Should return JSON with system info
```

### 10. Monitor for 30 Minutes
```bash
# Watch logs for any errors
sudo journalctl -u amarktai-api -f | grep -i "error\|critical"

# Watch for successful operations
sudo journalctl -u amarktai-api -f | grep -i "✅\|success"
```

## Health Metrics to Monitor

### System Health
- [ ] Service is `active (running)`
- [ ] No error logs in last 30 minutes
- [ ] Database connection stable
- [ ] All subsystems started successfully

### Trading Health
- [ ] Paper trades executing (if enabled)
- [ ] Bootstrap mode working for new bots
- [ ] Self-healing system running
- [ ] No infinite no_trade loops

### Safety Gates
- [ ] Emergency stop works
- [ ] Emergency resume works
- [ ] Bots stay paused after resume
- [ ] Live trading gates enforced

## Rollback Plan (If Needed)

If critical issues occur:

```bash
# 1. Activate emergency stop
curl -X POST http://localhost:8000/api/admin/emergency-stop \
  -H "Authorization: Bearer $TOKEN"

# 2. Stop service
sudo systemctl stop amarktai-api

# 3. Rollback to previous version
cd /var/amarktai/app
git log --oneline -10  # Find previous commit
sudo git reset --hard <previous-commit-hash>

# 4. Restore old service file (if changed)
sudo cp deployment/systemd/amarktai-api.service /etc/systemd/system/
sudo systemctl daemon-reload

# 5. Restart service
sudo systemctl start amarktai-api

# 6. Verify
python3 scripts/smoke_check.py http://localhost:8000
```

## Success Criteria

Deployment is successful if:

✅ All smoke test checks pass
✅ Service runs for 30+ minutes without errors
✅ Lifecycle manager starts all subsystems
✅ Bootstrap trading mode works for new bots
✅ Self-healing runs without crashes
✅ Emergency stop/resume work correctly
✅ No permission denied errors
✅ Database migration completes successfully
✅ No "NoneType await" errors in logs

## Final Sign-Off

- [ ] Smoke test PASSED
- [ ] All verifications completed
- [ ] No critical errors in logs
- [ ] Emergency stop tested
- [ ] System stable for 30+ minutes
- [ ] Team notified of successful deployment

**Deployed by**: ___________________  
**Date/Time**: ___________________  
**Verified by**: ___________________  
**Notes**: ___________________
