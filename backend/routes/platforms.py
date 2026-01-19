"""
Platform Endpoints - Platform-specific bot performance and drilldown
Provides per-exchange analytics and bot listings
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
import logging

from auth import get_current_user
import database as db
from services.profit_service import profit_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/platforms", tags=["Platforms"])

# Supported platforms/exchanges
EXCHANGES = ["luno", "binance", "kucoin", "ovex", "valr"]


@router.get("/summary")
async def get_platforms_summary(
    mode: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """Get summary of all platforms with performance metrics
    
    Returns per-platform:
    - bots_count_total
    - bots_active
    - profit_today
    - profit_total
    - trades_today
    - win_rate
    
    Args:
        mode: Filter by trading mode ('paper' or 'live', None = current system mode)
        user_id: Current user ID
        
    Returns:
        Summary data for each platform
    """
    try:
        # Get system mode if not specified
        if not mode:
            from routes.system_mode import get_system_mode
            system_mode = await get_system_mode()
            if system_mode.get("paperTrading"):
                mode = "paper"
            elif system_mode.get("liveTrading"):
                mode = "live"
            else:
                mode = "paper"  # Default to paper
        
        # Calculate today's start
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        
        # Get all user's bots
        bots_query = {"user_id": user_id}
        if mode:
            bots_query["trading_mode"] = mode
        
        bots_cursor = db.bots_collection.find(bots_query, {"_id": 0})
        all_bots = await bots_cursor.to_list(1000)
        
        # Build summary for each exchange
        platform_summaries = []
        
        for exchange in EXCHANGES:
            # Filter bots for this exchange
            exchange_bots = [b for b in all_bots if b.get("exchange") == exchange]
            
            bots_count_total = len(exchange_bots)
            bots_active = sum(1 for b in exchange_bots if b.get("status") == "active")
            
            # Calculate profit for this exchange's bots
            bot_ids = [b["id"] for b in exchange_bots if "id" in b]
            
            # Get today's trades for these bots
            today_trades_query = {
                "bot_id": {"$in": bot_ids},
                "status": "closed",
                "timestamp": {"$gte": today_start.isoformat()}
            }
            
            today_trades_cursor = db.trades_collection.find(
                today_trades_query,
                {"_id": 0, "profit_loss": 1}
            )
            today_trades = await today_trades_cursor.to_list(1000)
            
            profit_today = sum(t.get("profit_loss", 0) for t in today_trades)
            trades_today = len(today_trades)
            
            # Get all-time trades for these bots
            all_trades_query = {
                "bot_id": {"$in": bot_ids},
                "status": "closed"
            }
            
            all_trades_cursor = db.trades_collection.find(
                all_trades_query,
                {"_id": 0, "profit_loss": 1}
            )
            all_trades = await all_trades_cursor.to_list(10000)
            
            profit_total = sum(t.get("profit_loss", 0) for t in all_trades)
            
            # Calculate win rate
            winning_trades = sum(1 for t in all_trades if t.get("profit_loss", 0) > 0)
            win_rate = (winning_trades / len(all_trades) * 100) if all_trades else 0
            
            platform_summaries.append({
                "platform": exchange,
                "display_name": exchange.upper(),
                "bots_count_total": bots_count_total,
                "bots_active": bots_active,
                "profit_today": round(profit_today, 2),
                "profit_total": round(profit_total, 2),
                "trades_today": trades_today,
                "win_rate": round(win_rate, 2)
            })
        
        return {
            "success": True,
            "mode": mode,
            "platforms": platform_summaries,
            "total_platforms": len(EXCHANGES),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Get platforms summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{platform}/bots")
async def get_platform_bots(
    platform: str,
    mode: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """Get all bots on a specific platform with performance metrics
    
    Args:
        platform: Platform/exchange name (luno, binance, kucoin, ovex, valr)
        mode: Filter by trading mode ('paper' or 'live')
        user_id: Current user ID
        
    Returns:
        List of bots with performance data and action controls
    """
    try:
        # Validate platform
        if platform.lower() not in EXCHANGES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid platform. Must be one of: {', '.join(EXCHANGES)}"
            )
        
        # Get system mode if not specified
        if not mode:
            from routes.system_mode import get_system_mode
            system_mode = await get_system_mode()
            if system_mode.get("paperTrading"):
                mode = "paper"
            elif system_mode.get("liveTrading"):
                mode = "live"
            else:
                mode = "paper"
        
        # Get bots for this platform
        bots_query = {
            "user_id": user_id,
            "exchange": platform.lower()
        }
        
        if mode:
            bots_query["trading_mode"] = mode
        
        bots_cursor = db.bots_collection.find(bots_query, {"_id": 0})
        bots = await bots_cursor.to_list(1000)
        
        # Enrich each bot with performance data
        enriched_bots = []
        
        for bot in bots:
            bot_id = bot.get("id")
            
            if not bot_id:
                continue
            
            # Get bot's trades
            trades_query = {
                "bot_id": bot_id,
                "status": "closed"
            }
            
            trades_cursor = db.trades_collection.find(
                trades_query,
                {"_id": 0, "profit_loss": 1, "timestamp": 1}
            )
            trades = await trades_cursor.to_list(1000)
            
            # Calculate performance
            total_profit = sum(t.get("profit_loss", 0) for t in trades)
            total_trades = len(trades)
            winning_trades = sum(1 for t in trades if t.get("profit_loss", 0) > 0)
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Calculate today's profit
            today_start = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            
            today_trades = [
                t for t in trades
                if t.get("timestamp") and t["timestamp"] >= today_start.isoformat()
            ]
            
            profit_today = sum(t.get("profit_loss", 0) for t in today_trades)
            
            # Build enriched bot data
            enriched_bot = {
                "id": bot_id,
                "name": bot.get("name"),
                "pair": bot.get("pair"),
                "status": bot.get("status"),
                "trading_mode": bot.get("trading_mode"),
                "current_capital": bot.get("current_capital", 0),
                "total_profit": round(total_profit, 2),
                "profit_today": round(profit_today, 2),
                "total_trades": total_trades,
                "win_rate": round(win_rate, 2),
                "created_at": bot.get("created_at"),
                "last_trade_time": bot.get("last_trade_time"),
                # Action controls
                "can_start": bot.get("status") in ["stopped", "paused"],
                "can_pause": bot.get("status") == "active",
                "can_resume": bot.get("status") == "paused",
                "can_stop": bot.get("status") in ["active", "paused"],
                "can_delete": True  # With safety checks in delete endpoint
            }
            
            enriched_bots.append(enriched_bot)
        
        # Sort by profit_total descending
        enriched_bots.sort(key=lambda b: b["total_profit"], reverse=True)
        
        return {
            "success": True,
            "platform": platform.lower(),
            "display_name": platform.upper(),
            "mode": mode,
            "bots": enriched_bots,
            "total_bots": len(enriched_bots),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get platform bots error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
