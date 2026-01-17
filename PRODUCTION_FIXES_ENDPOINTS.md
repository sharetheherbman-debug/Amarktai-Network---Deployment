# Production Fixes - New Endpoints Documentation

**Date:** 2026-01-17  
**PR:** Fix dashboard console errors and backend 404/500s  
**Status:** ✅ Implemented

This document details the new endpoints added as part of the production fixes to address dashboard 404 errors and backend failures.

---

## New Compatibility Endpoints

These endpoints were added to provide backward compatibility with the dashboard and prevent 404 errors.

### AI Insights

**Endpoint:** `GET /api/ai/insights`  
**Status:** ✅ Implemented  
**Purpose:** Lightweight AI-powered system insights summary  
**Authentication:** Required (JWT Bearer token)

**Response Schema:**
```json
{
  "timestamp": "2026-01-17T15:30:00.000Z",
  "user_id": "user-uuid",
  "regime": {
    "current": "bullish_calm",
    "confidence": 0.85,
    "description": "Market showing stable upward movement"
  },
  "sentiment": {
    "overall": "positive",
    "score": 0.75,
    "sources_count": 12
  },
  "whale_signals": {
    "active_count": 2,
    "top_signal": {
      "coin": "BTC",
      "strength": 0.82
    }
  },
  "last_decision": {
    "symbol": "BTC/ZAR",
    "action": "buy",
    "confidence": 0.78,
    "timestamp": "2026-01-17T15:25:00.000Z"
  },
  "system_health": "trading_active"
}
```

**System Health Values:**
- `operational` - System running, no active bots
- `idle` - System running, no active trading
- `trading_active` - Bots actively trading
- `emergency_stop` - Emergency stop activated
- `error` - System error occurred

**Notes:**
- Returns safe defaults if underlying services unavailable
- Never returns 404 or 500 errors
- Aggregates data from multiple subsystems

---

### ML Predict (Query Params)

**Endpoint:** `GET /api/ml/predict`  
**Status:** ✅ Implemented  
**Purpose:** ML price prediction with query parameter compatibility  
**Authentication:** Required (JWT Bearer token)

**Query Parameters:**
- `symbol` (optional): Trading pair symbol (e.g., "BTC-ZAR")
- `pair` (optional): Trading pair in slash format (e.g., "BTC/ZAR")
- `platform` (optional): Exchange platform name
- `timeframe` (default: "1h"): Prediction timeframe

**Response Schema:**
```json
{
  "success": true,
  "prediction": {
    "direction": "bullish",
    "confidence": 0.75,
    "target_price": 52500.00,
    "timeframe": "1h"
  },
  "query": {
    "symbol": "BTC-ZAR",
    "pair": "BTC/ZAR",
    "platform": "luno",
    "timeframe": "1h"
  }
}
```

**Notes:**
- Accepts both `symbol` and `pair` parameters for flexibility
- Automatically converts dash format (BTC-ZAR) to slash format (BTC/ZAR)
- Returns safe neutral prediction if ML service unavailable
- Compatible with existing `/api/ml/predict/{pair}` path endpoint

---

### Profits Reinvest

**Endpoint:** `POST /api/profits/reinvest`  
**Status:** ✅ Implemented  
**Purpose:** Trigger profit reinvestment for paper trading  
**Authentication:** Required (JWT Bearer token)

**Request Body:**
```json
{
  "amount": 1000.0,  // Optional: specific amount to reinvest
  "top_n": 3         // Optional: number of top bots to reinvest in
}
```

**Response Schema (Success):**
```json
{
  "success": true,
  "message": "Reinvestment triggered successfully",
  "details": {
    "amount_reinvested": 1500.00,
    "bots_created": 2,
    "profit_source": ["bot-123", "bot-456"]
  },
  "timestamp": "2026-01-17T15:30:00.000Z"
}
```

**Response Schema (Limit Reached):**
```json
{
  "success": false,
  "message": "Cannot reinvest: maximum bot limit (30) reached",
  "current_bots": 30,
  "max_bots": 30
}
```

**Validation Rules:**
- Maximum 30 bots per user
- Reinvests into top 3 performing bots by default
- Paper trading safe (no real money movement)
- Creates reinvest request if service unavailable

**Notes:**
- Integrates with daily reinvestment service if available
- Falls back to queued request if service not running
- Never returns 404 - always provides feedback

---

### Advanced Decisions Recent

**Endpoint:** `GET /api/advanced/decisions/recent`  
**Status:** ✅ Implemented  
**Purpose:** Get recent trading decisions for Decision Trace UI  
**Authentication:** Required (JWT Bearer token)

**Query Parameters:**
- `limit` (default: 100, max: 1000): Number of recent decisions
- `symbol` (optional): Filter by specific trading pair

**Response Schema:**
```json
{
  "success": true,
  "count": 25,
  "limit": 100,
  "decisions": [
    {
      "timestamp": "2026-01-17T15:25:00.000Z",
      "symbol": "BTC/ZAR",
      "action": "buy",
      "confidence": 0.78,
      "reasoning": [
        "Market regime bullish (85% confidence)",
        "Order flow imbalance positive (65%)",
        "Sentiment analysis positive (80%)"
      ],
      "component_scores": {
        "regime": 0.85,
        "ofi": 0.65,
        "sentiment": 0.80,
        "whale": 0.55,
        "macro": 0.60
      },
      "position_size_multiplier": 1.2,
      "stop_loss": 48500.00,
      "take_profit": 52500.00
    }
  ],
  "timestamp": "2026-01-17T15:30:00.000Z"
}
```

**Notes:**
- Returns empty array with metadata if no decisions found
- Never returns 404 error
- Integrates with decision trace collection and decision_trace router
- Supports symbol filtering for specific pair analysis

---

## Fixed Endpoints

These endpoints were fixed to prevent 500 errors and security issues.

### Emergency Stop

**Endpoint:** `POST /api/system/emergency-stop`  
**Status:** ✅ Fixed  
**Issue:** TypeError - expected Dict but got str from get_current_user  
**Fix:** Changed parameter type from `Dict` to `str`

**Query Parameters:**
- `reason` (default: "User initiated"): Reason for emergency stop

**Response Schema:**
```json
{
  "success": true,
  "message": "Emergency stop activated - all trading halted",
  "bots_paused": 5,
  "timestamp": "2026-01-17T15:30:00.000Z"
}
```

**Related Endpoints:**
- `POST /api/system/emergency-stop/disable` - Deactivate emergency stop
- `GET /api/system/emergency-stop/status` - Get current status

---

### Wallet Requirements

**Endpoint:** `GET /api/wallet/requirements`  
**Status:** ✅ Fixed  
**Issue:** UnboundLocalError - variable 'balances' referenced before assignment  
**Fix:** Initialize `balances = None` before conditional block

**Response Schema:**
```json
{
  "user_id": "user-uuid",
  "requirements": {
    "luno": {
      "required": 5000.00,
      "bots": 3,
      "available": 6500.00,
      "surplus_deficit": 1500.00,
      "health": "healthy"
    }
  },
  "timestamp": "2026-01-17T15:30:00.000Z"
}
```

**Health Indicators:**
- `healthy` - Surplus >= 1000 ZAR
- `adequate` - Surplus >= 0 ZAR
- `warning` - Deficit < 500 ZAR
- `critical` - Deficit >= 500 ZAR

---

### Profile Update

**Endpoint:** `PUT /api/auth/profile`  
**Status:** ✅ Fixed  
**Issues:**
1. No validation of forbidden fields
2. Could update sensitive fields (email, password_hash)
3. No proper error handling

**Fixes:**
- Added forbidden fields list (password_hash, email, id, _id, etc.)
- Validate at least one valid field present
- Check if user exists after update
- Return sanitized user object (no sensitive fields)

**Request Body:**
```json
{
  "first_name": "Updated Name",
  "currency": "USD",
  "system_mode": "live"
}
```

**Response Schema:**
```json
{
  "success": true,
  "message": "Profile updated successfully",
  "user": {
    "id": "user-uuid",
    "first_name": "Updated Name",
    "email": "user@example.com",
    "currency": "USD",
    "system_mode": "live",
    // ... other safe fields
  }
}
```

**Forbidden Fields (Cannot Update):**
- `password_hash`, `hashed_password`, `new_password`, `password`
- `id`, `_id`
- `email` (prevents account takeover)

---

### OpenAI Key Test

**Endpoint:** `POST /api/keys/test`  
**Status:** ✅ Fixed  
**Issue:** Using deprecated `openai.ChatCompletion.acreate()` (openai<1.0)  
**Fix:** Updated to use `AsyncOpenAI` client (openai>=1.x)

**Request Body:**
```json
{
  "provider": "openai",
  "api_key": "sk-proj-..."
}
```

**Response Schema (Success):**
```json
{
  "success": true,
  "message": "✅ OpenAI API key validated successfully",
  "provider": "openai",
  "test_data": {
    "model_accessible": true,
    "test_model": "gpt-4o-mini",
    "models": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo", "gpt-4"]
  }
}
```

**Response Schema (Invalid Key):**
```json
{
  "success": false,
  "message": "❌ Invalid OpenAI API key",
  "error": "Authentication failed - check your API key"
}
```

**Environment Variables:**
- `OPENAI_TEST_MODEL` (default: "gpt-4o-mini"): Model to use for testing

**Supported Models:**
- `gpt-4o-mini` (default, cost-effective)
- `gpt-4o`
- `gpt-3.5-turbo`
- `gpt-4`

---

## Security Fixes

### Login/Register Response Sanitization

**Endpoints:**
- `POST /api/auth/login`
- `POST /api/auth/register`
- `GET /api/auth/me`
- `PUT /api/auth/profile`

**Issue:** Responses included sensitive fields like `password_hash`

**Fix:** All auth endpoints now sanitize responses to exclude:
- `password_hash`
- `hashed_password`
- `new_password`
- `password`
- `_id`

**Before (INSECURE):**
```json
{
  "user": {
    "id": "user-uuid",
    "email": "user@example.com",
    "password_hash": "$2b$12$...",  // ❌ EXPOSED
    "hashed_password": "$2b$12$..."  // ❌ EXPOSED
  }
}
```

**After (SECURE):**
```json
{
  "user": {
    "id": "user-uuid",
    "email": "user@example.com",
    "first_name": "User Name",
    "currency": "ZAR"
    // No sensitive fields ✅
  }
}
```

---

## Environment Variables

New environment variables added:

```bash
# OpenAI model for API key testing (default: gpt-4o-mini)
OPENAI_TEST_MODEL=gpt-4o-mini
```

Existing critical variables:

```bash
# Required for admin bootstrap
JWT_SECRET=your-secret-key
AMK_ADMIN_EMAIL=admin@example.com
AMK_ADMIN_PASS=secure-admin-password

# MongoDB connection
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=amarktai

# OpenAI (if using AI features)
OPENAI_API_KEY=sk-proj-...
```

---

## Testing

A comprehensive test suite has been created:

**Test Script:** `tests/test_production_fixes.py`

**Run Tests:**
```bash
# With backend running on localhost:8000
python tests/test_production_fixes.py

# With custom API base
API_BASE=https://api.amarktai.online python tests/test_production_fixes.py
```

**Tests Coverage:**
1. ✅ Login response security (no password hashes)
2. ✅ Register response security
3. ✅ Profile update validation and security
4. ✅ Wallet requirements returns 200 (no 500 errors)
5. ✅ Emergency stop activation/deactivation
6. ✅ OpenAI key test uses new API (no deprecated calls)
7. ✅ AI insights endpoint availability
8. ✅ ML predict query params compatibility
9. ✅ Profits reinvest endpoint
10. ✅ Advanced decisions recent endpoint
11. ✅ OpenAPI schema includes new endpoints

---

## Migration Notes

### For Deployment:

1. **Update Environment:**
   ```bash
   # Add to .env if using OpenAI key testing
   OPENAI_TEST_MODEL=gpt-4o-mini
   ```

2. **No Database Migrations Required:**
   - All changes are backward compatible
   - Existing data structures unchanged

3. **Bootstrap Admin (if needed):**
   ```bash
   python scripts/bootstrap_admin.py
   ```

4. **Test New Endpoints:**
   ```bash
   python tests/test_production_fixes.py
   ```

5. **Frontend Rebuild:**
   ```bash
   cd frontend
   npm run build
   ```

### Breaking Changes:

**None.** All changes are backward compatible. Existing endpoints continue to work as before, with improved security and reliability.

### Deprecated:

**None.** No endpoints deprecated in this release.

---

## Frontend Updates Required

**Register.js:**
```javascript
// Before (ERROR):
const API = API_BASE;  // ❌ API_BASE not defined

// After (FIXED):
import { API_BASE } from '@/lib/api';
const API = API_BASE;  // ✅ Properly imported
```

**No other frontend changes required** - all new endpoints are backward-compatible aliases or new features.

---

## Summary

**Total Endpoints Added:** 4  
**Total Endpoints Fixed:** 5  
**Security Issues Fixed:** 5  
**Breaking Changes:** 0  

**Impact:**
- ✅ No more dashboard 404 errors
- ✅ No more backend 500 errors
- ✅ Sensitive data never exposed in API responses
- ✅ OpenAI key testing works with latest library versions
- ✅ All validation properly implemented
- ✅ Safe defaults for missing data

**Reliability Improvements:**
- Emergency stop never crashes
- Wallet requirements never crashes
- Profile updates properly validated
- ML predictions degrade gracefully
- AI insights return safe defaults

---

**Document Version:** 1.0  
**Last Updated:** 2026-01-17  
**Author:** Production Fixes PR
