"""Health routes for ping endpoints.

This module provides basic health check endpoints for deployment verification.
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
import logging
import os
import database as db
from utils.env_utils import env_bool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/health", tags=["Health"])

# Module-level state for preflight checks (populated by server.py at startup)
_router_status = {"mounted": [], "failed": []}


def set_router_status(mounted: list, failed: list):
    """Called by server.py after router mounting completes."""
    _router_status["mounted"] = mounted
    _router_status["failed"] = failed


@router.get("/preflight")
async def preflight_check() -> dict:
    """
    Pre-deployment readiness check (no auth required).
    
    Returns comprehensive system readiness including:
    - Feature flags configuration
    - Router mounting status
    - Service connectivity (DB, CCXT)
    - Authentication configuration
    
    Returns:
        dict: ok=True if system is ready, ok=False if critical issues detected
    """
    try:
        # Collect feature flags
        flags = {
            "ENABLE_TRADING": env_bool("ENABLE_TRADING", False),
            "ENABLE_AUTOPILOT": env_bool("ENABLE_AUTOPILOT", False),
            "ENABLE_SCHEDULERS": env_bool("ENABLE_SCHEDULERS", False),
            "ENABLE_CCXT": env_bool("ENABLE_CCXT", True),
            "ENABLE_REALTIME": env_bool("ENABLE_REALTIME", True),
        }
        
        # Check router mounting status
        routers = {
            "mounted": _router_status["mounted"],
            "failed": _router_status["failed"],
        }
        
        # Check services
        services = {}
        
        # Database check (required)
        try:
            if db.client is not None:
                await db.client.admin.command('ping')
                services["db"] = "ok"
            else:
                services["db"] = "fail"
        except Exception as e:
            logger.error(f"Preflight DB check failed: {e}")
            services["db"] = "fail"
        
        # Redis check (optional - only if used)
        services["redis"] = "skipped"  # Not used in this deployment
        
        # CCXT check (only if enabled)
        if flags["ENABLE_CCXT"]:
            try:
                import ccxt
                # Simple sanity check - can we instantiate?
                services["ccxt"] = "ok"
            except Exception as e:
                logger.warning(f"Preflight CCXT check failed: {e}")
                services["ccxt"] = "fail"
        else:
            services["ccxt"] = "skipped"
        
        # Paper trading DB check (required for paper trading mode)
        try:
            # Check if paper trading engine can access DB collections
            if db.bots_collection is not None and db.trades_collection is not None:
                services["paper_trading_db"] = "ok"
            else:
                services["paper_trading_db"] = "error"
        except Exception as e:
            logger.warning(f"Preflight paper trading DB check failed: {e}")
            services["paper_trading_db"] = "error"
        
        # OpenAI key source check (for AI features)
        env_openai_key = os.getenv("OPENAI_API_KEY")
        if env_openai_key:
            services["openai_key_source"] = "env"
        else:
            services["openai_key_source"] = "none"
        
        # Note: Cannot check user-saved keys without authentication in preflight
        # User-saved keys would override env in actual usage
        
        # API keys count (global count - no user context in preflight)
        keys = {}
        try:
            if db.api_keys_collection is not None:
                total_count = await db.api_keys_collection.count_documents({})
                keys["saved_count_global"] = total_count
            else:
                keys["saved_count_global"] = 0
        except Exception as e:
            logger.warning(f"Preflight keys count check failed: {e}")
            keys["saved_count_global"] = 0
        
        # Auth configuration check
        jwt_secret = os.getenv("JWT_SECRET", "")
        auth = {
            "jwt_secret_present": bool(jwt_secret and jwt_secret != "your-secret-key-change-in-production-min-32-chars"),
            "algorithm": "HS256"
        }
        
        # Determine overall readiness
        ok = True
        issues = []
        
        # Critical: Any router failed to mount
        if routers["failed"]:
            ok = False
            issues.append(f"Router mount failures: {len(routers['failed'])}")
        
        # Critical: Database must be available
        if services["db"] != "ok":
            ok = False
            issues.append("Database not available")
        
        # Critical: JWT secret must be configured
        if not auth["jwt_secret_present"]:
            ok = False
            issues.append("JWT_SECRET not configured or using default")
        
        # Critical: Realtime router must be mounted if enabled
        if flags["ENABLE_REALTIME"]:
            realtime_mounted = any("realtime" in m.lower() for m in routers["mounted"])
            if not realtime_mounted:
                ok = False
                issues.append("ENABLE_REALTIME=true but realtime router not mounted")
        
        # Warning: CCXT should work if enabled
        if flags["ENABLE_CCXT"] and services["ccxt"] != "ok":
            # Not critical - just a warning
            logger.warning("ENABLE_CCXT=true but CCXT service check failed")
        
        response = {
            "ok": ok,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "flags": flags,
            "routers": routers,
            "services": services,
            "auth": auth,
            "keys": keys,
        }
        
        if not ok:
            response["issues"] = issues
        
        return response
        
    except Exception as e:
        logger.error(f"Preflight check error: {e}", exc_info=True)
        return {
            "ok": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
            "issues": ["Preflight check crashed - see logs"]
        }


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
