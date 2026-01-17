#!/bin/bash

# Dashboard Smoke Test Script
# Tests all dashboard endpoints and returns PASS/FAIL

set -e

API_BASE="${API_BASE:-http://127.0.0.1:8000}"
TEST_EMAIL="smoke_test_$(date +%s)@test.local"
TEST_PASSWORD="TestPass123!"

echo "==================================="
echo "Dashboard Smoke Test"
echo "API Base: $API_BASE"
echo "==================================="

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

# Helper functions
pass_test() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    PASSED=$((PASSED + 1))
}

fail_test() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    FAILED=$((FAILED + 1))
}

warn_test() {
    echo -e "${YELLOW}⚠ WARN${NC}: $1"
}

# Test 1: Health check
echo ""
echo "Test 1: Health Check"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE/api/health/ping")
if [ "$RESPONSE" == "200" ]; then
    pass_test "Health endpoint responding"
else
    fail_test "Health endpoint failed (HTTP $RESPONSE)"
fi

# Test 2: Register user
echo ""
echo "Test 2: User Registration (Email Normalization)"
REGISTER_RESPONSE=$(curl -s -X POST "$API_BASE/api/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${TEST_EMAIL^^}\",\"password\":\"$TEST_PASSWORD\",\"first_name\":\"Smoke\",\"last_name\":\"Test\"}")

if echo "$REGISTER_RESPONSE" | grep -q "token"; then
    pass_test "User registration successful"
    TOKEN=$(echo "$REGISTER_RESPONSE" | grep -o '"token":"[^"]*' | cut -d'"' -f4)
else
    warn_test "User registration (may already exist)"
    # Try login instead
    LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/api/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"${TEST_EMAIL}\",\"password\":\"$TEST_PASSWORD\"}")
    TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"token":"[^"]*' | cut -d'"' -f4)
fi

if [ -z "$TOKEN" ]; then
    fail_test "Could not obtain auth token"
    echo "OVERALL: FAILED"
    exit 1
fi

# Test 3: Login with different case
echo ""
echo "Test 3: Login Email Case Insensitivity"
LOGIN_LOWER=$(curl -s -X POST "$API_BASE/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${TEST_EMAIL,,}\",\"password\":\"$TEST_PASSWORD\"}")
if echo "$LOGIN_LOWER" | grep -q "token"; then
    pass_test "Login with lowercase email"
else
    fail_test "Login with lowercase email failed"
fi

# Test 4: Canonical API Keys endpoint
echo ""
echo "Test 4: Canonical API Keys Endpoint"
KEYS_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE/api/api-keys" \
    -H "Authorization: Bearer $TOKEN")
if [ "$KEYS_RESPONSE" == "200" ]; then
    pass_test "Canonical API keys endpoint (/api/api-keys)"
else
    fail_test "Canonical API keys endpoint failed (HTTP $KEYS_RESPONSE)"
fi

# Test 5: Whale Flow alias
echo ""
echo "Test 5: Whale Flow Alias"
WHALE_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE/api/whale-flow/summary" \
    -H "Authorization: Bearer $TOKEN")
if [ "$WHALE_RESPONSE" == "200" ] || [ "$WHALE_RESPONSE" == "503" ]; then
    pass_test "Whale flow alias endpoint (200 or 503 expected if disabled)"
else
    fail_test "Whale flow alias failed (HTTP $WHALE_RESPONSE)"
fi

# Test 6: Decision Trace REST endpoint
echo ""
echo "Test 6: Decision Trace REST Endpoint"
DECISION_RESPONSE=$(curl -s "$API_BASE/api/decision-trace/latest?limit=10" \
    -H "Authorization: Bearer $TOKEN")
if echo "$DECISION_RESPONSE" | grep -q "success"; then
    pass_test "Decision trace REST endpoint"
else
    fail_test "Decision trace REST endpoint failed"
fi

# Test 7: Metrics Summary
echo ""
echo "Test 7: Metrics Summary Endpoint"
METRICS_RESPONSE=$(curl -s "$API_BASE/api/metrics/summary" \
    -H "Authorization: Bearer $TOKEN")
if echo "$METRICS_RESPONSE" | grep -q "metrics"; then
    pass_test "Metrics summary endpoint"
else
    fail_test "Metrics summary endpoint failed"
fi

# Test 8: Wallet Hub (safe empty state)
echo ""
echo "Test 8: Wallet Hub (Safe Empty State)"
WALLET_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE/api/wallet/balances" \
    -H "Authorization: Bearer $TOKEN")
if [ "$WALLET_RESPONSE" == "200" ]; then
    pass_test "Wallet hub endpoint returns safe state"
else
    fail_test "Wallet hub endpoint failed (HTTP $WALLET_RESPONSE)"
fi

# Test 9: Analytics Exchange Comparison
echo ""
echo "Test 9: Analytics Exchange Comparison"
EXCHANGE_RESPONSE=$(curl -s "$API_BASE/api/analytics/exchange-comparison?period=30d" \
    -H "Authorization: Bearer $TOKEN")
if echo "$EXCHANGE_RESPONSE" | grep -q "exchanges"; then
    pass_test "Exchange comparison endpoint"
else
    fail_test "Exchange comparison endpoint failed"
fi

# Test 10: SSE (Server-Sent Events)
echo ""
echo "Test 10: SSE Real-time Events"
SSE_RESPONSE=$(timeout 3 curl -s "$API_BASE/api/realtime/events" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Accept: text/event-stream" || true)
if echo "$SSE_RESPONSE" | grep -q "event: heartbeat"; then
    pass_test "SSE heartbeat events"
else
    fail_test "SSE heartbeat events not received"
fi

# Results
echo ""
echo "==================================="
echo "Results:"
echo "  Passed: $PASSED"
echo "  Failed: $FAILED"
echo "==================================="

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}OVERALL: PASS${NC}"
    exit 0
else
    echo -e "${RED}OVERALL: FAIL${NC}"
    exit 1
fi
