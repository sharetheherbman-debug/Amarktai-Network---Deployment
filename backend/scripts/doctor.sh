#!/bin/bash
# Backend Doctor Script - Pre-flight health checks
# Runs: python compile check, unit sanity checks, curl local health, prints actionable errors
# Exit code 0 = healthy, non-zero = issues found

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$BACKEND_DIR")"

echo "========================================="
echo "🏥 Backend Doctor - Pre-Flight Health Checks"
echo "========================================="
echo ""
echo "Backend directory: $BACKEND_DIR"
echo "Project root: $PROJECT_ROOT"
echo ""

ISSUES_FOUND=0

# ============================================================================
# STEP 1: Check Python installation
# ============================================================================
echo "📍 Step 1: Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "❌ ERROR: python3 not found in PATH"
    echo "   → Install Python 3.8+ and ensure it's in your PATH"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo "✅ Python found: $PYTHON_VERSION"
fi
echo ""

# ============================================================================
# STEP 2: Check if we're in a virtual environment (recommended but not required)
# ============================================================================
echo "📍 Step 2: Checking virtual environment..."
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo "⚠️  WARNING: Not running in a virtual environment"
    echo "   → Recommended: source venv/bin/activate"
else
    echo "✅ Virtual environment active: $VIRTUAL_ENV"
fi
echo ""

# ============================================================================
# STEP 3: Python syntax check (compile all .py files)
# ============================================================================
echo "📍 Step 3: Checking Python syntax (py_compile)..."
cd "$BACKEND_DIR"

COMPILE_ERRORS=0
# Check main files
for file in server.py auth.py database.py config.py; do
    if [[ -f "$file" ]]; then
        if python3 -m py_compile "$file" 2>&1; then
            echo "  ✓ $file"
        else
            echo "  ✗ $file - SYNTAX ERROR"
            COMPILE_ERRORS=$((COMPILE_ERRORS + 1))
        fi
    fi
done

# Check routes directory
if [[ -d "routes" ]]; then
    for file in routes/*.py; do
        if [[ -f "$file" ]]; then
            if python3 -m py_compile "$file" 2>&1 | grep -v "wrote"; then
                echo "  ✓ $(basename $file)"
            else
                echo "  ✗ $(basename $file) - SYNTAX ERROR"
                COMPILE_ERRORS=$((COMPILE_ERRORS + 1))
            fi
        fi
    done
fi

if [[ $COMPILE_ERRORS -eq 0 ]]; then
    echo "✅ All Python files compile successfully"
else
    echo "❌ $COMPILE_ERRORS file(s) have syntax errors"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi
echo ""

# ============================================================================
# STEP 4: Check required dependencies
# ============================================================================
echo "📍 Step 4: Checking required dependencies..."
MISSING_DEPS=0

for pkg in fastapi uvicorn motor pymongo passlib jose python-multipart; do
    if python3 -c "import $pkg" 2>/dev/null; then
        echo "  ✓ $pkg"
    else
        echo "  ✗ $pkg - MISSING"
        MISSING_DEPS=$((MISSING_DEPS + 1))
    fi
done

if [[ $MISSING_DEPS -eq 0 ]]; then
    echo "✅ All core dependencies installed"
else
    echo "❌ $MISSING_DEPS core dependencies missing"
    echo "   → Run: pip install -r requirements.txt"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi
echo ""

# ============================================================================
# STEP 5: Check environment variables
# ============================================================================
echo "📍 Step 5: Checking environment variables..."
ENV_ISSUES=0

# Check .env file exists
if [[ ! -f "$PROJECT_ROOT/.env" ]] && [[ ! -f "$BACKEND_DIR/.env" ]]; then
    echo "  ⚠️  No .env file found (using defaults)"
else
    echo "  ✓ .env file found"
fi

# Check critical env vars
if [[ -z "${MONGODB_URL:-}" ]]; then
    echo "  ⚠️  MONGODB_URL not set (will use default: mongodb://localhost:27017)"
else
    echo "  ✓ MONGODB_URL is set"
fi

if [[ -z "${JWT_SECRET:-}" ]] || [[ "${JWT_SECRET:-}" == "your-secret-key" ]]; then
    echo "  ❌ JWT_SECRET not properly configured"
    echo "     → Must be set to a secure value (32+ characters)"
    ENV_ISSUES=$((ENV_ISSUES + 1))
else
    echo "  ✓ JWT_SECRET is configured"
fi

if [[ $ENV_ISSUES -gt 0 ]]; then
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi
echo ""

# ============================================================================
# STEP 6: Try to start server and check health endpoint (if no other issues)
# ============================================================================
if [[ $ISSUES_FOUND -eq 0 ]]; then
    echo "📍 Step 6: Testing server startup and health endpoint..."
    
    # Start server in background
    cd "$BACKEND_DIR"
    export PYTHONUNBUFFERED=1
    
    # Start server and capture PID
    python3 -m uvicorn server:app --host 127.0.0.1 --port 8765 > /tmp/doctor_server.log 2>&1 &
    SERVER_PID=$!
    
    echo "  → Started test server (PID: $SERVER_PID)"
    echo "  → Waiting 8 seconds for startup..."
    sleep 8
    
    # Check if process is still running
    if ! kill -0 $SERVER_PID 2>/dev/null; then
        echo "  ❌ Server crashed during startup"
        echo "  → Check logs:"
        tail -20 /tmp/doctor_server.log
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    else
        # Test health endpoint
        echo "  → Testing http://127.0.0.1:8765/api/health/ping"
        
        if curl -f -s -m 5 http://127.0.0.1:8765/api/health/ping > /tmp/doctor_health.json 2>&1; then
            echo "  ✅ Health endpoint responded:"
            cat /tmp/doctor_health.json | python3 -m json.tool 2>/dev/null || cat /tmp/doctor_health.json
        else
            echo "  ❌ Health endpoint failed or timed out"
            echo "  → Check logs:"
            tail -20 /tmp/doctor_server.log
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
        fi
        
        # Cleanup: kill test server
        echo "  → Stopping test server..."
        kill $SERVER_PID 2>/dev/null || true
        wait $SERVER_PID 2>/dev/null || true
    fi
else
    echo "📍 Step 6: Skipping server test due to previous issues"
fi
echo ""

# ============================================================================
# FINAL REPORT
# ============================================================================
echo "========================================="
echo "🏥 Backend Doctor - Final Report"
echo "========================================="

if [[ $ISSUES_FOUND -eq 0 ]]; then
    echo "✅ ALL CHECKS PASSED - Backend is healthy!"
    echo ""
    echo "Next steps:"
    echo "  1. Start server: uvicorn server:app --host 0.0.0.0 --port 8000"
    echo "  2. Or with systemd: sudo systemctl start amarktai-backend"
    echo "  3. Check logs: journalctl -u amarktai-backend -f"
    exit 0
else
    echo "❌ ISSUES FOUND: $ISSUES_FOUND"
    echo ""
    echo "Action required:"
    echo "  1. Review errors above"
    echo "  2. Fix issues and re-run: ./backend/scripts/doctor.sh"
    echo "  3. See DEPLOY.md for deployment guide"
    exit 1
fi
