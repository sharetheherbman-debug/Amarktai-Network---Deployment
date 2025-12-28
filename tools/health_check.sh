#!/bin/bash
# Amarktai Network - Health Check Script
# Verifies deployment is working correctly
# Run as: bash tools/health_check.sh

set -e  # Exit on error

echo "🏥 Amarktai Network - Health Check"
echo "==================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

# Helper functions
check_pass() {
    echo -e "${GREEN}✅ $1${NC}"
}

check_fail() {
    echo -e "${RED}❌ $1${NC}"
    ((ERRORS++))
}

check_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    ((WARNINGS++))
}

# Configuration
API_URL="http://127.0.0.1:8000"
BACKEND_DIR="/var/amarktai/app/backend"
FRONTEND_BUILD_DIR="/var/amarktai/app/frontend/build"

# Check 1: System dependencies
echo ""
echo "1️⃣  Checking system dependencies..."

if command -v python3.12 &> /dev/null; then
    check_pass "Python 3.12 installed ($(python3.12 --version))"
else
    check_fail "Python 3.12 not found"
fi

if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    if [[ $NODE_VERSION == v20* ]]; then
        check_pass "Node.js 20.x installed ($NODE_VERSION)"
    else
        check_warn "Node.js version is $NODE_VERSION (expected 20.x)"
    fi
else
    check_warn "Node.js not found (optional for runtime)"
fi

# Check 2: Directory structure
echo ""
echo "2️⃣  Checking directory structure..."

if [ -d "$BACKEND_DIR" ]; then
    check_pass "Backend directory exists"
else
    check_fail "Backend directory not found: $BACKEND_DIR"
fi

if [ -f "$BACKEND_DIR/.env" ]; then
    check_pass ".env file exists"
else
    check_warn ".env file not found (required for startup)"
fi

if [ -d "/var/amarktai/venv" ]; then
    check_pass "Virtual environment exists"
else
    check_fail "Virtual environment not found"
fi

if [ -d "$FRONTEND_BUILD_DIR" ]; then
    if [ -f "$FRONTEND_BUILD_DIR/index.html" ]; then
        check_pass "Frontend build exists"
    else
        check_warn "Frontend build directory exists but index.html missing"
    fi
else
    check_warn "Frontend build not found (optional)"
fi

# Check 3: Systemd service
echo ""
echo "3️⃣  Checking systemd service..."

if systemctl list-unit-files | grep -q amarktai-api.service; then
    check_pass "Systemd service installed"
    
    if systemctl is-enabled --quiet amarktai-api; then
        check_pass "Service is enabled"
    else
        check_warn "Service is not enabled (won't start on boot)"
    fi
    
    if systemctl is-active --quiet amarktai-api; then
        check_pass "Service is running"
    else
        check_fail "Service is not running"
        echo "   Start with: sudo systemctl start amarktai-api"
    fi
else
    check_warn "Systemd service not installed"
fi

# Check 4: API health endpoint
echo ""
echo "4️⃣  Checking API endpoints..."

if systemctl is-active --quiet amarktai-api 2>/dev/null; then
    # Wait a moment for service to be ready
    sleep 2
    
    # Test health endpoint
    if curl -s -f "$API_URL/api/health/ping" > /dev/null 2>&1; then
        RESPONSE=$(curl -s "$API_URL/api/health/ping")
        if echo "$RESPONSE" | grep -q "pong"; then
            check_pass "Health check endpoint working"
        else
            check_fail "Health check returned unexpected response"
        fi
    else
        check_fail "Health check endpoint not responding"
        echo "   URL: $API_URL/api/health/ping"
    fi
    
    # Test OpenAPI
    if curl -s -f "$API_URL/openapi.json" > /dev/null 2>&1; then
        check_pass "OpenAPI endpoint working"
        
        # Check for required routes
        OPENAPI=$(curl -s "$API_URL/openapi.json")
        REQUIRED_ROUTES=(
            "/api/auth/login"
            "/api/health/ping"
            "/api/realtime/events"
            "/api/system/ping"
        )
        
        for route in "${REQUIRED_ROUTES[@]}"; do
            if echo "$OPENAPI" | grep -q "$route"; then
                check_pass "Route $route found"
            else
                check_warn "Route $route not found"
            fi
        done
    else
        check_warn "OpenAPI endpoint not responding"
    fi
else
    check_warn "Service not running, skipping API tests"
fi

# Check 5: Logs
echo ""
echo "5️⃣  Checking logs..."

if [ -d "/var/amarktai/logs" ]; then
    check_pass "Log directory exists"
else
    check_warn "Log directory not found"
fi

if systemctl list-unit-files | grep -q amarktai-api.service; then
    if journalctl -u amarktai-api -n 1 &> /dev/null; then
        check_pass "Journal logs accessible"
        
        # Check for errors in recent logs
        ERROR_COUNT=$(journalctl -u amarktai-api --since "5 minutes ago" --no-pager | grep -i "error\|fail\|exception" | wc -l)
        if [ $ERROR_COUNT -gt 0 ]; then
            check_warn "Found $ERROR_COUNT error messages in recent logs"
            echo "   View with: sudo journalctl -u amarktai-api -n 50"
        else
            check_pass "No errors in recent logs"
        fi
    fi
fi

# Summary
echo ""
echo "==================================="
echo "📊 Health Check Summary"
echo "==================================="
echo ""
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo ""
    echo "🎉 Deployment is healthy"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  $WARNINGS warning(s)${NC}"
    echo ""
    echo "Deployment is working but has warnings"
    exit 0
else
    echo -e "${RED}❌ $ERRORS error(s), $WARNINGS warning(s)${NC}"
    echo ""
    echo "Action required:"
    if [ $ERRORS -gt 0 ]; then
        echo "1. Fix errors listed above"
        echo "2. Check service logs: sudo journalctl -u amarktai-api -n 50"
        echo "3. Verify .env configuration"
        echo "4. Run health check again"
    fi
    exit 1
fi
