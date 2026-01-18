"""System routes for basic ping and status endpoints.

This module defines a minimal router that exposes system‑wide ping endpoints.  Having a
dedicated file ensures that the server can mount `/api/system/ping` without
conflicting with other route prefixes and satisfies health checks used by
deployment scripts.
"""

from fastapi import APIRouter, Depends
from datetime import datetime, timezone
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
    Restricted to Luno, Binance, and KuCoin only as per requirements.
    """
    try:
        # Supported exchanges only: Luno, Binance, KuCoin
        supported_platforms = ["luno", "binance", "kucoin"]
        
        # Get platform config from backend config with safe fallback
        try:
            exchange_limits = config.EXCHANGE_BOT_LIMITS
        except:
            # Fallback to safe defaults if config not available
            exchange_limits = {
                'luno': 5,
                'binance': 10,
                'kucoin': 10
            }
        
        platforms = []
        for platform_name in supported_platforms:
            bot_limit = exchange_limits.get(platform_name, 10)  # Default to 10 if not in config
            platforms.append({
                "id": platform_name,
                "name": platform_name.title(),
                "display_name": platform_name.title(),
                "enabled": True,
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
    except Exception as e:
        # Never crash - return safe defaults
        logger.error(f"Error in get_platforms: {e}")
        return {
            "platforms": [
                {"id": "luno", "name": "Luno", "enabled": True, "bot_limit": 5},
                {"id": "binance", "name": "Binance", "enabled": True, "bot_limit": 10},
                {"id": "kucoin", "name": "KuCoin", "enabled": True, "bot_limit": 10}
            ],
            "total_count": 3,
            "default": "all",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.get("/live-eligibility")
async def get_live_eligibility(user_id: str = Depends(get_current_user)) -> dict:
    """Check if user is eligible for live trading
    
    Protected endpoint that returns eligibility status based on:
    - ENABLE_LIVE_TRADING feature flag
    - Emergency stop status
    - User-specific requirements
    """
    try:
        eligible = False
        reasons = []
        flags = {}
        
        # Check ENABLE_LIVE_TRADING feature flag
        enable_live = os.getenv('ENABLE_LIVE_TRADING', 'false').lower() == 'true'
        flags['enable_live_trading'] = enable_live
        if not enable_live:
            reasons.append("ENABLE_LIVE_TRADING is disabled in system configuration")
        
        # Check emergency stop status
        try:
            emergency_status = await db.emergency_stop_collection.find_one({}) or {}
            emergency_enabled = emergency_status.get('enabled', False)
            flags['emergency_stop'] = emergency_enabled
            if emergency_enabled:
                reasons.append("Emergency stop is currently active")
        except:
            flags['emergency_stop'] = False
        
        # Check if user has completed paper training
        try:
            # Get user's bots that have completed paper training
            bots = await db.bots_collection.find({
                "user_id": user_id,
                "status": "active"
            }).to_list(100)
            
            paper_trained_bots = [b for b in bots if b.get('paper_training_complete', False)]
            flags['paper_trained_bots'] = len(paper_trained_bots)
            
            if len(paper_trained_bots) == 0:
                reasons.append("No bots have completed paper training requirements")
        except Exception as e:
            logger.warning(f"Error checking paper training status: {e}")
            flags['paper_trained_bots'] = 0
            reasons.append("Unable to verify paper training status")
        
        # Check if user has API keys configured
        try:
            api_keys = await db.api_keys_collection.count_documents({"user_id": user_id})
            flags['api_keys_configured'] = api_keys > 0
            if api_keys == 0:
                reasons.append("No exchange API keys configured")
        except:
            flags['api_keys_configured'] = False
            reasons.append("Unable to verify API keys")
        
        # User is eligible only if all checks pass
        if enable_live and not flags.get('emergency_stop', False) and flags.get('paper_trained_bots', 0) > 0 and flags.get('api_keys_configured', False):
            eligible = True
            reasons = ["All requirements met for live trading"]
        
        return {
            "eligible": eligible,
            "reasons": reasons,
            "flags": flags,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error checking live eligibility: {e}")
        return {
            "eligible": False,
            "reasons": [f"Error checking eligibility: {str(e)}"],
            "flags": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.get("/emergency-stop/status")
async def get_emergency_stop_status(user_id: str = Depends(get_current_user)) -> dict:
    """Get emergency stop status
    
    Protected endpoint that returns current emergency stop state
    """
    try:
        # Get global emergency stop status
        emergency_status = await db.emergency_stop_collection.find_one({}) or {}
        enabled = emergency_status.get('enabled', False)
        
        return {
            "enabled": enabled,
            "reason": emergency_status.get('reason', ''),
            "activated_at": emergency_status.get('activated_at', None),
            "activated_by": emergency_status.get('activated_by', None),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting emergency stop status: {e}")
        return {
            "enabled": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }