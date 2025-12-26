"""Health routes for ping endpoints.

This module provides basic health check endpoints for deployment verification.
"""

from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter(prefix="/api/health", tags=["Health"])


@router.get("/ping")
async def health_ping() -> dict:
    """Return a simple heartbeat response for health checks."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
