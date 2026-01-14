"""System routes for basic ping and status endpoints.

This module defines a minimal router that exposes system‑wide ping endpoints.  Having a
dedicated file ensures that the server can mount `/api/system/ping` without
conflicting with other route prefixes and satisfies health checks used by
deployment scripts.
"""

from fastapi import APIRouter
from datetime import datetime, timezone
import config

# Prefix ensures final paths begin with /api/system when mounted without an
# additional prefix.
router = APIRouter(prefix="/api/system", tags=["System"])


@router.get("/ping")
async def system_ping() -> dict:
    """Return a simple heartbeat response for system health checks."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/platforms")
async def get_platforms() -> dict:
    """Return list of all enabled trading platforms/exchanges.
    
    Returns platform names, enabled status, and bot limits.
    Frontend should use this to populate platform selectors.
    """
    # Get platform config from backend config
    exchange_limits = config.EXCHANGE_BOT_LIMITS
    
    platforms = []
    for platform_name, bot_limit in exchange_limits.items():
        platforms.append({
            "name": platform_name,
            "display_name": platform_name.title(),
            "enabled": True,  # All platforms in config are enabled
            "bot_limit": bot_limit,
            "supports_paper": True,
            "supports_live": True
        })
    
    return {
        "platforms": platforms,
        "total_count": len(platforms),
        "default": "all",  # Default filter value
        "timestamp": datetime.now(timezone.utc).isoformat()
    }