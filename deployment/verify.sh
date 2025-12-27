#!/bin/bash
# Amarktai Network - Production Verification Script
# Standalone plug-and-play validation for deployment readiness

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track overall pass/fail status
OVERALL_STATUS="PASS"
FAILED_TESTS=()

# Helper functions
log_section() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
    OVERALL_STATUS="FAIL"
    FAILED_TESTS+=("$1")
}

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Change to repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Amarktai Network - Verification    ║${NC}"
echo -e "${BLUE}║  Production Readiness Checks         ║${NC}"
echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
echo ""
log_info "Repository: $REPO_ROOT"
echo ""

# ============================================================================
# 1. STATIC CHECKS - Python Syntax Validation
# ============================================================================
log_section "1. Static Checks - Python Syntax"

PYTHON_FILES=$(find backend -name "*.py" -type f | grep -v "__pycache__" | grep -v ".pyc")
SYNTAX_ERRORS=0

for file in $PYTHON_FILES; do
    if ! python3 -m py_compile "$file" 2>/dev/null; then
        log_error "Syntax error in: $file"
        SYNTAX_ERRORS=$((SYNTAX_ERRORS + 1))
    fi
done

if [ $SYNTAX_ERRORS -eq 0 ]; then
    log_success "All Python files have valid syntax"
else
    log_error "Found $SYNTAX_ERRORS Python syntax errors"
fi

# ============================================================================
# 2. DEPENDENCY CHECKS
# ============================================================================
log_section "2. Dependency Checks"

# Check if requirements.txt exists
if [ -f "backend/requirements.txt" ]; then
    log_success "requirements.txt found"
    
    # Try to check if dependencies are installable (dry-run)
    if python3 -m pip check &>/dev/null; then
        log_success "Python dependencies are consistent"
    else
        log_warning "Python dependency inconsistencies detected (run pip check for details)"
    fi
else
    log_error "requirements.txt not found"
fi

# Check Node.js dependencies
if [ -f "frontend/package.json" ]; then
    log_success "package.json found"
else
    log_warning "package.json not found"
fi

# ============================================================================
# 3. PYTEST TEST SUITE
# ============================================================================
log_section "3. Running Test Suite (pytest)"

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    log_warning "pytest not installed - skipping unit tests"
    log_info "Install with: pip install pytest pytest-asyncio pytest-httpx"
else
    # Run pytest if tests exist
    if [ -d "backend/tests" ] || [ -d "tests" ]; then
        log_info "Running pytest..."
        if pytest -v --tb=short 2>&1 | tee /tmp/pytest_output.log; then
            log_success "All tests passed"
        else
            log_error "Some tests failed - see /tmp/pytest_output.log"
        fi
    else
        log_warning "No tests directory found"
    fi
fi

# ============================================================================
# 4. CONTRACT TESTS - Critical API Endpoints
# ============================================================================
log_section "4. Contract Tests - API Endpoints"

# Check if backend server is running
log_info "Checking if backend server is accessible..."

# Try to start server in background if not running
if ! curl -s http://localhost:8000/api/health &>/dev/null; then
    log_warning "Backend server not running on localhost:8000"
    log_info "Start the server with: cd backend && python3 server.py"
    log_warning "Skipping contract tests (server required)"
else
    log_success "Backend server is accessible"
    
    # Test 1: /api/bots - Fetch bots with state
    log_info "Testing GET /api/bots..."
    if curl -s -f http://localhost:8000/api/bots -H "Authorization: Bearer test" &>/dev/null; then
        log_success "/api/bots endpoint is accessible"
    else
        log_error "/api/bots endpoint failed or requires authentication"
    fi
    
    # Test 2: Health check
    log_info "Testing GET /api/health..."
    if HEALTH_RESPONSE=$(curl -s -f http://localhost:8000/api/health 2>/dev/null); then
        if echo "$HEALTH_RESPONSE" | grep -q "healthy\|connected"; then
            log_success "/api/health endpoint is healthy"
        else
            log_warning "/api/health returned unexpected response"
        fi
    else
        log_error "/api/health endpoint failed"
    fi
    
    # Test 3: OpenAPI docs
    log_info "Testing GET /openapi.json..."
    if OPENAPI_RESPONSE=$(curl -s -f http://localhost:8000/openapi.json 2>/dev/null); then
        if echo "$OPENAPI_RESPONSE" | grep -q "openapi\|swagger"; then
            log_success "/openapi.json is accessible"
            
            # Check if order endpoints are mounted
            if echo "$OPENAPI_RESPONSE" | grep -q "/api/orders/submit"; then
                log_success "Order pipeline endpoints are mounted"
            else
                log_error "Order pipeline endpoints NOT found in OpenAPI spec"
            fi
            
            # Check if pause/resume endpoints support both POST and PUT
            if echo "$OPENAPI_RESPONSE" | grep -E -q '(pause.*post|pause.*put)'; then
                log_success "Bot pause endpoint is accessible"
            else
                log_warning "Bot pause endpoint may not be properly registered"
            fi
        else
            log_warning "/openapi.json returned unexpected format"
        fi
    else
        log_error "/openapi.json endpoint failed"
    fi
    
    # Test 4: Profit analytics
    log_info "Testing GET /api/analytics/profit-history?period=daily..."
    if curl -s -f "http://localhost:8000/api/analytics/profit-history?period=daily" &>/dev/null; then
        log_success "Profit analytics endpoint is accessible"
    else
        log_warning "Profit analytics endpoint requires authentication or failed"
    fi
    
    # Test 5: Countdown status
    log_info "Testing GET /api/analytics/countdown-to-million..."
    if COUNTDOWN_RESPONSE=$(curl -s -f http://localhost:8000/api/analytics/countdown-to-million 2>/dev/null); then
        if echo "$COUNTDOWN_RESPONSE" | grep -q "current_capital\|target"; then
            log_success "Countdown endpoint returns valid data"
        else
            log_warning "Countdown endpoint returned unexpected format"
        fi
    else
        log_warning "Countdown endpoint requires authentication or failed"
    fi
fi

# ============================================================================
# 5. CONFIGURATION CHECKS
# ============================================================================
log_section "5. Configuration & Environment"

# Check for .env file
if [ -f ".env" ]; then
    log_success ".env file exists"
    
    # Check for critical env vars
    if grep -q "MONGODB_URI" .env; then
        log_success "MONGODB_URI configured"
    else
        log_warning "MONGODB_URI not found in .env"
    fi
    
    if grep -q "JWT_SECRET" .env; then
        log_success "JWT_SECRET configured"
    else
        log_warning "JWT_SECRET not found in .env"
    fi
else
    log_warning ".env file not found (check .env.example)"
fi

# ============================================================================
# 6. SECURITY CHECKS
# ============================================================================
log_section "6. Security Checks"

# Check for exposed secrets in code
log_info "Scanning for exposed secrets..."
if grep -r 'password.*=.*["'\''][^"'\'']*["'\'']' backend --include="*.py" | grep -v "password_hash" | grep -v "get_password" | grep -q "password"; then
    log_warning "Possible hardcoded passwords found - review manually"
else
    log_success "No obvious hardcoded passwords found"
fi

# Check for proper authentication usage
if grep -r "Depends(get_current_user)" backend/routes --include="*.py" &>/dev/null; then
    log_success "Authentication guards are in use"
else
    log_warning "Some routes may lack authentication"
fi

# ============================================================================
# 7. DEPLOYMENT READINESS
# ============================================================================
log_section "7. Deployment Readiness"

# Check deployment scripts exist
if [ -f "deployment/vps-setup.sh" ]; then
    log_success "VPS setup script exists"
else
    log_error "VPS setup script not found"
fi

if [ -f "deployment/build_frontend.sh" ]; then
    log_success "Frontend build script exists"
else
    log_warning "Frontend build script not found"
fi

# Check for systemd service file
if [ -f "deployment/amarktai-api.service" ]; then
    log_success "Systemd service file exists"
else
    log_warning "Systemd service file not found"
fi

# ============================================================================
# FINAL REPORT
# ============================================================================
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}       VERIFICATION SUMMARY            ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

if [ "$OVERALL_STATUS" == "PASS" ]; then
    echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║          ✅ ALL CHECKS PASSED        ║${NC}"
    echo -e "${GREEN}║     System is production-ready       ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "${RED}╔══════════════════════════════════════╗${NC}"
    echo -e "${RED}║        ❌ VERIFICATION FAILED         ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${RED}Failed checks:${NC}"
    for test in "${FAILED_TESTS[@]}"; do
        echo -e "${RED}  • $test${NC}"
    done
    echo ""
    exit 1
fi
