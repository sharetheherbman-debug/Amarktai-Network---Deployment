#!/bin/bash
# Verify OpenAPI Endpoint
# Validates that /api/openapi.json exists and returns valid schema

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

echo "Verifying OpenAPI endpoint at $BASE_URL/api/openapi.json"

# Check if backend is running
if ! curl -s -f "$BASE_URL/api/health/ping" > /dev/null 2>&1; then
    echo "❌ Backend is not running at $BASE_URL"
    echo "Start backend first: cd backend && python server.py"
    exit 1
fi

echo "✓ Backend is running"

# Check OpenAPI endpoint
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/openapi.json")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" != "200" ]; then
    echo "❌ OpenAPI endpoint returned HTTP $http_code (expected 200)"
    exit 1
fi

echo "✓ OpenAPI endpoint returns HTTP 200"

# Validate JSON structure
if echo "$body" | jq -e '.openapi' > /dev/null 2>&1 || \
   echo "$body" | jq -e '.swagger' > /dev/null 2>&1 || \
   echo "$body" | jq -e '.paths' > /dev/null 2>&1; then
    echo "✓ OpenAPI JSON has valid structure"
    
    # Count endpoints
    if command -v jq &> /dev/null; then
        path_count=$(echo "$body" | jq '.paths | length')
        echo "✓ Found $path_count API endpoints"
    fi
    
    echo ""
    echo "✅ OpenAPI validation passed"
    exit 0
else
    echo "❌ OpenAPI JSON structure is invalid"
    echo "Response: $body" | head -c 200
    exit 1
fi
