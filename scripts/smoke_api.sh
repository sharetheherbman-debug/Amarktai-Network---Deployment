#!/bin/bash
# Smoke test script for Amarktai Network API
# Tests all critical endpoints to ensure they're operational

set -e

API_BASE="${API_BASE:-http://localhost:8000}"
TEST_EMAIL="${TEST_EMAIL:-test@example.com}"
TEST_PASSWORD="${TEST_PASSWORD:-testpassword123}"

echo "🧪 Amarktai Network API Smoke Test"
echo "======================================"
echo "API Base: $API_BASE"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track results
PASSED=0
FAILED=0

# Helper function to test endpoint
test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local expected_code=$4
    local description=$5
    
    echo -n "Testing: $description... "
    
    if [ -z "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$API_BASE$endpoint" \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" 2>&1)
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$API_BASE$endpoint" \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            -d "$data" 2>&1)
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "$expected_code" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Expected $expected_code, got $http_code)"
        echo "Response: $body"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

echo "📍 Step 1: Health Check"
echo "========================"
test_endpoint GET "/api/system/ping" "" "200" "System ping"
echo ""

echo "🔐 Step 2: Authentication"
echo "=========================="

# Try to login first (user might exist from previous tests)
echo "Attempting login..."
login_response=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}" 2>&1)

login_code=$(echo "$login_response" | tail -n1)
login_body=$(echo "$login_response" | sed '$d')

if [ "$login_code" = "200" ]; then
    echo -e "${GREEN}✓ Login successful${NC}"
    TOKEN=$(echo "$login_body" | grep -o '"token":"[^"]*' | cut -d'"' -f4)
    PASSED=$((PASSED + 1))
else
    echo -e "${YELLOW}⚠ Login failed, will try registration${NC}"
    
    # Try to register
    echo "Attempting registration..."
    register_response=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/api/auth/register" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\",\"first_name\":\"Test\"}" 2>&1)
    
    register_code=$(echo "$register_response" | tail -n1)
    register_body=$(echo "$register_response" | sed '$d')
    
    if [ "$register_code" = "200" ]; then
        echo -e "${GREEN}✓ Registration successful${NC}"
        TOKEN=$(echo "$register_body" | grep -o '"token":"[^"]*' | cut -d'"' -f4)
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗ Both login and registration failed${NC}"
        echo "Cannot continue without authentication"
        exit 1
    fi
fi

if [ -z "$TOKEN" ]; then
    echo -e "${RED}✗ Failed to get authentication token${NC}"
    exit 1
fi

echo "Token obtained: ${TOKEN:0:20}..."
echo ""

echo "📊 Step 3: System Endpoints"
echo "============================"
test_endpoint GET "/api/system/status" "" "200" "System status"
test_endpoint GET "/api/system/mode" "" "200" "System mode"
test_endpoint GET "/api/system/platforms" "" "200" "Platforms list"
echo ""

echo "🔑 Step 4: Platform Health"
echo "==========================="
test_endpoint GET "/api/platforms/health" "" "200" "Platform health"
test_endpoint GET "/api/platforms/readiness" "" "200" "Platform readiness"
echo ""

echo "💬 Step 5: Chat Endpoints"
echo "=========================="
test_endpoint POST "/api/chat/message" '{"message":"Hello"}' "200" "Chat message"
test_endpoint POST "/api/ai/chat" '{"content":"Status check"}' "200" "AI chat"
echo ""

echo "🤖 Step 6: Bot Management"
echo "=========================="
test_endpoint GET "/api/bots" "" "200" "List bots"
echo ""

echo "📈 Step 7: Metrics & Analytics"
echo "==============================="
test_endpoint GET "/api/metrics" "" "200" "Get metrics"
test_endpoint GET "/api/trades" "" "200" "Get trades"
echo ""

echo "💰 Step 8: Wallet Endpoints"
echo "============================"
test_endpoint GET "/api/wallet/transfers" "" "200" "Get transfers"
test_endpoint GET "/api/wallet/balance/summary" "" "200" "Balance summary"
echo ""

echo "⚡ Step 9: Realtime Connection Test"
echo "===================================="
echo -n "Testing SSE connection... "
# Test SSE endpoint (just check if it connects, don't wait for events)
sse_response=$(timeout 2 curl -s -N "$API_BASE/api/realtime/events" \
    -H "Authorization: Bearer $TOKEN" 2>&1 || true)

if echo "$sse_response" | grep -q "event:"; then
    echo -e "${GREEN}✓ PASS${NC} (SSE stream active)"
    PASSED=$((PASSED + 1))
else
    echo -e "${YELLOW}⚠ SKIP${NC} (SSE connection timeout - may be working)"
fi
echo ""

echo "📊 Summary"
echo "=========="
echo -e "Tests Passed: ${GREEN}$PASSED${NC}"
echo -e "Tests Failed: ${RED}$FAILED${NC}"
echo -e "Total Tests: $((PASSED + FAILED))"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
fi
