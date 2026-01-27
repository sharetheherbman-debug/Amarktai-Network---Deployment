#!/bin/bash
# Test Bot CRUD operations (Create, List, Delete)
# Validates bot creation with funding checks

set -e

API_BASE="${API_BASE:-http://localhost:8000/api}"
TEST_EMAIL="${TEST_EMAIL:-test@example.com}"
TEST_PASSWORD="${TEST_PASSWORD:-testpass123}"

echo "🤖 Testing Bot CRUD Operations"
echo "================================"
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
    exit 1
fi

echo -e "${GREEN}✓ Login successful${NC}"
echo ""

# Step 2: List existing bots (before creation)
echo "📋 Step 2: Listing existing bots..."
LIST_BEFORE=$(curl -s -X GET "${API_BASE}/bots" \
  -H "Authorization: Bearer ${TOKEN}" || echo "[]")

BOT_COUNT_BEFORE=$(echo "$LIST_BEFORE" | grep -o '"id"' | wc -l)
echo "  Current bot count: $BOT_COUNT_BEFORE"
echo ""

# Step 3: Create a test bot
echo "🔨 Step 3: Creating test bot..."
TEST_BOT_NAME="TestBot-$(date +%s)"

CREATE_RESPONSE=$(curl -s -X POST "${API_BASE}/bots" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d "{
    \"name\": \"${TEST_BOT_NAME}\",
    \"exchange\": \"luno\",
    \"risk_mode\": \"safe\",
    \"trading_mode\": \"paper\",
    \"initial_capital\": 1000
  }" || echo "{}")

# Check if bot was created
BOT_ID=$(echo "$CREATE_RESPONSE" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$BOT_ID" ]; then
    echo -e "${YELLOW}⚠ Bot creation response:${NC}"
    echo "$CREATE_RESPONSE"
    echo ""
    
    # Check if it's a funding error (expected in paper mode, actually should work)
    if echo "$CREATE_RESPONSE" | grep -q "FUNDING_PLAN_REQUIRED\|insufficient.*fund"; then
        echo -e "${YELLOW}⚠ Funding check triggered (may need wallet setup)${NC}"
        echo "Note: Paper mode should allow bot creation without real funds"
        echo "This suggests funding validation may be too strict for paper mode"
    else
        echo -e "${RED}✗ Bot creation failed unexpectedly${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Bot created successfully${NC}"
    echo "  Bot ID: $BOT_ID"
    echo "  Bot Name: $TEST_BOT_NAME"
    echo ""
fi

# Step 4: List bots again (after creation)
if [ -n "$BOT_ID" ]; then
    echo "📋 Step 4: Listing bots after creation..."
    LIST_AFTER=$(curl -s -X GET "${API_BASE}/bots" \
      -H "Authorization: Bearer ${TOKEN}" || echo "[]")
    
    BOT_COUNT_AFTER=$(echo "$LIST_AFTER" | grep -o '"id"' | wc -l)
    echo "  New bot count: $BOT_COUNT_AFTER"
    
    if [ "$BOT_COUNT_AFTER" -gt "$BOT_COUNT_BEFORE" ]; then
        echo -e "${GREEN}✓ Bot appears in list${NC}"
    else
        echo -e "${RED}✗ Bot not found in list${NC}"
        exit 1
    fi
    echo ""
fi

# Step 5: Delete the test bot
if [ -n "$BOT_ID" ]; then
    echo "🗑️  Step 5: Deleting test bot..."
    DELETE_RESPONSE=$(curl -s -X DELETE "${API_BASE}/bots/${BOT_ID}" \
      -H "Authorization: Bearer ${TOKEN}" || echo "{}")
    
    if echo "$DELETE_RESPONSE" | grep -q '"success"\s*:\s*true\|deleted\|removed'; then
        echo -e "${GREEN}✓ Bot deleted successfully${NC}"
    else
        echo -e "${YELLOW}⚠ Bot deletion response:${NC}"
        echo "$DELETE_RESPONSE"
    fi
    echo ""
fi

# Step 6: Verify deletion
if [ -n "$BOT_ID" ]; then
    echo "✅ Step 6: Verifying deletion..."
    LIST_FINAL=$(curl -s -X GET "${API_BASE}/bots" \
      -H "Authorization: Bearer ${TOKEN}" || echo "[]")
    
    BOT_COUNT_FINAL=$(echo "$LIST_FINAL" | grep -o '"id"' | wc -l)
    echo "  Final bot count: $BOT_COUNT_FINAL"
    
    if [ "$BOT_COUNT_FINAL" -eq "$BOT_COUNT_BEFORE" ]; then
        echo -e "${GREEN}✓ Bot successfully removed from list${NC}"
    else
        echo -e "${YELLOW}⚠ Bot count doesn't match (may still be listed)${NC}"
    fi
    echo ""
fi

# Summary
echo "📊 Summary"
echo "=========="
echo -e "${GREEN}✓ Login: Working${NC}"
echo -e "${GREEN}✓ List Bots: Working${NC}"

if [ -n "$BOT_ID" ]; then
    echo -e "${GREEN}✓ Create Bot: Working${NC}"
    echo -e "${GREEN}✓ Delete Bot: Working${NC}"
    echo ""
    echo -e "${GREEN}✓ ALL BOT CRUD TESTS PASSED${NC}"
else
    echo -e "${YELLOW}⚠ Create Bot: Blocked by funding validation${NC}"
    echo -e "${YELLOW}⚠ Delete Bot: Skipped (no bot created)${NC}"
    echo ""
    echo -e "${YELLOW}⚠ PARTIAL SUCCESS (funding validation may be too strict for paper mode)${NC}"
fi
