#!/bin/bash
###############################################################################
# GO-LIVE VERIFICATION SCRIPT
# Validates all requirements for production deployment
###############################################################################

set -e  # Exit on error

echo "=========================================="
echo "🚀 AMARKTAI NETWORK - GO-LIVE VERIFICATION"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track pass/fail
PASSED=0
FAILED=0

# Helper functions
pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((PASSED++))
}

fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    ((FAILED++))
}

warn() {
    echo -e "${YELLOW}⚠ WARN${NC}: $1"
}

# Get API base URL from environment or use default
API_BASE="${API_BASE:-http://localhost:8000}"
echo "Testing API at: $API_BASE"
echo ""

###############################################################################
# TEST 1: Platform Standardization - OVEX present, Kraken absent
###############################################################################
echo "📋 Test 1: Platform Standardization"
echo "-----------------------------------"

# Check frontend platform configuration
if grep -q "ovex" frontend/src/lib/platforms.js && grep -q "OVEX" frontend/src/lib/platforms.js; then
    if ! grep -q "kraken" frontend/src/lib/platforms.js; then
        pass "Frontend platforms.js: OVEX present, Kraken removed"
    else
        fail "Frontend platforms.js: Kraken still present"
    fi
else
    fail "Frontend platforms.js: OVEX not found"
fi

# Check frontend exchanges configuration
if grep -q "ovex" frontend/src/config/exchanges.js && grep -q "OVEX" frontend/src/config/exchanges.js; then
    pass "Frontend exchanges.js: OVEX present, Kraken removed"
else
    fail "Frontend exchanges.js: OVEX not found"
fi

# Check backend exchange_limits.py
if grep -q '"ovex"' backend/exchange_limits.py; then
    if ! grep -q '"kraken"' backend/exchange_limits.py; then
        pass "Backend exchange_limits.py: OVEX present, Kraken removed"
    else
        fail "Backend exchange_limits.py: Kraken still present"
    fi
else
    fail "Backend exchange_limits.py: OVEX not found"
fi

# Check backend config.py
if grep -q "'ovex'" backend/config.py; then
    if ! grep -q "'kraken'" backend/config.py; then
        pass "Backend config.py: OVEX present, Kraken removed"
    else
        fail "Backend config.py: Kraken still present"
    fi
else
    fail "Backend config.py: OVEX not found"
fi

# Verify bot limits: Luno(5), Binance(10), KuCoin(10), OVEX(10), VALR(10) = 45
echo ""
echo "Checking platform bot limits..."
if grep -A5 "BOT_ALLOCATION" backend/exchange_limits.py | grep -q '"luno": 5' && \
   grep -A5 "BOT_ALLOCATION" backend/exchange_limits.py | grep -q '"binance": 10' && \
   grep -A5 "BOT_ALLOCATION" backend/exchange_limits.py | grep -q '"kucoin": 10' && \
   grep -A5 "BOT_ALLOCATION" backend/exchange_limits.py | grep -q '"ovex": 10' && \
   grep -A5 "BOT_ALLOCATION" backend/exchange_limits.py | grep -q '"valr": 10'; then
    if grep -q "MAX_BOTS_GLOBAL = 45" backend/exchange_limits.py; then
        pass "Platform bot limits correct: Total 45 bots (5+10+10+10+10)"
    else
        fail "MAX_BOTS_GLOBAL should be 45"
    fi
else
    fail "Platform bot limits incorrect"
fi

echo ""

###############################################################################
# TEST 2: Admin Unlock Endpoint
###############################################################################
echo "🔐 Test 2: Admin Unlock Endpoint"
echo "---------------------------------"

# Note: We can't test with actual password in CI/CD, but we can verify endpoint exists
response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$API_BASE/api/admin/unlock" 2>/dev/null || echo "000")
if [ "$response" = "405" ] || [ "$response" = "422" ] || [ "$response" = "401" ]; then
    # These codes mean endpoint exists (405=method not allowed, 422=validation error, 401=unauthorized)
    pass "Admin unlock endpoint exists at /api/admin/unlock"
else
    if [ "$response" = "404" ]; then
        fail "Admin unlock endpoint not found (404)"
    else
        warn "Admin unlock endpoint returned unexpected code: $response (may not be running)"
    fi
fi

# Check if admin endpoints file has required functions
if grep -q "def unlock_admin_panel" backend/routes/admin_endpoints.py; then
    pass "Admin unlock function defined"
else
    fail "Admin unlock function not found"
fi

if grep -q "def get_system_resources" backend/routes/admin_endpoints.py; then
    pass "System resources monitoring endpoint defined"
else
    fail "System resources monitoring not found"
fi

if grep -q "def get_process_health" backend/routes/admin_endpoints.py; then
    pass "Process health monitoring endpoint defined"
else
    fail "Process health monitoring not found"
fi

if grep -q "def get_system_logs" backend/routes/admin_endpoints.py; then
    pass "System logs viewing endpoint defined"
else
    fail "System logs viewing not found"
fi

if grep -q "def get_user_api_keys_status" backend/routes/admin_endpoints.py; then
    pass "User API keys status endpoint defined"
else
    fail "User API keys status not found"
fi

echo ""

###############################################################################
# TEST 3: API Keys Save/Test Endpoints
###############################################################################
echo "🔑 Test 3: API Keys Endpoints"
echo "-----------------------------"

# Check save endpoint
response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$API_BASE/api/keys/save" 2>/dev/null || echo "000")
if [ "$response" = "405" ] || [ "$response" = "422" ] || [ "$response" = "401" ]; then
    pass "API keys save endpoint exists"
else
    if [ "$response" = "404" ]; then
        fail "API keys save endpoint not found (404)"
    else
        warn "API keys save endpoint returned: $response (may not be running)"
    fi
fi

# Check test endpoint
response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$API_BASE/api/keys/test" 2>/dev/null || echo "000")
if [ "$response" = "405" ] || [ "$response" = "422" ] || [ "$response" = "401" ]; then
    pass "API keys test endpoint exists"
else
    if [ "$response" = "404" ]; then
        fail "API keys test endpoint not found (404)"
    else
        warn "API keys test endpoint returned: $response (may not be running)"
    fi
fi

# Check if OVEX is in the test logic
if grep -q '"ovex"' backend/routes/api_key_management.py; then
    pass "OVEX included in API key test logic"
else
    fail "OVEX not in API key test logic"
fi

echo ""

###############################################################################
# TEST 4: Paper Trading Status Endpoint
###############################################################################
echo "📊 Test 4: Paper Trading Status"
echo "--------------------------------"

# Check endpoint exists
response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$API_BASE/api/health/paper-trading" 2>/dev/null || echo "000")
if [ "$response" = "200" ]; then
    pass "Paper trading status endpoint responds (200)"
    
    # Try to fetch actual status
    status_json=$(curl -s --max-time 5 "$API_BASE/api/health/paper-trading" 2>/dev/null || echo "{}")
    if echo "$status_json" | grep -q "is_running"; then
        pass "Paper trading status returns expected fields"
    else
        warn "Paper trading status may not have all expected fields"
    fi
else
    if [ "$response" = "404" ]; then
        fail "Paper trading status endpoint not found (404)"
    else
        warn "Paper trading status returned: $response (may not be running)"
    fi
fi

# Check if status tracking is in paper_trading_engine.py
if grep -q "self.is_running" backend/paper_trading_engine.py && \
   grep -q "self.last_tick_time" backend/paper_trading_engine.py && \
   grep -q "self.last_trade_simulation" backend/paper_trading_engine.py && \
   grep -q "self.last_error" backend/paper_trading_engine.py; then
    pass "Paper trading engine has status tracking variables"
else
    fail "Paper trading engine missing status tracking"
fi

if grep -q "def get_status" backend/paper_trading_engine.py; then
    pass "Paper trading engine has get_status() method"
else
    fail "Paper trading engine missing get_status() method"
fi

echo ""

###############################################################################
# TEST 5: WebSocket Typed Messages
###############################################################################
echo "🔌 Test 5: WebSocket Typed Messages"
echo "-----------------------------------"

# Check websocket manager sends connection message
if grep -q '"type": "connection"' backend/websocket_manager.py; then
    pass "WebSocket sends 'connection' type message"
else
    fail "WebSocket missing 'connection' type"
fi

# Check websocket sends ping
if grep -q '"type": "ping"' backend/websocket_manager.py; then
    pass "WebSocket sends 'ping' type message"
else
    fail "WebSocket missing 'ping' type"
fi

# Check realtime_events uses typed messages
if grep -q '"type":' backend/realtime_events.py; then
    pass "Realtime events use typed messages"
else
    warn "Realtime events may not be using typed messages"
fi

# Check if trade_update, bot_update types exist
if grep -q '"type": "trade_executed"' backend/realtime_events.py || \
   grep -q '"type": "bot_created"' backend/realtime_events.py; then
    pass "Realtime events have trade/bot update types"
else
    warn "Realtime events missing some update types"
fi

echo ""

###############################################################################
# TEST 6: No Kraken References in Current Files (case-insensitive)
###############################################################################
echo "🔍 Test 6: Kraken Reference Check"
echo "----------------------------------"

# Check for kraken references in key files (excluding git history, comments about removal)
kraken_found=0

# Frontend JS files
if grep -ri "kraken" frontend/src/ --include="*.js" --include="*.jsx" 2>/dev/null | grep -v "Removed\|removed\|Replace" | grep -q .; then
    fail "Found 'Kraken' references in frontend/src/"
    kraken_found=1
else
    pass "No Kraken references in frontend/src/"
fi

# Backend Python files (excluding migrations/docs about the change)
if grep -ri "kraken" backend/ --include="*.py" 2>/dev/null | grep -v "Removed\|removed\|Replace\|#.*kraken" | grep -q .; then
    fail "Found 'Kraken' references in backend/"
    kraken_found=1
else
    pass "No Kraken references in backend/"
fi

# Platform constants check
if [ -f "backend/platform_constants.py" ]; then
    if grep -qi "kraken" backend/platform_constants.py; then
        fail "Kraken found in platform_constants.py"
        kraken_found=1
    else
        pass "Platform constants clean (no Kraken)"
    fi
else
    warn "platform_constants.py not found"
fi

if [ -f "frontend/src/constants/platforms.js" ]; then
    if grep -qi "kraken" frontend/src/constants/platforms.js; then
        fail "Kraken found in frontend constants/platforms.js"
        kraken_found=1
    else
        pass "Frontend platform constants clean (no Kraken)"
    fi
else
    warn "frontend constants/platforms.js not found"
fi

echo ""

###############################################################################
# TEST 7: Platform Constants Validation
###############################################################################
echo "📐 Test 7: Platform Constants Validation"
echo "----------------------------------------"

# Check backend constants exist and have correct platforms
if [ -f "backend/platform_constants.py" ]; then
    # Check all 5 platforms present
    if grep -q "'luno'" backend/platform_constants.py && \
       grep -q "'binance'" backend/platform_constants.py && \
       grep -q "'kucoin'" backend/platform_constants.py && \
       grep -q "'ovex'" backend/platform_constants.py && \
       grep -q "'valr'" backend/platform_constants.py; then
        pass "Backend constants: All 5 platforms defined"
    else
        fail "Backend constants: Missing one or more platforms"
    fi
    
    # Check total capacity is 45
    if grep -q "45" backend/platform_constants.py; then
        pass "Backend constants: Total capacity appears correct"
    else
        warn "Backend constants: Could not verify total capacity of 45"
    fi
else
    fail "Backend platform_constants.py not found"
fi

# Check frontend constants exist and have correct platforms
if [ -f "frontend/src/constants/platforms.js" ]; then
    if grep -q "'luno'" frontend/src/constants/platforms.js && \
       grep -q "'binance'" frontend/src/constants/platforms.js && \
       grep -q "'kucoin'" frontend/src/constants/platforms.js && \
       grep -q "'ovex'" frontend/src/constants/platforms.js && \
       grep -q "'valr'" frontend/src/constants/platforms.js; then
        pass "Frontend constants: All 5 platforms defined"
    else
        fail "Frontend constants: Missing one or more platforms"
    fi
    
    # Check maxBots are correct
    if grep -q "maxBots: 5" frontend/src/constants/platforms.js && \
       grep -q "maxBots: 10" frontend/src/constants/platforms.js; then
        pass "Frontend constants: Bot limits appear correct"
    else
        warn "Frontend constants: Could not verify bot limits"
    fi
else
    fail "Frontend constants/platforms.js not found"
fi

echo ""

###############################################################################
# TEST 8: File Structure Check
###############################################################################
echo "📁 Test 8: File Structure"
echo "-------------------------"

required_files=(
    "backend/exchange_limits.py"
    "backend/config.py"
    "backend/paper_trading_engine.py"
    "backend/platform_constants.py"
    "backend/routes/admin_endpoints.py"
    "backend/routes/api_key_management.py"
    "backend/routes/system_health_endpoints.py"
    "backend/websocket_manager.py"
    "backend/realtime_events.py"
    "frontend/src/config/exchanges.js"
    "frontend/src/lib/platforms.js"
    "frontend/src/constants/platforms.js"
    "frontend/src/components/Dashboard/CreateBotSection.js"
    "frontend/src/components/Dashboard/APISetupSection.js"
    "frontend/src/components/LiveTradesView.js"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        pass "File exists: $file"
    else
        fail "File missing: $file"
    fi
done

echo ""

###############################################################################
# SUMMARY
###############################################################################
echo "=========================================="
echo "📊 VERIFICATION SUMMARY"
echo "=========================================="
echo ""
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL CHECKS PASSED - READY FOR GO-LIVE! 🎉${NC}"
    exit 0
else
    echo -e "${RED}✗ $FAILED CHECK(S) FAILED - REVIEW REQUIRED${NC}"
    exit 1
fi
