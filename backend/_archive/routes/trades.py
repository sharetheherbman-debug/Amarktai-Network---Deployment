"""Trades routes for simple health checks.

Although the full trade management lives in other modules, this lightweight
router exposes a `/api/trades/ping` endpoint.  Deployment scripts use
this to verify that the trades subsystem is reachable without pulling in
heavy dependencies.
"""

from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter(prefix="/api/trades", tags=["Trades"])


@router.get("/ping")
async def trades_ping() -> dict:
    """Return a simple heartbeat response for trades checks."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }