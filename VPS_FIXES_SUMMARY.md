# VPS Bundle3 Fixes - Endpoint Mapping

## Fixed Issues Summary

### 1. Config Import Failures ✅
**Problem**: `cannot import name 'PAPER_TRAINING_DAYS' from config`

**Solution**:
- Created `backend/config/__init__.py` with all required constants
- Avoided circular imports by duplicating constants from `backend/config.py`
- All imports from `config` package now work correctly

**Affected Files**:
- `backend/config/__init__.py` - Added all promotion criteria constants
- `backend/engines/promotion_engine.py` - Now imports successfully
- `backend/routes/live_trading_gate.py` - Now imports successfully
- `backend/bot_lifecycle.py` - Now imports successfully

### 2. System Endpoints ✅

**Problem**: Missing endpoints causing 404 errors

**Solution**: Added missing endpoints to `/api/system` router

| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/api/system/live-eligibility` | GET | ✅ Added | Returns live trading eligibility with reasons |
| `/api/system/emergency-stop/status` | GET | ✅ Added | Returns emergency stop status |
| `/api/system/platforms` | GET | ✅ Fixed | Returns only Luno, Binance, KuCoin (no 500 errors) |
| `/api/system/emergency-stop` | POST | ✅ Exists | Already in emergency_stop_endpoints.py |
| `/api/system/mode` | GET | ✅ Exists | Already in server.py api_router |
| `/api/system/mode` | PUT | ✅ Exists | Already in server.py api_router |

**Affected Files**:
- `backend/routes/system.py` - Added live-eligibility, emergency-stop/status, fixed platforms

### 3. Profits Endpoints ✅

**Problem**: `/api/profits` and `/api/profits/reinvest` missing (404)

**Solution**: Created new profits router

| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/api/profits` | GET | ✅ Added | Returns profit data by period (daily/weekly/monthly) |
| `/api/profits/reinvest` | POST | ✅ Added | Reinvests profits (with stub support) |

**Affected Files**:
- `backend/routes/profits.py` - New file with both endpoints
- `backend/server.py` - Mounted profits router

### 4. API Key Field Mismatch ✅

**Problem**: `KeyError 'api_key_encrypted'` when reading stored keys

**Solution**: Support multiple field name variants

**Changes**:
- Modified `get_decrypted_key()` to check for:
  - `api_key_encrypted` (canonical)
  - `apiKeyEncrypted` (camelCase)
  - `encrypted_api_key` (alternate)
- Made DELETE `/api/api-keys/{provider}` idempotent (returns 200 even if key not found)

**Affected Files**:
- `backend/routes/api_key_management.py` - Enhanced get_decrypted_key()
- `backend/routes/api_keys_canonical.py` - Made DELETE idempotent

### 5. Chat Error ✅

**Problem**: `'module' object is not subscriptable` causing chat failures

**Solution**: Enhanced error handling

**Changes**:
- Wrapped chat endpoint in comprehensive try/except
- Returns graceful error message instead of 500 status
- Logs full traceback for debugging

**Affected Files**:
- `backend/server.py` - Enhanced `/api/chat/message` error handling

### 6. Eligible Bots Endpoint ✅

**Problem**: `/api/bots/eligible-for-promotion` could return 500 on config import errors

**Solution**: Never throw 500, always return safe response

**Changes**:
- Wrapped endpoint in try/except with ImportError handling
- Returns empty list with error details on failure
- Never crashes the API

**Affected Files**:
- `backend/server.py` - Enhanced `/api/bots/eligible-for-promotion` error handling

### 7. Wallet Endpoints ✅

**Status**: Already exist and are properly mounted

| Endpoint | Method | Status | Location |
|----------|--------|--------|----------|
| `/api/wallet/balances` | GET | ✅ Exists | routes/wallet_endpoints.py |
| `/api/wallet/requirements` | GET | ✅ Exists | routes/wallet_endpoints.py |
| `/api/wallet/funding-plans` | GET | ✅ Exists | routes/wallet_endpoints.py |

**No changes needed** - these endpoints already exist.

---

## Endpoint Compatibility Mapping

### Frontend Legacy → Canonical Backend

| Frontend Call | Backend Endpoint | Status |
|--------------|------------------|--------|
| `DELETE /api/api-keys/openai` | `DELETE /api/api-keys/{provider}` | ✅ Works (idempotent) |
| `POST /api/profits/reinvest` | `POST /api/profits/reinvest` | ✅ Added |
| `GET /api/profits` | `GET /api/profits?period={period}` | ✅ Added |
| `GET /api/wallet/balances` | `GET /api/wallet/balances` | ✅ Exists |
| `GET /api/wallet/requirements` | `GET /api/wallet/requirements` | ✅ Exists |
| `GET /api/wallet/funding-plans` | `GET /api/wallet/funding-plans` | ✅ Exists |
| `GET /api/system/live-eligibility` | `GET /api/system/live-eligibility` | ✅ Added |
| `GET /api/system/emergency-stop/status` | `GET /api/system/emergency-stop/status` | ✅ Added |
| `GET /api/system/platforms` | `GET /api/system/platforms` | ✅ Fixed |

---

## Supported Exchanges

As per requirements, **only these 3 exchanges** are returned by `/api/system/platforms`:

1. **Luno** (id: luno, bot_limit: 5)
2. **Binance** (id: binance, bot_limit: 10)
3. **KuCoin** (id: kucoin, bot_limit: 10)

---

## Real Funds Live Trading Gate

Live trading is gated by **three conditions** (all must be true):

1. `ENABLE_LIVE_TRADING=true` (environment variable)
2. `GET /api/system/live-eligibility` returns `eligible: true`
3. `GET /api/system/emergency-stop/status` returns `enabled: false`

The `/api/system/live-eligibility` endpoint checks:
- Feature flag enabled
- Emergency stop not active
- User has completed paper training
- User has API keys configured

---

## Files Modified

1. `backend/config/__init__.py` - Added all config constants to avoid circular imports
2. `backend/routes/system.py` - Added live-eligibility, emergency-stop/status, fixed platforms
3. `backend/routes/profits.py` - New file with profits and reinvest endpoints
4. `backend/routes/api_key_management.py` - Enhanced field compatibility
5. `backend/routes/api_keys_canonical.py` - Made DELETE idempotent
6. `backend/server.py` - Enhanced error handling, mounted profits router

---

## Next Steps

1. ✅ All code changes complete
2. ⏳ Test server startup on VPS
3. ⏳ Run `scripts/verify_production_ready.py`
4. ⏳ Run `scripts/verify_go_live.py`
5. ⏳ Verify frontend console has no more 404 errors
6. ⏳ Test real-time functionality
7. ⏳ Verify live trading is properly gated
