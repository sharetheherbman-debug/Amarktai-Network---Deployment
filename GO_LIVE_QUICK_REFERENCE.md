# Production Go-Live - Quick Reference Card

## 🚀 Pre-Deployment Checklist

### 1. Database Migration (REQUIRED)
```bash
# Backup first!
mongodump --uri="$MONGO_URL" --db amarktai_trading --out backup_$(date +%Y%m%d)

# Run migration
cd backend
python migrations/migrate_api_keys_user_id.py

# Verify (should return 0)
mongo amarktai_trading --eval 'db.api_keys.find({"user_id": {$type: "objectId"}}).count()'
```

### 2. Environment Variables
```bash
# Required
export ENABLE_TRADING=1
export ENABLE_SCHEDULERS=1
export MONGO_URL=mongodb://localhost:27017
export DB_NAME=amarktai_trading
export JWT_SECRET=your_secret_here
export API_KEY_ENCRYPTION_KEY=your_key_here

# Optional
export ENABLE_AUTOPILOT=0
export ENABLE_CCXT=1
```

### 3. Test Key Features
```bash
# Test system health
curl -H "Authorization: Bearer $JWT_TOKEN" http://localhost:8000/api/system/health

# Test system status
curl -H "Authorization: Bearer $JWT_TOKEN" http://localhost:8000/api/system/status

# Test overview
curl -H "Authorization: Bearer $JWT_TOKEN" http://localhost:8000/api/overview

# Test wallet balance
curl -H "Authorization: Bearer $JWT_TOKEN" http://localhost:8000/api/wallet/balances
```

## 🔧 Key Changes Summary

### API Key Management
| Feature | Endpoint | Status |
|---------|----------|--------|
| Save (canonical) | POST `/api/api-keys` | ✅ |
| Save (legacy) | POST `/api/keys/save` | ✅ |
| Test (canonical) | POST `/api/api-keys/{provider}/test` | ✅ |
| Test (legacy) | POST `/api/keys/test` | ✅ |
| List (canonical) | GET `/api/api-keys` | ✅ |
| List (legacy) | GET `/api/keys/list` | ✅ |

### New Endpoints
| Endpoint | Purpose | Auth Required |
|----------|---------|---------------|
| `/api/system/status` | Feature flags, scheduler status | Yes |
| `/api/system/health` | Health check | No |
| `/api/overview?include_wallet=true` | Overview with live Luno balance | Yes |

## 📊 API Key Status Display

| Status | Display | Meaning |
|--------|---------|---------|
| `saved_tested` | "Saved & Tested ✅" | Key saved and validated |
| `test_failed` | "Test Failed ❌" | Key saved but validation failed |
| `saved_untested` | "Saved (untested)" | Key saved, not yet tested |

## 🔐 Security Checklist
- [x] API keys encrypted at rest (Fernet)
- [x] Keys never returned in plaintext
- [x] Browser password save disabled (`autocomplete="new-password"`)
- [x] User ID type consistency (prevents auth bypass)
- [x] Backward-compatible migration (no data loss)

## 📝 Testing Commands

### Integration Test Suite
```bash
export JWT_TOKEN="your_token_here"
python tools/test_api_keys_flow.py
```

### Manual Dashboard Tests
1. Navigate to Settings → API Keys
2. Add Luno API key
3. Click "Test" button
4. Verify status shows "Saved & Tested ✅"
5. Go to Dashboard → Overview
6. Verify wallet balance displays

## 🐛 Troubleshooting

### Issue: "Luno API keys not configured"
**Solution**: Add Luno API key via Settings → API Keys

### Issue: "Authentication failed"
**Solution**: Verify API key permissions on Luno (need view balance)

### Issue: Key saved but not appearing
**Solution**: Run migration script to convert ObjectId → String

### Issue: "Invalid API-key" error
**Solution**: Check API key format and permissions

### Issue: Scheduler not running
**Solution**: Set `ENABLE_TRADING=1` and `ENABLE_SCHEDULERS=1`

## 📞 Support Contacts

### Logs Locations
```bash
# Backend logs
docker logs amarktai-backend

# MongoDB logs
docker logs amarktai-mongo

# System status
curl localhost:8000/api/system/status
```

### Key Files
- Migration guide: `MIGRATION.md`
- Full summary: `PRODUCTION_FIXES_SUMMARY.md`
- Endpoints: `ENDPOINTS.md`
- Deployment: `DEPLOY.md`

## ✅ Go-Live Verification

After deployment, verify:
- [ ] Migration completed (0 ObjectId user_ids remaining)
- [ ] System status endpoint returns 200
- [ ] Can save API key via dashboard
- [ ] Can test API key successfully
- [ ] Wallet balance displays correctly
- [ ] Overview endpoint works
- [ ] Paper trading executes (if enabled)
- [ ] No browser password prompts on API key inputs

## 🎯 Success Criteria

| Metric | Target | Check |
|--------|--------|-------|
| API key save success rate | > 95% | Dashboard logs |
| API key test success rate | > 90% | Test endpoint logs |
| Wallet balance fetch time | < 3s | Performance monitoring |
| Overview load time | < 1s | Frontend metrics |
| Migration completion | 100% | MongoDB query |

---

**Version**: 1.0  
**Last Updated**: 2026-01-16  
**Status**: Ready for Production  
**Migration Required**: Yes (one-time)
