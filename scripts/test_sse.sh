#!/bin/bash
# Test SSE (Server-Sent Events) endpoint connectivity
# This script logs in and connects to the SSE endpoint for 5 seconds

set -e

API_BASE="${API_BASE:-http://localhost:8000/api}"
TEST_EMAIL="${TEST_EMAIL:-test@example.com}"
TEST_PASSWORD="${TEST_PASSWORD:-testpass123}"

echo "🔌 Testing SSE Endpoint"
echo "======================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Login to get token
echo "📝 Step 1: Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "${API_BASE}/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${TEST_EMAIL}\",\"password\":\"${TEST_PASSWORD}\"}" || echo "{}")

TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}✗ Login failed. Please ensure:${NC}"
    echo "  1. Backend server is running"
    echo "  2. Test user exists (email: ${TEST_EMAIL})"
    echo "  3. API_BASE is correct (current: ${API_BASE})"
    echo ""
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓ Login successful${NC}"
echo ""

# Step 2: Connect to SSE endpoint
echo "🔌 Step 2: Connecting to SSE endpoint..."
echo "Endpoint: ${API_BASE}/realtime/events"
echo "Duration: 5 seconds"
echo ""

# Connect to SSE with timeout
SSE_OUTPUT=$(timeout 5s curl -s -N \
  -H "Authorization: Bearer ${TOKEN}" \
  "${API_BASE}/realtime/events" || true)

# Check if we got any events
if [ -z "$SSE_OUTPUT" ]; then
    echo -e "${RED}✗ No SSE events received${NC}"
    echo "Possible issues:"
    echo "  1. SSE endpoint not properly registered"
    echo "  2. Nginx buffering enabled (should be disabled)"
    echo "  3. Network/firewall issues"
    exit 1
fi

# Parse events
HEARTBEAT_COUNT=$(echo "$SSE_OUTPUT" | grep -c "event: heartbeat" || echo "0")
OVERVIEW_COUNT=$(echo "$SSE_OUTPUT" | grep -c "event: overview_update" || echo "0")
BOT_UPDATE_COUNT=$(echo "$SSE_OUTPUT" | grep -c "event: bot_update" || echo "0")

echo "📊 SSE Events Received:"
echo "  - Heartbeats: $HEARTBEAT_COUNT"
echo "  - Overview Updates: $OVERVIEW_COUNT"
echo "  - Bot Updates: $BOT_UPDATE_COUNT"
echo ""

# Validate minimum requirements
if [ "$HEARTBEAT_COUNT" -ge 1 ]; then
    echo -e "${GREEN}✓ SSE endpoint is working!${NC}"
    echo ""
    echo "Sample events:"
    echo "$SSE_OUTPUT" | head -20
    echo ""
    echo -e "${GREEN}✓ SSE TEST PASSED${NC}"
    exit 0
else
    echo -e "${RED}✗ SSE endpoint not sending heartbeats${NC}"
    echo "Expected at least 1 heartbeat in 5 seconds"
    echo ""
    echo "Raw output:"
    echo "$SSE_OUTPUT"
    exit 1
fi
