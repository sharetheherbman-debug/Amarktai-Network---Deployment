"""
Bot Lifecycle Management Router
Handles pause, resume, cooldown periods, and bot lifecycle operations
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict
import logging

from auth import get_current_user
from database import bots_collection, trades_collection
from websocket_manager import manager
from realtime_events import rt_events

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bots", tags=["Bot Lifecycle"])


@router.post("/{bot_id}/start")
async def start_bot(bot_id: str, user_id: str = Depends(get_current_user)):
    """Start a bot's trading activity
    
    Args:
        bot_id: Bot ID to start
        user_id: Current user ID (from auth)
        
    Returns:
        Updated bot status
    """
    try:
        # Verify bot belongs to user
        bot = await bots_collection.find_one({"id": bot_id, "user_id": user_id}, {"_id": 0})
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        # Check if already active
        if bot.get('status') == 'active':
            return {
                "success": False,
                "message": f"Bot '{bot['name']}' is already active",
                "bot": bot
            }
        
        # Start the bot
        started_at = datetime.now(timezone.utc).isoformat()
        
        await bots_collection.update_one(
            {"id": bot_id},
            {
                "$set": {
                    "status": "active",
                    "started_at": started_at
                },
                "$unset": {
                    "stopped_at": "",
                    "paused_at": "",
                    "pause_reason": "",
                    "paused_by_user": "",
                    "paused_by_system": "",
                    "stop_reason": ""
                }
            }
        )
        
        # Get updated bot
        updated_bot = await bots_collection.find_one({"id": bot_id}, {"_id": 0})
        
        # Send real-time notification
        await rt_events.bot_resumed(user_id, updated_bot)
        
        logger.info(f"✅ Bot {bot['name']} started by user {user_id[:8]}")
        
        return {
            "success": True,
            "message": f"Bot '{bot['name']}' started successfully",
            "bot": updated_bot
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Start bot error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{bot_id}/stop")
async def stop_bot(bot_id: str, data: Optional[Dict] = None, user_id: str = Depends(get_current_user)):
    """Stop a bot's trading activity permanently
    
    Args:
        bot_id: Bot ID to stop
        data: Optional data with reason for stop
        user_id: Current user ID (from auth)
        
    Returns:
        Updated bot status
    """
    try:
        # Verify bot belongs to user
        bot = await bots_collection.find_one({"id": bot_id, "user_id": user_id}, {"_id": 0})
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        # Check if already stopped
        if bot.get('status') == 'stopped':
            return {
                "success": False,
                "message": f"Bot '{bot['name']}' is already stopped",
                "bot": bot
            }
        
        # Stop the bot
        if data is None:
            data = {}
        reason = data.get('reason', 'Manual stop by user')
        stopped_at = datetime.now(timezone.utc).isoformat()
        
        await bots_collection.update_one(
            {"id": bot_id},
            {
                "$set": {
                    "status": "stopped",
                    "stopped_at": stopped_at,
                    "stop_reason": reason
                }
            }
        )
        
        # Get updated bot
        updated_bot = await bots_collection.find_one({"id": bot_id}, {"_id": 0})
        
        # Send real-time notification
        await manager.send_message(user_id, {
            "type": "bot_stopped",
            "bot": updated_bot,
            "message": f"⏹️ Bot '{bot['name']}' stopped"
        })
        
        logger.info(f"✅ Bot {bot['name']} stopped by user {user_id[:8]}")
        
        return {
            "success": True,
            "message": f"Bot '{bot['name']}' stopped successfully",
            "bot": updated_bot
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Stop bot error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{bot_id}/pause")
@router.put("/{bot_id}/pause")
async def pause_bot(bot_id: str, data: Optional[Dict] = None, user_id: str = Depends(get_current_user)):
    """Pause a bot's trading activity
    
    Accepts both POST and PUT methods for compatibility with frontend
    
    Args:
        bot_id: Bot ID to pause
        data: Optional data with reason for pause
        user_id: Current user ID (from auth)
        
    Returns:
        Updated bot status
    """
    try:
        # Verify bot belongs to user
        bot = await bots_collection.find_one({"id": bot_id, "user_id": user_id}, {"_id": 0})
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        # Check if already paused
        if bot.get('status') == 'paused':
            return {
                "success": False,
                "message": f"Bot '{bot['name']}' is already paused",
                "bot": bot
            }
        
        # Pause the bot
        if data is None:
            data = {}
        reason = data.get('reason', 'Manual pause by user')
        paused_at = datetime.now(timezone.utc).isoformat()
        
        await bots_collection.update_one(
            {"id": bot_id},
            {
                "$set": {
                    "status": "paused",
                    "paused_at": paused_at,
                    "pause_reason": reason,
                    "paused_by_user": True
                }
            }
        )
        
        # Get updated bot
        updated_bot = await bots_collection.find_one({"id": bot_id}, {"_id": 0})
        
        # Send real-time notification
        await rt_events.bot_paused(user_id, updated_bot)
        
        logger.info(f"✅ Bot {bot['name']} paused by user {user_id[:8]}")
        
        return {
            "success": True,
            "message": f"Bot '{bot['name']}' paused successfully",
            "bot": updated_bot
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pause bot error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{bot_id}/resume")
@router.put("/{bot_id}/resume")
async def resume_bot(bot_id: str, user_id: str = Depends(get_current_user)):
    """Resume a paused bot's trading activity
    
    Accepts both POST and PUT methods for compatibility with frontend
    
    Args:
        bot_id: Bot ID to resume
        user_id: Current user ID (from auth)
        
    Returns:
        Updated bot status
    """
    try:
        # Verify bot belongs to user
        bot = await bots_collection.find_one({"id": bot_id, "user_id": user_id}, {"_id": 0})
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        # Check if currently paused
        if bot.get('status') != 'paused':
            return {
                "success": False,
                "message": f"Bot '{bot['name']}' is not paused (status: {bot.get('status', 'unknown')})",
                "bot": bot
            }
        
        # Resume the bot
        resumed_at = datetime.now(timezone.utc).isoformat()
        
        await bots_collection.update_one(
            {"id": bot_id},
            {
                "$set": {
                    "status": "active",
                    "resumed_at": resumed_at
                },
                "$unset": {
                    "paused_at": "",
                    "pause_reason": "",
                    "paused_by_user": "",
                    "paused_by_system": ""
                }
            }
        )
        
        # Get updated bot
        updated_bot = await bots_collection.find_one({"id": bot_id}, {"_id": 0})
        
        # Send real-time notification
        await rt_events.bot_resumed(user_id, updated_bot)
        
        logger.info(f"✅ Bot {bot['name']} resumed by user {user_id[:8]}")
        
        return {
            "success": True,
            "message": f"Bot '{bot['name']}' resumed successfully",
            "bot": updated_bot
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resume bot error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{bot_id}/cooldown")
async def set_bot_cooldown(
    bot_id: str, 
    data: dict,
    user_id: str = Depends(get_current_user)
):
    """Set custom cooldown period for a bot
    
    Args:
        bot_id: Bot ID
        data: {"cooldown_minutes": int} - Cooldown period in minutes
        user_id: Current user ID (from auth)
        
    Returns:
        Updated bot with cooldown settings
    """
    try:
        # Verify bot belongs to user
        bot = await bots_collection.find_one({"id": bot_id, "user_id": user_id}, {"_id": 0})
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        # Validate cooldown period
        cooldown_minutes = data.get('cooldown_minutes')
        if not cooldown_minutes or not isinstance(cooldown_minutes, (int, float)):
            raise HTTPException(status_code=400, detail="Invalid cooldown_minutes value")
        
        # Validate range (5 minutes to 120 minutes)
        if cooldown_minutes < 5 or cooldown_minutes > 120:
            raise HTTPException(
                status_code=400, 
                detail="Cooldown period must be between 5 and 120 minutes"
            )
        
        # Update bot cooldown
        await bots_collection.update_one(
            {"id": bot_id},
            {
                "$set": {
                    "custom_cooldown_minutes": cooldown_minutes,
                    "cooldown_updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        # Get updated bot
        updated_bot = await bots_collection.find_one({"id": bot_id}, {"_id": 0})
        
        logger.info(f"✅ Bot {bot['name']} cooldown set to {cooldown_minutes} minutes")
        
        return {
            "success": True,
            "message": f"Cooldown set to {cooldown_minutes} minutes for '{bot['name']}'",
            "bot": updated_bot,
            "cooldown_minutes": cooldown_minutes
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Set cooldown error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{bot_id}/status")
async def get_bot_detailed_status(bot_id: str, user_id: str = Depends(get_current_user)):
    """Get detailed status information for a bot
    
    Args:
        bot_id: Bot ID
        user_id: Current user ID (from auth)
        
    Returns:
        Comprehensive bot status including cooldown info, recent trades, etc.
    """
    try:
        # Verify bot belongs to user
        bot = await bots_collection.find_one({"id": bot_id, "user_id": user_id}, {"_id": 0})
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        # Calculate cooldown status
        last_trade_time = bot.get('last_trade_time')
        custom_cooldown = bot.get('custom_cooldown_minutes', 15)  # Default 15 minutes
        cooldown_remaining = 0
        can_trade_at = None
        
        if last_trade_time:
            if isinstance(last_trade_time, str):
                last_trade_dt = datetime.fromisoformat(last_trade_time.replace('Z', '+00:00'))
            else:
                last_trade_dt = last_trade_time
            
            next_trade_allowed = last_trade_dt + timedelta(minutes=custom_cooldown)
            now = datetime.now(timezone.utc)
            
            if now < next_trade_allowed:
                cooldown_remaining = int((next_trade_allowed - now).total_seconds() / 60)
                can_trade_at = next_trade_allowed.isoformat()
        
        # Get recent trades (last 10)
        recent_trades = await trades_collection.find(
            {"bot_id": bot_id},
            {"_id": 0}
        ).sort("timestamp", -1).limit(10).to_list(10)
        
        # Calculate daily stats
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        trades_today = await trades_collection.count_documents({
            "bot_id": bot_id,
            "timestamp": {"$gte": today_start.isoformat()}
        })
        
        # Calculate profit today
        today_trades = await trades_collection.find(
            {
                "bot_id": bot_id,
                "timestamp": {"$gte": today_start.isoformat()}
            },
            {"_id": 0}
        ).to_list(1000)
        
        profit_today = sum(t.get('profit_loss', 0) for t in today_trades)
        
        return {
            "bot": bot,
            "status": {
                "current_status": bot.get('status', 'unknown'),
                "is_active": bot.get('status') == 'active',
                "is_paused": bot.get('status') == 'paused',
                "pause_reason": bot.get('pause_reason'),
                "paused_at": bot.get('paused_at'),
                "paused_by_system": bot.get('paused_by_system', False)
            },
            "cooldown": {
                "custom_cooldown_minutes": custom_cooldown,
                "remaining_minutes": cooldown_remaining,
                "can_trade_now": cooldown_remaining == 0 and bot.get('status') == 'active',
                "next_trade_at": can_trade_at
            },
            "performance": {
                "total_trades": bot.get('trades_count', 0),
                "trades_today": trades_today,
                "total_profit": bot.get('total_profit', 0),
                "profit_today": round(profit_today, 2),
                "current_capital": bot.get('current_capital', 0),
                "win_rate": bot.get('win_rate', 0)
            },
            "recent_trades": recent_trades[:5]  # Last 5 trades
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get bot status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pause-all")
async def pause_all_bots(data: Optional[Dict] = None, user_id: str = Depends(get_current_user)):
    """Pause all active bots for a user
    
    Args:
        data: Optional data with reason for pause
        user_id: Current user ID (from auth)
        
    Returns:
        Summary of paused bots
    """
    try:
        if data is None:
            data = {}
        reason = data.get('reason', 'Bulk pause by user')
        paused_at = datetime.now(timezone.utc).isoformat()
        
        # Pause all active bots
        result = await bots_collection.update_many(
            {"user_id": user_id, "status": "active"},
            {
                "$set": {
                    "status": "paused",
                    "paused_at": paused_at,
                    "pause_reason": reason,
                    "paused_by_user": True
                }
            }
        )
        
        # Send real-time notification
        await rt_events.force_refresh(user_id, f"Paused {result.modified_count} bots")
        
        logger.info(f"✅ Paused {result.modified_count} bots for user {user_id[:8]}")
        
        return {
            "success": True,
            "message": f"Paused {result.modified_count} bot(s)",
            "paused_count": result.modified_count
        }
        
    except Exception as e:
        logger.error(f"Pause all bots error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume-all")
async def resume_all_bots(user_id: str = Depends(get_current_user)):
    """Resume all paused bots for a user
    
    Args:
        user_id: Current user ID (from auth)
        
    Returns:
        Summary of resumed bots
    """
    try:
        resumed_at = datetime.now(timezone.utc).isoformat()
        
        # Resume all paused bots (only those paused by user, not system)
        result = await bots_collection.update_many(
            {"user_id": user_id, "status": "paused", "paused_by_user": True},
            {
                "$set": {
                    "status": "active",
                    "resumed_at": resumed_at
                },
                "$unset": {
                    "paused_at": "",
                    "pause_reason": "",
                    "paused_by_user": ""
                }
            }
        )
        
        # Send real-time notification
        await rt_events.force_refresh(user_id, f"Resumed {result.modified_count} bots")
        
        logger.info(f"✅ Resumed {result.modified_count} bots for user {user_id[:8]}")
        
        return {
            "success": True,
            "message": f"Resumed {result.modified_count} bot(s)",
            "resumed_count": result.modified_count
        }
        
    except Exception as e:
        logger.error(f"Resume all bots error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
