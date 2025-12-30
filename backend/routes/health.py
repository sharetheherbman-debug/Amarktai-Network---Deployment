"""Health routes for ping endpoints.

This module provides basic health check endpoints for deployment verification.
"""

from fastapi import APIRouter
from datetime import datetime, timezone
import logging
import database as db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/health", tags=["Health"])


@router.get("/ping")
async def health_ping() -> dict:
    """Return a simple heartbeat response for health checks with database connectivity."""
    try:
        # Test database connection
        if db.client is not None:
            await db.client.admin.command('ping')
            db_status = "connected"
            status_code = "healthy"
        else:
            db_status = "disconnected"
            status_code = "unhealthy"
    except Exception as e:
        logger.error(f"Health check database ping failed: {e}")
        db_status = "error"
        status_code = "unhealthy"
    
    return {
        "status": status_code,
        "db": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
