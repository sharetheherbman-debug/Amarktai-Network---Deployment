"""
Mode Manager - Handle Paper vs Live Mode Separation

Ensures clean separation of paper and live trading data:
- Separate equity tracking
- Mode-aware PnL calculations
- Smooth transitions from paper to live
"""

import database as db
from logger_config import logger
from datetime import datetime, timezone


class ModeManager:
    """Manages paper vs live mode separation"""
    
    async def get_user_mode_stats(self, user_id: str) -> dict:
        """Get separate paper and live stats for user"""
        try:
            bots = await db.bots_collection.find({"user_id": user_id}, {"_id": 0}).to_list(100)
            active_bots = [b for b in bots if b.get('status') == 'active']
            
            # Separate by mode
            paper_bots = [b for b in active_bots if b.get('trading_mode') == 'paper']
            live_bots = [b for b in active_bots if b.get('trading_mode') == 'live']
            
            # Calculate paper stats
            paper_equity = sum(b.get('current_capital', 0) for b in paper_bots)
            paper_initial = sum(b.get('initial_capital', 0) for b in paper_bots)
            paper_pnl = paper_equity - paper_initial
            
            # Calculate live stats
            live_equity = sum(b.get('current_capital', 0) for b in live_bots)
            live_initial = sum(b.get('initial_capital', 0) for b in live_bots)
            live_pnl = live_equity - live_initial
            
            # Get today's trades
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0).isoformat()
            
            paper_trades_today = await db.trades_collection.count_documents({
                "user_id": user_id,
                "timestamp": {"$gte": today_start},
                "mode": "paper"
            })
            
            live_trades_today = await db.trades_collection.count_documents({
                "user_id": user_id,
                "timestamp": {"$gte": today_start},
                "mode": "live"
            })
            
            # Get today's PnL
            paper_trades = await db.trades_collection.find({
                "user_id": user_id,
                "timestamp": {"$gte": today_start},
                "mode": "paper"
            }, {"_id": 0}).to_list(10000)
            
            live_trades = await db.trades_collection.find({
                "user_id": user_id,
                "timestamp": {"$gte": today_start},
                "mode": "live"
            }, {"_id": 0}).to_list(10000)
            
            paper_pnl_today = sum(t.get('profit_loss', 0) for t in paper_trades)
            live_pnl_today = sum(t.get('profit_loss', 0) for t in live_trades)
            
            return {
                "paper": {
                    "equity": round(paper_equity, 2),
                    "pnl": round(paper_pnl, 2),
                    "pnl_today": round(paper_pnl_today, 2),
                    "bots": len(paper_bots),
                    "trades_today": paper_trades_today
                },
                "live": {
                    "equity": round(live_equity, 2),
                    "pnl": round(live_pnl, 2),
                    "pnl_today": round(live_pnl_today, 2),
                    "bots": len(live_bots),
                    "trades_today": live_trades_today
                },
                "total_bots": len(active_bots)
            }
        except Exception as e:
            logger.error(f"Mode stats error: {e}")
            return {
                "paper": {"equity": 0, "pnl": 0, "pnl_today": 0, "bots": 0, "trades_today": 0},
                "live": {"equity": 0, "pnl": 0, "pnl_today": 0, "bots": 0, "trades_today": 0},
                "total_bots": 0
            }
    
    async def switch_bot_to_live(self, bot_id: str) -> dict:
        """Switch bot from paper to live - preserve history, start fresh"""
        try:
            bot = await db.bots_collection.find_one({"id": bot_id}, {"_id": 0})
            if not bot:
                return {"success": False, "error": "Bot not found"}
            
            if bot.get('trading_mode') == 'live':
                return {"success": False, "error": "Bot already in live mode"}
            
            # Preserve paper performance
            paper_performance = {
                "paper_final_capital": bot.get('current_capital', 0),
                "paper_total_profit": bot.get('current_capital', 0) - bot.get('initial_capital', 0),
                "paper_trades_count": bot.get('trades_count', 0),
                "paper_win_rate": bot.get('win_rate', 0),
                "switched_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Reset for live trading
            initial_capital = bot.get('initial_capital', 1000)
            
            await db.bots_collection.update_one(
                {"id": bot_id},
                {"$set": {
                    "trading_mode": "live",
                    "current_capital": initial_capital,
                    "total_profit": 0.0,
                    "trades_count": 0,
                    "paper_performance": paper_performance,
                    "live_started_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            
            logger.info(f"Bot {bot['name']} switched to LIVE - capital reset to R{initial_capital}")
            return {"success": True, "message": f"Bot switched to live trading with R{initial_capital}"}
            
        except Exception as e:
            logger.error(f"Bot switch error: {e}")
            return {"success": False, "error": str(e)}


# Global instance
mode_manager = ModeManager()
