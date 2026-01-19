#!/bin/bash

# Live Readiness Gate Script
# Checks for known runtime errors and data consistency issues
# Exit code 0 = ready for live, Exit code 1 = not ready

set -e

CHECKS_PASSED=0
CHECKS_FAILED=0

echo "========================================="
echo "LIVE TRADING READINESS GATE"
echo "========================================="
echo ""

# Function to report check result
check_result() {
    local check_name="$1"
    local result="$2"
    
    if [ "$result" -eq 0 ]; then
        echo "✅ PASS: $check_name"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
    else
        echo "❌ FAIL: $check_name"
        CHECKS_FAILED=$((CHECKS_FAILED + 1))
    fi
}

# Check 1: No critical errors in recent logs
echo "🔍 Check 1: Scanning logs for known errors (last 10 minutes)..."

# Check if journald is available
if command -v journalctl &> /dev/null; then
    # Check for "cannot access local variable 'db'" error
    if journalctl --since "10 minutes ago" | grep -q "cannot access local variable 'db'"; then
        echo "   ⚠️  Found 'db variable' errors in logs"
        check_result "No db variable errors" 1
    else
        check_result "No db variable errors" 0
    fi
    
    # Check for "current_price is not defined" error
    if journalctl --since "10 minutes ago" | grep -q "current_price is not defined"; then
        echo "   ⚠️  Found 'current_price undefined' errors in logs"
        check_result "No current_price errors" 1
    else
        check_result "No current_price errors" 0
    fi
    
    # Check for "new_total_profit is not defined" error
    if journalctl --since "10 minutes ago" | grep -q "new_total_profit is not defined"; then
        echo "   ⚠️  Found 'new_total_profit undefined' errors in logs"
        check_result "No new_total_profit errors" 1
    else
        check_result "No new_total_profit errors" 0
    fi
    
    # Check for general tracebacks (Python errors)
    TRACEBACK_COUNT=$(journalctl --since "10 minutes ago" | grep -c "Traceback" || true)
    if [ "$TRACEBACK_COUNT" -gt 5 ]; then
        echo "   ⚠️  Found $TRACEBACK_COUNT traceback errors (threshold: 5)"
        check_result "Low traceback error rate" 1
    else
        echo "   ℹ️  Found $TRACEBACK_COUNT traceback errors (acceptable)"
        check_result "Low traceback error rate" 0
    fi
else
    echo "   ⚠️  journalctl not available, skipping log checks"
    check_result "journalctl available" 1
fi

echo ""

# Check 2: API endpoint health
echo "🔍 Check 2: Testing API endpoints..."

# Check if server is running
if curl -f -s http://localhost:8000/api/health/ping > /dev/null 2>&1; then
    check_result "Server responding" 0
else
    echo "   ⚠️  Server not responding on port 8000"
    check_result "Server responding" 1
fi

# Check realtime endpoint
if curl -f -s http://localhost:8000/api/realtime/events -m 2 > /dev/null 2>&1; then
    check_result "Realtime endpoint reachable" 0
else
    echo "   ⚠️  Realtime endpoint not reachable"
    check_result "Realtime endpoint reachable" 1
fi

echo ""

# Check 3: Profit calculation consistency
echo "🔍 Check 3: Verifying profit calculations..."

# This requires API access with authentication - skip if not available
# In production, this would use a service account or admin token

echo "   ℹ️  Profit consistency check requires authentication - manual verification needed"
echo "   ℹ️  Verify: /api/profits and /api/profits/summary return same total_profit"

echo ""

# Check 4: Database connectivity
echo "🔍 Check 4: Testing database connectivity..."

# Test MongoDB connection
if command -v mongosh &> /dev/null; then
    if mongosh --quiet --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
        check_result "MongoDB responding" 0
    else
        echo "   ⚠️  MongoDB ping failed"
        check_result "MongoDB responding" 1
    fi
elif command -v mongo &> /dev/null; then
    if mongo --quiet --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
        check_result "MongoDB responding" 0
    else
        echo "   ⚠️  MongoDB ping failed"
        check_result "MongoDB responding" 1
    fi
else
    echo "   ⚠️  MongoDB client not available"
    check_result "MongoDB client available" 1
fi

echo ""

# Check 5: API keys configured
echo "🔍 Check 5: Checking API key configuration..."

# This also requires authentication - skip if not available
echo "   ℹ️  API key check requires authentication - manual verification needed"
echo "   ℹ️  Verify: At least one exchange key is saved and tested via /api/keys/list"

echo ""

# Summary
echo "========================================="
echo "READINESS GATE SUMMARY"
echo "========================================="
echo "Checks Passed: $CHECKS_PASSED"
echo "Checks Failed: $CHECKS_FAILED"
echo ""

if [ "$CHECKS_FAILED" -eq 0 ]; then
    echo "✅ SYSTEM READY FOR LIVE TRADING"
    echo ""
    exit 0
else
    echo "❌ SYSTEM NOT READY FOR LIVE TRADING"
    echo ""
    echo "Please fix the failed checks before enabling live mode."
    echo ""
    exit 1
fi
