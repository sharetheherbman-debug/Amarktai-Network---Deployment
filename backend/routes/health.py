"""Health routes for ping endpoints.

This module provides basic health check endpoints for deployment verification.
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
import logging
import database as db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/health", tags=["Health"])


@router.get("/ping")
async def health_ping() -> dict:
    """Return a simple heartbeat response for health checks with database connectivity.
    
    Returns:
        - HTTP 200 with status="healthy" when database is connected
        - HTTP 503 with status="unhealthy" when database is disconnected or error occurs
    """
    try:
        # Test database connection
        if db.client is not None:
            await db.client.admin.command('ping')
            # Database is reachable - return 200
            return {
                "status": "healthy",
                "db": "connected",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        else:
            # Database client not initialized - return 503
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "unhealthy",
                    "db": "disconnected",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
    except HTTPException:
        raise  # Re-raise HTTPException as-is
    except Exception as e:
        # Database connection error - return 503
        logger.error(f"Health check database ping failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "db": "error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }
        )
