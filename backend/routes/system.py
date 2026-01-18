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
    - User-specific requirements (paper training, API keys, drawdown)
    
    Returns stable schema:
    {
        "live_allowed": false,
        "reasons": ["..."]
    }
    """
    try:
        live_allowed = True
        reasons = []
        
        # Check ENABLE_LIVE_TRADING feature flag
        enable_live = os.getenv('ENABLE_LIVE_TRADING', 'false').lower() == 'true'
        if not enable_live:
            live_allowed = False
            reasons.append("Live trading is disabled in system configuration (ENABLE_LIVE_TRADING=false)")
        
        # Check emergency stop status
        try:
            if db.emergency_stop_collection:
                emergency_status = await db.emergency_stop_collection.find_one({}) or {}
                emergency_enabled = emergency_status.get('enabled', False)
                if emergency_enabled:
                    live_allowed = False
                    reasons.append("Emergency stop is currently active")
        except Exception as e:
            logger.warning(f"Could not check emergency stop: {e}")
        
        # Check if user has completed paper training (minimum 7 days)
        try:
            # Get user's bots
            bots = await db.bots_collection.find({
                "user_id": user_id,
                "status": "active"
            }).to_list(100)
            
            paper_days = 0
            for bot in bots:
                created_at = bot.get('created_at')
                if created_at:
                    from datetime import datetime, timezone
                    created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    days_old = (datetime.now(timezone.utc) - created).days
                    paper_days = max(paper_days, days_old)
            
            if paper_days < 7:
                live_allowed = False
                reasons.append(f"Minimum 7 days paper trading required (current: {paper_days} days)")
        except Exception as e:
            logger.warning(f"Error checking paper training: {e}")
            live_allowed = False
            reasons.append("Unable to verify paper training status")
        
        # Check if user has API keys configured
        try:
            api_keys = await db.api_keys_collection.count_documents({"user_id": user_id})
            if api_keys == 0:
                live_allowed = False
                reasons.append("No exchange API keys configured")
        except Exception as e:
            logger.warning(f"Error checking API keys: {e}")
            live_allowed = False
            reasons.append("Unable to verify API keys")
        
        # Check for excessive drawdown (max 15% from initial capital)
        try:
            for bot in bots:
                initial = bot.get('initial_capital', 1000)
                current = bot.get('current_capital', 1000)
                if initial > 0:
                    drawdown = ((initial - current) / initial) * 100
                    if drawdown > 15:
                        live_allowed = False
                        reasons.append(f"Bot '{bot.get('name')}' has excessive drawdown ({drawdown:.1f}%)")
        except Exception as e:
            logger.warning(f"Error checking drawdown: {e}")
        
        # If all checks passed
        if live_allowed and not reasons:
            reasons = ["All requirements met for live trading"]
        
        return {
            "live_allowed": live_allowed,
            "reasons": reasons
        }
    except Exception as e:
        logger.error(f"Error checking live eligibility: {e}")
        # Return safe default: NOT eligible
        return {
            "live_allowed": False,
            "reasons": [f"Error checking eligibility: {str(e)}"]
        }


@router.get("/emergency-stop/status")
async def get_emergency_stop_status(user_id: str = Depends(get_current_user)) -> dict:
    """Get emergency stop status
    
    Protected endpoint that returns current emergency stop state with stable schema
    """
    try:
        # Get global emergency stop status
        emergency_status = await db.emergency_stop_collection.find_one({}) if db.emergency_stop_collection else {}
        
        # Always return stable schema with explicit fields required by verify_production_ready.py
        # Contract: success, enabled (was is_emergency_stop_active), reason, updated_at
        return {
            "success": True,
            "enabled": emergency_status.get('enabled', False) if emergency_status else False,
            "active": emergency_status.get('enabled', False) if emergency_status else False,  # alias for backward compat
            "reason": emergency_status.get('reason') if emergency_status else None,
            "updated_at": emergency_status.get('activated_at') if emergency_status else None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting emergency stop status: {e}")
        # Return safe default schema even on error
        return {
            "success": True,
            "enabled": False,
            "active": False,
            "reason": None,
            "updated_at": None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }