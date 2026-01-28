#!/bin/bash
# Test SPA Routing - Validates deep linking works correctly
# This script tests that all React Router routes return 200 (serving index.html)
# rather than 404 (nginx treating them as missing files)

set -e

# Configuration
BASE_URL="${BASE_URL:-http://localhost:80}"
TIMEOUT=5

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

echo "======================================"
echo "   SPA ROUTING VALIDATION TEST"
echo "======================================"
echo "Base URL: $BASE_URL"
echo "Timeout: ${TIMEOUT}s"
echo ""

# Function to test a route
test_route() {
    local route="$1"
    local description="$2"
    local url="${BASE_URL}${route}"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    echo -n "Testing $description ($route)... "
    
    # Make request and capture HTTP status code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT "$url" 2>/dev/null || echo "000")
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $http_code)"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# Function to test API routes (should also return 200 or expected status)
test_api_route() {
    local route="$1"
    local description="$2"
    local expected_code="${3:-200}"
    local url="${BASE_URL}${route}"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    echo -n "Testing $description ($route)... "
    
    # Make request and capture HTTP status code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT "$url" 2>/dev/null || echo "000")
    
    # Check if status code matches expected (200, 401, etc.)
    if [ "$http_code" = "$expected_code" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $http_code, expected $expected_code)"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# Test SPA routes (should all return 200 and serve index.html)
echo "=== Testing SPA Deep Links ==="
test_route "/" "Home page"
test_route "/dashboard" "Dashboard page"
test_route "/login" "Login page"
test_route "/register" "Register page"
test_route "/bots" "Bots page"
test_route "/settings" "Settings page"
test_route "/wallet" "Wallet page"
test_route "/analytics" "Analytics page"
test_route "/profile" "Profile page"

# Test some non-existent SPA routes (should still return 200 with index.html)
echo ""
echo "=== Testing Non-Existent Routes (Should Still Serve SPA) ==="
test_route "/nonexistent" "Non-existent route"
test_route "/bots/123" "Bot detail route"
test_route "/settings/api-keys" "Settings sub-route"

# Test API routes (should proxy to backend, not serve index.html)
echo ""
echo "=== Testing API Routes (Should Proxy to Backend) ==="
test_api_route "/api/health/ping" "Health check API" "200"
# Auth endpoints might return 401 without token, which is correct behavior
test_api_route "/api/bots" "Bots API" "401"

# Test static assets return 404 for missing files (not index.html)
echo ""
echo "=== Testing Static Asset Handling ==="
echo -n "Testing missing static asset... "
http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT "${BASE_URL}/static/missing.js" 2>/dev/null || echo "000")
if [ "$http_code" = "404" ]; then
    echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code - correctly returns 404, not index.html)"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
else
    echo -e "${RED}✗ FAIL${NC} (HTTP $http_code - should return 404 for missing static files)"
    FAILED_TESTS=$((FAILED_TESTS + 1))
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
fi

# Print summary
echo ""
echo "======================================"
echo "   TEST SUMMARY"
echo "======================================"
echo "Total Tests: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}"
echo "======================================"

# Exit with appropriate code
if [ $FAILED_TESTS -gt 0 ]; then
    echo -e "${RED}RESULT: FAILED${NC}"
    echo ""
    echo "Some routes are not working correctly."
    echo "Check your nginx configuration and ensure:"
    echo "1. 'try_files \$uri \$uri/ /index.html;' is present in location / block"
    echo "2. API routes are proxied before the catch-all SPA route"
    echo "3. Static assets are handled correctly"
    exit 1
else
    echo -e "${GREEN}RESULT: ALL TESTS PASSED${NC}"
    echo ""
    echo "SPA routing is configured correctly!"
    echo "Deep linking should work for all React Router routes."
    exit 0
fi
