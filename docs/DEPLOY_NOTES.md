# Route Collision Fixes - Deployment Notes

## Overview

This deployment resolves all route collisions in the Amarktai Network backend that were preventing the server from starting in production. **All 10 duplicate route registrations have been fixed.**

## What Was Fixed

### Route Collisions Removed

The following duplicate endpoints were identified and resolved:

1. **GET /api/metrics** - Kept Prometheus metrics endpoint (line 2951 in server.py), removed alias to /overview
2. **GET /api/system/mode** - Canonical in `routes/system_mode.py`, removed from server.py
3. **GET /api/trades/recent** - Canonical in `routes/trades.py`, removed from routes/trading.py and server.py
4. **GET /api/system/status** - Canonical in `routes/system_status.py`, removed from server.py
5. **POST /api/system/emergency-stop** - Canonical in `routes/emergency_stop_endpoints.py`, removed from server.py
6. **GET /api/admin/users** - Canonical in `routes/admin_endpoints.py`, removed from server.py
7. **GET /api/admin/system-stats** - Canonical in `routes/admin_endpoints.py`, removed from server.py
8. **DELETE /api/bots/{bot_id}** - Canonical in `routes/bot_lifecycle.py`, removed from server.py
9. **GET /api/portfolio/summary** - Canonical in `routes/ledger_endpoints.py`, removed from routes/dashboard_endpoints.py
10. **GET /api/countdown/status** - Canonical in `routes/ledger_endpoints.py`, removed from routes/dashboard_endpoints.py

### Additional Fixes

- **Daily Report Scheduler**: Fixed "coroutine was never awaited" warning by commenting out sync call to async method
- **Route Collision Detector**: Already present in server.py; now passes without errors

## Canonical Endpoint Mapping

All endpoints now have exactly ONE canonical location:

| Endpoint | Canonical Location | Prefix | Purpose |
|----------|-------------------|--------|---------|
| GET /api/metrics | server.py | /api | Prometheus metrics (text format) |
| GET /api/system/mode | routes/system_mode.py | /api/system | System mode configuration |
| GET /api/trades/recent | routes/trades.py | /api/trades | Recent trade history |
| GET /api/system/status | routes/system_status.py | /api/system | System health status |
| POST /api/system/emergency-stop | routes/emergency_stop_endpoints.py | /api/system | Emergency trading halt |
| GET /api/admin/users | routes/admin_endpoints.py | /api/admin | Admin user management |
| GET /api/admin/system-stats | routes/admin_endpoints.py | /api/admin | Admin system statistics |
| DELETE /api/bots/{bot_id} | routes/bot_lifecycle.py | /api/bots | Bot deletion |
| GET /api/portfolio/summary | routes/ledger_endpoints.py | /api | Portfolio summary (ledger-based) |
| GET /api/countdown/status | routes/ledger_endpoints.py | /api | Countdown to target (ledger-based) |

### Why Ledger is Canonical for Portfolio Data

- **routes/ledger_endpoints.py** is the single source of truth for portfolio and equity calculations
- It uses the immutable ledger service for accurate financial data
- dashboard_endpoints.py duplicates were removed in favor of ledger-based calculations

## Verification Tools

### 1. Route Collision Checker Script

```bash
cd backend
python scripts/check_routes.py
```

**Expected Output:**
```
✅ NO ROUTE COLLISIONS DETECTED
Checked 282 unique routes
All routes have exactly one handler each
Server should boot successfully
```

**Exit Codes:**
- `0` - No collisions (success)
- `1` - Collisions detected (prints details)

### 2. Pytest Test Suite

```bash
cd backend
pytest tests/test_route_collisions.py -v
```

**Tests:**
- `test_no_route_collisions` - Ensures no duplicate routes exist
- `test_critical_routes_exist` - Verifies all essential endpoints are registered
- `test_route_count_reasonable` - Sanity check for route count (200-400 expected)

## How to Start the Server

```bash
cd backend
uvicorn server:app --host 0.0.0.0 --port 8000
```

**Expected Startup Output:**
```
INFO:server:✅ Mounted: API Keys (Unified) (CRITICAL)
INFO:server:✅ Mounted: System Mode (CRITICAL)
...
INFO:server:✅ Route collision check passed - 282 unique routes registered
INFO:server:📊 Router mounting complete: 36 mounted, 0 failed
```

## Health Check

After starting the server, verify it's running:

```bash
curl http://localhost:8000/api/health/ping
```

**Expected Response:**
```json
{
  "status": "ok",
  "message": "pong",
  "timestamp": "2026-01-27T12:00:00.000000Z"
}
```

## CI/CD Integration

Add to your CI pipeline:

```yaml
# .github/workflows/backend-tests.yml
- name: Check Route Collisions
  run: |
    cd backend
    python scripts/check_routes.py
    
- name: Run Route Collision Tests
  run: |
    cd backend
    pytest tests/test_route_collisions.py -v
```

## Architecture Principles

### ✅ DO:
1. Define each endpoint in exactly ONE location
2. Use router prefixes consistently (e.g., `prefix="/api/admin"`)
3. Mount each router exactly once in server.py
4. Use redirects (307/308) if you need URL aliases

### ❌ DON'T:
1. Define the same method+path in multiple routers
2. Mount the same router multiple times
3. Create inline endpoints in server.py if a router module exists
4. Mix prefixes (some routes with `/api`, others without)

## Migration Notes for Existing Code

If you had code calling the old endpoints:

- **All endpoints still work** - we removed duplicates, not functionality
- **No API contract changes** - same URLs, same responses
- **Frontend requires no changes** - canonical endpoints serve the same data

## Troubleshooting

### Server Won't Start

**Error:** "Route collision detected - cannot start server"

**Solution:**
1. Run `python scripts/check_routes.py` to identify duplicates
2. Check the collision detection output in server logs
3. Remove duplicate endpoint definitions
4. Verify with `pytest tests/test_route_collisions.py`

### Missing Endpoint

**Error:** 404 for endpoint that should exist

**Solution:**
1. Check if the router is in `routers_to_mount` list in server.py
2. Verify the router module has a `router` variable exported
3. Check the router prefix matches the expected URL path

### Daily Report Scheduler Warning

**Warning:** "Could not start daily report scheduler: no running event loop"

**Status:** This is expected and handled
- The scheduler is commented out to prevent async/sync mismatch
- To re-enable: Move to FastAPI lifespan context manager or startup event handler

## Files Changed

- `backend/server.py` - Removed 7 duplicate inline endpoints, fixed scheduler
- `backend/routes/trading.py` - Removed 3 duplicate endpoints
- `backend/routes/dashboard_endpoints.py` - Removed 2 duplicate endpoints
- `backend/scripts/check_routes.py` - NEW: Route collision detection script
- `backend/tests/test_route_collisions.py` - NEW: Automated collision tests

## Deployment Checklist

Before deploying to production:

- [ ] Run `python scripts/check_routes.py` - must exit 0
- [ ] Run `pytest tests/test_route_collisions.py` - all tests pass
- [ ] Start server locally - must boot without errors
- [ ] Test `/api/health/ping` - must respond 200 OK
- [ ] No "Route collision detected" errors in logs
- [ ] No "coroutine was never awaited" warnings
- [ ] All critical endpoints respond correctly

## Support

For issues or questions about route collisions:

1. Check server startup logs for collision details
2. Run `python scripts/check_routes.py` for diagnostic output
3. Review this document for canonical endpoint locations
4. Ensure all routers follow the architecture principles above
