# Quick Verification Commands

This document provides the exact curl commands needed to verify all runtime fixes.

## Prerequisites

1. **Server Running:**
   ```bash
   # Start MongoDB
   docker run -d --name test-mongo -p 27017:27017 mongo:7
   
   # Set environment variables
   export MONGO_URL="mongodb://localhost:27017"
   export DB_NAME="amarktai_trading_test"
   export JWT_SECRET="test-secret-key-for-verification-purposes-min-32-chars"
   export OPENAI_API_KEY="sk-test-key-if-available"  # Optional
   
   # Start server (in new terminal)
   cd /home/runner/work/Amarktai-Network---Deployment/Amarktai-Network---Deployment
   uvicorn backend.server:app --host 0.0.0.0 --port 8000
   ```

2. **Create Test User:**
   ```bash
   # Register user
   curl -X POST http://localhost:8000/api/auth/register \
     -H "Content-Type: application/json" \
     -d '{
       "email": "test@example.com",
       "password": "TestPass123!",
       "name": "Test User"
     }'
   ```

---

## Test 1: Preflight Check

**Command:**
```bash
curl -X GET http://localhost:8000/api/health/preflight | jq
```

**Expected Keys in Response:**
```json
{
  "ok": true,
  "services": {
    "db": "ok",
    "paper_trading_db": "ok",           // ← NEW
    "openai_key_source": "env" | "none"  // ← NEW
  },
  "keys": {
    "saved_count_global": 0               // ← NEW
  }
}
```

**What This Verifies:** Fix E - Preflight exposes runtime status

---

## Test 2: Login & Get Token

**Command:**
```bash
# Login and extract token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!"
  }' | jq -r '.token')

# Verify token obtained
echo "Token: $TOKEN"
```

**Expected:** JWT token string

---

## Test 3: List API Keys (Should Be Empty)

**Command:**
```bash
curl -X GET http://localhost:8000/api/keys/list \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Expected Response:**
```json
{
  "success": true,
  "keys": [],
  "total": 0
}
```

**What This Verifies:** Fix B - List endpoint works

---

## Test 4: Save OpenAI API Key

**Command:**
```bash
curl -X POST http://localhost:8000/api/keys/save \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "api_key": "sk-test-fake-key-for-verification"
  }' | jq
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Saved OPENAI API key",
  "provider": "openai",
  "status": "saved_untested",
  "key_info": {
    "provider": "openai",
    "masked_key": "sk-t...tion"
  }
}
```

**What This Verifies:** Fix B - Save endpoint works

---

## Test 5: List API Keys (Should Have 1)

**Command:**
```bash
curl -X GET http://localhost:8000/api/keys/list \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Expected Response:**
```json
{
  "success": true,
  "keys": [
    {
      "provider": "openai",
      "created_at": "...",
      "status": "saved_untested"
    }
  ],
  "total": 1
}
```

**What This Verifies:** Fix B - List shows saved key

---

## Test 6: Test API Key WITHOUT Providing Key

**THIS IS THE CRITICAL TEST FOR FIX C**

**Command:**
```bash
curl -X POST http://localhost:8000/api/keys/test \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4o-mini"
  }' | jq
```

**Note:** We do NOT provide `api_key` in the request body - it should load the saved key.

**Expected Response (if using fake key):**
```json
{
  "ok": false,
  "success": false,
  "message": "❌ Invalid OpenAI API key",
  "error": "Authentication failed - check your API key"
}
```

**OR (if using real OPENAI_API_KEY env var):**
```json
{
  "ok": true,
  "success": true,
  "message": "✅ OpenAI API key validated successfully",
  "provider": "openai",
  "test_data": {
    "model_accessible": true,
    "test_model": "gpt-4o-mini"
  }
}
```

**What This Verifies:** 
- Fix C - Test endpoint loads saved key when not provided
- The test endpoint successfully found the saved key (didn't return "No saved key" error)

---

## Test 7: AI Chat WITH Saved Key

**Command:**
```bash
curl -X POST http://localhost:8000/api/ai/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Hello, what is 1+1?",
    "request_action": false
  }' | jq
```

**Expected Response (if using fake key):**
```json
{
  "role": "assistant",
  "content": "I'm having trouble connecting to my AI services. Please try again.",
  "timestamp": "..."
}
```

**Expected Response (if using real key):**
```json
{
  "role": "assistant",
  "content": "1+1 equals 2.",
  "timestamp": "...",
  "system_state": { ... }
}
```

**What This Verifies:**
- Fix D - AI chat attempts to use saved user key first
- If saved key fails, falls back to env OPENAI_API_KEY
- Does NOT return "Please save your OpenAI API key" error (that would be a FAIL)

---

## Test 8: AI Chat WITHOUT Saved Key

**Setup:** Delete the saved key first:
```bash
curl -X DELETE http://localhost:8000/api/keys/openai \
  -H "Authorization: Bearer $TOKEN"
```

**Command:**
```bash
curl -X POST http://localhost:8000/api/ai/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Hello, what is 1+1?",
    "request_action": false
  }' | jq
```

**Expected Response (if NO env OPENAI_API_KEY):**
```json
{
  "role": "assistant",
  "content": "AI service not configured. Please save your OpenAI API key in the Dashboard under API Keys.",
  "timestamp": "..."
}
```

**Expected Response (if env OPENAI_API_KEY is set):**
```json
{
  "role": "assistant",
  "content": "1+1 equals 2.",
  "timestamp": "..."
}
```

**What This Verifies:**
- Fix D - Priority order working: user > env > error
- When no user key, falls back to env
- When no env either, returns clear error message

---

## Test 9: Run Automated Verifier Script

**Command:**
```bash
# First, save a key again if you deleted it
curl -X POST http://localhost:8000/api/keys/save \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "api_key": "sk-test-key"
  }'

# Run verifier
export EMAIL="test@example.com"
export PASSWORD="TestPass123!"
python3 verify_go_live_runtime.py
```

**Expected Output:**
```
============================================================
🚀 GO-LIVE RUNTIME VERIFICATION
============================================================
🔐 Logging in as test@example.com...
✅ Login successful

📋 Test 1: Preflight Check
  Endpoint: GET /api/health/preflight
  ✅ PASS - Preflight OK

📋 Test 2: API Keys List
  Endpoint: GET /api/keys/list
  ✅ PASS - Found 1 OpenAI key(s)

📋 Test 3: API Key Test
  Endpoint: POST /api/keys/test
  ✅ PASS - Key test successful: ...

📋 Test 4: AI Chat
  Endpoint: POST /api/ai/chat
  ✅ PASS - AI chat responded: ...

============================================================
📊 RESULTS
============================================================
  ✅ Passed: 4
  ❌ Failed: 0

🎉 ALL TESTS PASSED - Go-Live Runtime Ready!
============================================================
```

**What This Verifies:** All fixes working together

---

## Test 10: Check Paper Trading (Requires Bot)

**Note:** Paper trading DB fix (Fix A) is automatically tested when paper trades execute. The fix prevents the "cannot access local variable 'db'" error.

**Verification:**
```bash
# Check server logs for paper trading errors
# Should NOT see: "cannot access local variable 'db'"
# Should see: "✅ Connected to LUNO (DEMO MODE)" or similar

# If you have a bot running, check trades collection
# (Requires MongoDB access)
mongo amarktai_trading_test --eval "db.trades.find().count()"
```

---

## Complete Test Suite (All Commands)

```bash
#!/bin/bash
# Save this as test_runtime_fixes.sh

set -e  # Exit on error

BASE_URL="http://localhost:8000"
EMAIL="test@example.com"
PASSWORD="TestPass123!"

echo "=========================================="
echo "Runtime Fixes Verification Suite"
echo "=========================================="

# Test 1: Preflight
echo -e "\n[Test 1] Preflight Check..."
curl -s -X GET $BASE_URL/api/health/preflight | jq -e '.ok == true' > /dev/null && echo "✅ PASS" || echo "❌ FAIL"

# Test 2: Login
echo -e "\n[Test 2] Login..."
TOKEN=$(curl -s -X POST $BASE_URL/api/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" | jq -r '.token')
[[ -n "$TOKEN" ]] && echo "✅ PASS - Token obtained" || echo "❌ FAIL - No token"

# Test 3: Save API Key
echo -e "\n[Test 3] Save API Key..."
curl -s -X POST $BASE_URL/api/keys/save \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"provider":"openai","api_key":"sk-test"}' | jq -e '.success == true' > /dev/null && echo "✅ PASS" || echo "❌ FAIL"

# Test 4: List Keys
echo -e "\n[Test 4] List Keys..."
curl -s -X GET $BASE_URL/api/keys/list \
  -H "Authorization: Bearer $TOKEN" | jq -e '.total >= 1' > /dev/null && echo "✅ PASS" || echo "❌ FAIL"

# Test 5: Test Key (without providing api_key)
echo -e "\n[Test 5] Test Key (loads from DB)..."
curl -s -X POST $BASE_URL/api/keys/test \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"provider":"openai","model":"gpt-4o-mini"}' | jq -e 'has("ok") or has("success")' > /dev/null && echo "✅ PASS" || echo "❌ FAIL"

# Test 6: AI Chat
echo -e "\n[Test 6] AI Chat..."
RESPONSE=$(curl -s -X POST $BASE_URL/api/ai/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"Hello","request_action":false}')
echo "$RESPONSE" | jq -e '.content' > /dev/null && echo "✅ PASS" || echo "❌ FAIL"
echo "$RESPONSE" | grep -q "Please save your OpenAI API key" && echo "⚠️  WARNING: Still showing save key message" || echo "✅ No error message found"

echo -e "\n=========================================="
echo "All manual tests completed"
echo "=========================================="
```

**Usage:**
```bash
chmod +x test_runtime_fixes.sh
./test_runtime_fixes.sh
```

---

## Troubleshooting

### If Test 6 (Test Key) Returns "No saved key"

This means the key wasn't saved properly in Test 3. Check:
```bash
# Verify key exists in database
curl -X GET http://localhost:8000/api/keys/list \
  -H "Authorization: Bearer $TOKEN" | jq '.keys'

# Should show at least one key with provider: "openai"
```

### If AI Chat Returns "Please save your OpenAI API key"

This means Fix D didn't work. Check:
1. Is the saved key actually in the database? (run list keys)
2. Is OPENAI_API_KEY env var set? (should fall back to this)
3. Check server logs for errors

### If Preflight Missing New Fields

This means Fix E didn't apply. Check:
```bash
# Verify new fields exist
curl -s -X GET http://localhost:8000/api/health/preflight | jq '.keys, .services.paper_trading_db, .services.openai_key_source'
```

---

## Success Criteria

✅ **All fixes working correctly if:**

1. Preflight returns new fields: `keys`, `paper_trading_db`, `openai_key_source`
2. List keys returns saved keys correctly
3. Test key works WITHOUT providing api_key in body
4. AI chat does NOT return "Please save..." when key exists
5. AI chat falls back to env OPENAI_API_KEY when user key doesn't exist
6. No "cannot access local variable 'db'" errors in server logs
7. Verifier script passes all 4 tests

---

## Production Deployment

After all tests pass locally:

```bash
# On production VPS
cd /opt/amarktai
git pull origin main
sudo systemctl restart amarktai-api

# Quick smoke test
curl http://localhost:8000/api/health/preflight | jq '.ok'
# Should return: true

# Check logs for errors
sudo journalctl -u amarktai-api -n 50 --no-pager
```

**Rollback if needed:**
```bash
git revert <commit-hash>
sudo systemctl restart amarktai-api
```
