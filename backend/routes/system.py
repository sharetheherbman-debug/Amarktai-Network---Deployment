"""System routes for basic ping and status endpoints.

This module defines a minimal router that exposes system‑wide ping endpoints.  Having a
dedicated file ensures that the server can mount `/api/system/ping` without
conflicting with other route prefixes and satisfies health checks used by
deployment scripts.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from datetime import datetime, timezone
from typing import Dict
import config
import logging
import os

from auth import get_current_user
import database as db

logger = logging.getLogger(__name__)

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
    NOW RETURNS ALL 5 PLATFORMS: Luno, Binance, KuCoin, OVEX, VALR
    """
    try:
        # Import canonical platform registry
        from config.platforms import get_all_platforms, SUPPORTED_PLATFORMS
        
        # Get all platform configs from canonical source
        platform_configs = get_all_platforms()
        
        platforms = []
        for platform_config in platform_configs:
            platforms.append({
                "id": platform_config["id"],
                "name": platform_config["name"],
                "display_name": platform_config["display_name"],
                "enabled": platform_config["enabled"],
                "bot_limit": platform_config["max_bots"],
                "supports_paper": platform_config["supports_paper"],
                "supports_live": platform_config["supports_live"],
                "icon": platform_config.get("icon", ""),
                "color": platform_config.get("color", ""),
                "region": platform_config.get("region", "")
            })
        
        return {
            "platforms": platforms,
            "total_count": len(platforms),
            "default": "all",  # Default filter value
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        # Never crash - return safe defaults with ALL 5 platforms
        logger.error(f"Error in get_platforms: {e}")
        return {
            "platforms": [
                {"id": "luno", "name": "Luno", "display_name": "Luno", "enabled": True, "bot_limit": 5, "supports_paper": True, "supports_live": True},
                {"id": "binance", "name": "Binance", "display_name": "Binance", "enabled": True, "bot_limit": 10, "supports_paper": True, "supports_live": True},
                {"id": "kucoin", "name": "KuCoin", "display_name": "KuCoin", "enabled": True, "bot_limit": 10, "supports_paper": True, "supports_live": True},
                {"id": "ovex", "name": "OVEX", "display_name": "OVEX", "enabled": True, "bot_limit": 10, "supports_paper": True, "supports_live": False},
                {"id": "valr", "name": "VALR", "display_name": "VALR", "enabled": True, "bot_limit": 10, "supports_paper": True, "supports_live": False}
            ],
            "total_count": 5,
            "default": "all",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# REMOVED: Duplicate of live_trading_gate.py endpoint GET /api/system/live-eligibility
# Use live_trading_gate.py instead


# REMOVED: Duplicate of emergency_stop_endpoints.py endpoint GET /api/system/emergency-stop/status  
# Use emergency_stop_endpoints.py instead


@router.get("/status")
async def system_status(user_id: str = Depends(get_current_user)) -> dict:
    """Get comprehensive system status for the authenticated user
    
    Returns:
        - Database connection status
        - WebSocket status
        - SSE status
        - API operational status
        - Bot counts for user
    """
    try:
        # Check database connection
        db_status = "connected"
        try:
            await db.users_collection.find_one({"id": user_id})
        except Exception as db_error:
            logger.error(f"Database check failed: {db_error}")
            db_status = "error"
        
        # Get bot counts for user
        bots_active = 0
        bots_total = 0
        try:
            bots_total = await db.bots_collection.count_documents({"user_id": user_id})
            bots_active = await db.bots_collection.count_documents(
                {"user_id": user_id, "status": "active"}
            )
        except Exception as bot_error:
            logger.error(f"Bot count check failed: {bot_error}")
        
        return {
            "success": True,
            "status": {
                "database": db_status,
                "websocket": "active",  # Always active if server is running
                "sse": "active",  # Always active if server is running
                "api": "operational",
                "bots_active": bots_active,
                "bots_total": bots_total
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    except Exception as e:
        logger.error(f"System status error: {e}")
        # Return partial status even on error
        return {
            "success": False,
            "status": {
                "database": "unknown",
                "websocket": "unknown",
                "sse": "unknown",
                "api": "operational",
                "bots_active": 0,
                "bots_total": 0
            },
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.get("/mode")
async def get_system_mode(user_id: str = Depends(get_current_user)) -> dict:
    """Get current system mode for authenticated user
    
    Returns user's current trading mode (testing, live_trading, autopilot)
    """
    try:
        # Get user's system mode from database
        user = await db.users_collection.find_one({"id": user_id}, {"_id": 0, "system_mode": 1})
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        system_mode = user.get("system_mode", "testing")
        
        # Map mode to boolean flags
        mode_flags = {
            "testing": {"paper_trading": True, "live_trading": False, "autopilot": False},
            "live_trading": {"paper_trading": False, "live_trading": True, "autopilot": False},
            "autopilot": {"paper_trading": False, "live_trading": True, "autopilot": True}
        }
        
        flags = mode_flags.get(system_mode, mode_flags["testing"])
        
        return {
            "success": True,
            "mode": system_mode,
            **flags,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get system mode error: {e}")
        # Return safe default
        return {
            "success": False,
            "mode": "testing",
            "paper_trading": True,
            "live_trading": False,
            "autopilot": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.post("/mode")
async def set_system_mode(
    payload: Dict = Body(...),
    user_id: str = Depends(get_current_user)
) -> dict:
    """Set system mode for authenticated user
    
    Body:
        {"mode": "testing" | "live_trading" | "autopilot"}
    """
    try:
        new_mode = payload.get("mode")
        
        if new_mode not in ["testing", "live_trading", "autopilot"]:
            raise HTTPException(
                status_code=400, 
                detail="Invalid mode. Must be: testing, live_trading, or autopilot"
            )
        
        # Update user's system mode
        result = await db.users_collection.update_one(
            {"id": user_id},
            {"$set": {"system_mode": new_mode}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        logger.info(f"User {user_id[:8]} changed system mode to: {new_mode}")
        
        return {
            "success": True,
            "mode": new_mode,
            "message": f"System mode changed to {new_mode}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Set system mode error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set system mode: {str(e)}")