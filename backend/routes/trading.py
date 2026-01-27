from fastapi import HTTPException, Depends, APIRouter
from datetime import datetime, timezone, timedelta
from typing import Optional, List
import logging

from models import User, UserLogin, Bot, BotCreate, APIKey, APIKeyCreate, Trade, SystemMode, Alert, ChatMessage, BotRiskMode
import database as db
from auth import create_access_token, get_current_user, get_password_hash, verify_password

logger = logging.getLogger(__name__)
router = APIRouter()
from ccxt_service import ccxt_service


@router.get("/overview")
async def get_overview(user_id: str = Depends(get_current_user)):
    """Get dashboard overview - FIXED with accurate counts + mode display"""
    try:
        bots = await db.bots_collection.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
        
        # Accurate counts
        active_bots = [b for b in bots if b.get('status') == 'active']
        total_bots = len(bots)
        active_count = len(active_bots)
        
        # Count by mode
        paper_bots = len([b for b in active_bots if b.get('trading_mode') == 'paper'])
        live_bots = len([b for b in active_bots if b.get('trading_mode') == 'live'])
        
        # Calculate total profit from active bots
        total_profit = sum(bot.get('total_profit', 0) for bot in active_bots)
        
        # Calculate exposure
        total_capital = sum(bot.get('current_capital', 0) for bot in active_bots)
        exposure = (total_capital / (total_capital + 1000)) * 100 if total_capital > 0 else 0
        
        # Get system modes
        modes = await db.system_modes_collection.find_one({"user_id": user_id}, {"_id": 0})
        
        # Determine display text
        if live_bots > 0:
            bot_display = f"{active_count} active / {total_bots} ({live_bots} live, {paper_bots} paper)"
        else:
            bot_display = f"{active_count} active / {total_bots} (paper)"
        
        trading_status = "Live Trading" if modes and modes.get('liveTrading') else "Paper Trading" if modes and modes.get('paperTrading') else "Inactive"
        
        return {
            "totalProfit": round(total_profit, 2),
            "total_profit": round(total_profit, 2),
            "activeBots": bot_display,
            "active_bots": active_count,
            "total_bots": total_bots,
            "paper_bots": paper_bots,
            "live_bots": live_bots,
            "exposure": round(exposure, 2),
            "riskLevel": "Low" if exposure < 50 else "Medium" if exposure < 75 else "High",
            "risk_level": "Low" if exposure < 50 else "Medium" if exposure < 75 else "High",
            "aiSentiment": "Bullish",
            "ai_sentiment": "Bullish",
            "lastUpdate": datetime.now(timezone.utc).isoformat(),
            "last_update": datetime.now(timezone.utc).isoformat(),
            "tradingStatus": trading_status
        }
    except Exception as e:
        logger.error(f"Overview error: {e}")
        return {
            "totalProfit": 0.00,
            "total_profit": 0.00,
            "activeBots": "0 / 0",
            "active_bots": 0,
            "total_bots": 0,
            "exposure": 0.00,
            "riskLevel": "Unknown",
            "risk_level": "Unknown",
            "aiSentiment": "Neutral",
            "ai_sentiment": "Neutral",
            "lastUpdate": datetime.now(timezone.utc).isoformat(),
            "last_update": datetime.now(timezone.utc).isoformat(),
            "tradingStatus": "Unknown"
        }


# NOTE: Removed duplicate endpoints to fix route collisions
# - GET /metrics (canonical: server.py @api_router.get("/metrics"))
# - GET /trades/recent (canonical: routes/trades.py)
# - GET /system/mode (canonical: server.py @api_router.get("/system/mode"))


@router.post("/system/mode/toggle")
async def toggle_system_mode(data: dict, user_id: str = Depends(get_current_user)):
    """Toggle system modes with mutual exclusion enforcement
    
    Enforces: paper vs live are mutually exclusive
    - When paperTrading is enabled, liveTrading is disabled
    - When liveTrading is enabled, paperTrading is disabled
    
    Args:
        data: {mode: "paperTrading"|"liveTrading"|"autopilot", enabled: bool}
        user_id: Current user ID from auth
        
    Returns:
        Updated modes with mutual exclusion applied
    """
    try:
        mode = data.get('mode')
        enabled = data.get('enabled', False)
        
        if mode not in ['paperTrading', 'liveTrading', 'autopilot', 'emergencyStop']:
            raise HTTPException(status_code=400, detail=f"Invalid mode: {mode}")
        
        # Get current modes
        modes = await db.system_modes_collection.find_one({"user_id": user_id}, {"_id": 0})
        if not modes:
            modes = {
                "user_id": user_id,
                "paperTrading": False,
                "liveTrading": False,
                "autopilot": False,
                "emergencyStop": False
            }
        
        # Apply mutual exclusion for paper vs live
        update_fields = {
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        if mode == 'paperTrading':
            update_fields['paperTrading'] = enabled
            if enabled:
                # Enabling paper disables live
                update_fields['liveTrading'] = False
        elif mode == 'liveTrading':
            update_fields['liveTrading'] = enabled
            if enabled:
                # Enabling live disables paper
                update_fields['paperTrading'] = False
        elif mode == 'autopilot':
            update_fields['autopilot'] = enabled
        elif mode == 'emergencyStop':
            update_fields['emergencyStop'] = enabled
        
        # Update database
        await db.system_modes_collection.update_one(
            {"user_id": user_id},
            {"$set": update_fields},
            upsert=True
        )
        
        # Get updated modes
        updated_modes = await db.system_modes_collection.find_one({"user_id": user_id}, {"_id": 0})
        
        # Emit realtime event
        from realtime_events import rt_events
        await rt_events.system_mode_changed(user_id, mode, enabled)
        
        logger.info(f"Mode toggled for user {user_id[:8]}: {mode}={enabled}")
        
        return {
            "success": True,
            "message": f"{mode} {'enabled' if enabled else 'disabled'}",
            "modes": updated_modes,
            "mutual_exclusion_applied": (mode in ['paperTrading', 'liveTrading'] and enabled)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Toggle mode error: {e}")
        raise HTTPException(status_code=500, detail=str(e))



