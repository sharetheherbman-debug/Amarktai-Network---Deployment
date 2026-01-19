"""
System Status Endpoint
Reports feature flags, scheduler status, and trading activity
"""

from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
import logging
import os

from auth import get_current_user
from utils.env_utils import env_bool
import database as db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system", tags=["System Status"])


@router.get("/status")
async def get_system_status(user_id: str = Depends(get_current_user)):
    """
    Get system status including:
    - Feature flags (trading, schedulers, autopilot)
    - Scheduler running status
    - Last trade time
    - Last tick time
    - Database health
    """
    try:
        # Get feature flags using consistent parsing
        feature_flags = {
            "enable_trading": env_bool('ENABLE_TRADING', False),
            "enable_schedulers": env_bool('ENABLE_SCHEDULERS', False),
            "enable_autopilot": env_bool('ENABLE_AUTOPILOT', False),
            "enable_ccxt": env_bool('ENABLE_CCXT', True)
        }
        
        # Check scheduler status
        scheduler_status = {}
        try:
            from trading_scheduler import trading_scheduler
            scheduler_status["trading_scheduler"] = {
                "running": trading_scheduler.is_running() if hasattr(trading_scheduler, 'is_running') else "unknown",
                "enabled": feature_flags["enable_trading"]
            }
        except Exception as e:
            logger.warning(f"Could not check trading_scheduler status: {e}")
            scheduler_status["trading_scheduler"] = {"running": "unknown", "error": str(e)}
        
        # Get last trade time for user
        last_trade = None
        last_trade_time = None
        try:
            last_trade = await db.trades_collection.find_one(
                {"user_id": user_id},
                {"_id": 0, "timestamp": 1, "symbol": 1, "side": 1, "profit_loss": 1},
                sort=[("timestamp", -1)]
            )
            if last_trade:
                last_trade_time = last_trade.get("timestamp")
        except Exception as e:
            logger.error(f"Error fetching last trade: {e}")
        
        # Get system health
        db_health = await db.health_check()
        
        # Get active bots count
        active_bots_count = 0
        try:
            active_bots_count = await db.bots_collection.count_documents({
                "user_id": user_id,
                "status": "active"
            })
        except Exception as e:
            logger.error(f"Error counting active bots: {e}")
        
        # Get system modes
        system_modes = {}
        try:
            modes = await db.system_modes_collection.find_one(
                {"user_id": user_id},
                {"_id": 0}
            )
            if modes:
                system_modes = {
                    "paper_trading": modes.get("paperTrading", False),
                    "live_trading": modes.get("liveTrading", False),
                    "autonomous": modes.get("autonomous", False)
                }
        except Exception as e:
            logger.error(f"Error fetching system modes: {e}")
        
        return {
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "feature_flags": feature_flags,
            "scheduler_status": scheduler_status,
            "database": {
                "connected": db_health.get("status") == "connected",
                "database_name": db_health.get("database")
            },
            "trading_activity": {
                "active_bots": active_bots_count,
                "last_trade": last_trade,
                "last_trade_time": last_trade_time
            },
            "system_modes": system_modes
        }
        
    except Exception as e:
        logger.error(f"System status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint (no auth required)
    Returns 200 if system is operational
    """
    try:
        # Check database connection
        db_health = await db.health_check()
        
        if db_health.get("status") != "connected":
            raise HTTPException(status_code=503, detail="Database not connected")
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": "connected"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")
