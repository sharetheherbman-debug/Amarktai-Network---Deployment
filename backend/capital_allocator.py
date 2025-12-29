"""
DEPRECATED - DO NOT USE

This file is kept for backwards compatibility only.

NEW PRODUCTION SYSTEM:
- Use /app/backend/engines/capital_allocator.py (Phase 5 implementation)
- Use /app/backend/engines/capital_injection_tracker.py (profit tracking)
- Use /app/backend/engines/autopilot_production.py (reinvestment)

The new system properly tracks capital injections separately from trading profits,
preventing the profit corruption issue that existed in this old implementation.
"""

import asyncio
from datetime import datetime, timezone
import database as db
from logger_config import logger
from performance_ranker import performance_ranker


class CapitalAllocator:
    """DEPRECATED - Use engines/capital_allocator.py instead"""
    
    def __init__(self):
        self.reallocation_threshold = 0.15
        self.min_bot_capital = 500
        logger.warning("⚠️  Old capital_allocator.py loaded - use engines/capital_allocator.py instead")
    
    async def reallocate_capital(self, user_id: str) -> dict:
        """
        DEPRECATED - Capital reallocation now handled by:
        1. engines/capital_allocator.py (performance-based allocation)
        2. engines/capital_injection_tracker.py (tracks injections separately)
        3. engines/autopilot_production.py (handles reinvestment)
        """
        logger.warning("⚠️  Deprecated capital_allocator called - redirecting to new system")
        
        # Import and use new system
        from engines.capital_allocator import capital_allocator as new_allocator
        return await new_allocator.rebalance_all_bots(user_id)
        
        try:
            # Get performance rankings
            top_bots = await performance_ranker.get_top_performers(user_id, limit=5)
            bottom_bots = await performance_ranker.get_bottom_performers(user_id, limit=5)
            
            if not top_bots or not bottom_bots:
                return {"reallocated": 0, "message": "Insufficient bots for reallocation"}
            
            # Calculate available capital from bottom performers
            available_capital = 0
            for bot in bottom_bots:
                current_capital = bot.get('current_capital', 1000)
                if current_capital > self.min_bot_capital:
                    # Take up to 15% from poor performers
                    takeable = (current_capital - self.min_bot_capital) * self.reallocation_threshold
                    available_capital += takeable
                    
                    # Update bot capital
                    new_capital = current_capital - takeable
                    await db.bots_collection.update_one(
                        {"id": bot['id']},
                        {
                            "$set": {"current_capital": new_capital},
                            "$push": {
                                "capital_history": {
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                    "amount": -takeable,
                                    "reason": "Reallocation (poor performance)"
                                }
                            }
                        }
                    )
            
            # Distribute to top performers
            if available_capital > 0:
                capital_per_top_bot = available_capital / len(top_bots)
                
                for bot in top_bots:
                    current_capital = bot.get('current_capital', 1000)
                    new_capital = current_capital + capital_per_top_bot
                    
                    await db.bots_collection.update_one(
                        {"id": bot['id']},
                        {
                            "$set": {"current_capital": new_capital},
                            "$push": {
                                "capital_history": {
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                    "amount": capital_per_top_bot,
                                    "reason": "Reallocation (top performer)"
                                }
                            }
                        }
                    )
                
                logger.info(f"Reallocated R{available_capital:.2f} to {len(top_bots)} top performers")
                return {
                    "reallocated": round(available_capital, 2),
                    "top_bots": len(top_bots),
                    "bottom_bots": len(bottom_bots),
                    "message": f"Redistributed R{available_capital:.2f}"
                }
            else:
                return {"reallocated": 0, "message": "No capital available for reallocation"}
                
        except Exception as e:
            logger.error(f"Capital reallocation failed: {e}")
            return {"reallocated": 0, "error": str(e)}
    
    async def reinvest_daily_profits(self, user_id: str) -> dict:
        """Reinvest daily profits to active bots based on performance"""
        try:
            # Calculate today's profit
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0).isoformat()
            
            trades_today = await db.trades_collection.find({
                "user_id": user_id,
                "timestamp": {"$gte": today_start}
            }, {"_id": 0}).to_list(10000)
            
            daily_profit = sum(t.get('pnl', 0) for t in trades_today)
            
            if daily_profit <= 0:
                return {"reinvested": 0, "message": "No profit to reinvest"}
            
            # Reinvest 80% of profit, keep 20% as reserves
            reinvestment_amount = daily_profit * 0.80
            
            # Get top performers
            top_bots = await performance_ranker.get_top_performers(user_id, limit=5)
            
            if not top_bots:
                return {"reinvested": 0, "message": "No active bots"}
            
            # Distribute proportionally to top performers
            capital_per_bot = reinvestment_amount / len(top_bots)
            
            for bot in top_bots:
                current_capital = bot.get('current_capital', 1000)
                new_capital = current_capital + capital_per_bot
                
                await db.bots_collection.update_one(
                    {"id": bot['id']},
                    {
                        "$set": {"current_capital": new_capital},
                        "$push": {
                            "capital_history": {
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "amount": capital_per_bot,
                                "reason": "Daily profit reinvestment"
                            }
                        }
                    }
                )
            
            logger.info(f"Reinvested R{reinvestment_amount:.2f} daily profit to {len(top_bots)} bots")
            return {
                "reinvested": round(reinvestment_amount, 2),
                "daily_profit": round(daily_profit, 2),
                "bots_funded": len(top_bots),
                "message": f"Reinvested R{reinvestment_amount:.2f} to top performers"
            }
            
        except Exception as e:
            logger.error(f"Profit reinvestment failed: {e}")
            return {"reinvested": 0, "error": str(e)}
    
    async def auto_spawn_bot(self, user_id: str) -> dict:
        """Auto-spawn new bot when R1000 profit milestone reached"""
        try:
            # Get total user profit
            trades = await db.trades_collection.find(
                {"user_id": user_id},
                {"_id": 0}
            ).to_list(10000)
            
            total_profit = sum(t.get('pnl', 0) for t in trades)
            
            # Check bot count
            bot_count = await db.bots_collection.count_documents({
                "user_id": user_id,
                "status": "active"
            })
            
            if bot_count >= 30:
                return {"spawned": False, "message": "Bot limit reached (30/30)"}
            
            # Check if R1000 milestone reached
            if total_profit >= 1000:
                # Create new AI-spawned bot
                from uuid import uuid4
                
                new_bot = {
                    "id": str(uuid4()),
                    "user_id": user_id,
                    "name": f"AI Bot #{bot_count + 1}",
                    "exchange": "luno",
                    "trading_pair": "BTC/ZAR",
                    "risk_mode": "safe",
                    "initial_capital": 1000,
                    "current_capital": 1000,
                    "total_profit": 0,
                    "status": "active",
                    "origin": "ai",
                    "trading_mode": "paper",  # Will go live if system is in live mode
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                
                await db.bots_collection.insert_one(new_bot)
                logger.info(f"Auto-spawned new bot for user {user_id} (milestone: R1000 profit)")
                
                return {
                    "spawned": True,
                    "bot_id": new_bot['id'],
                    "message": "New AI bot spawned (R1000 profit milestone)"
                }
            else:
                return {"spawned": False, "message": f"Need R{1000 - total_profit:.2f} more profit"}
                
        except Exception as e:
            logger.error(f"Auto-spawn failed: {e}")
            return {"spawned": False, "error": str(e)}


# Global instance
capital_allocator = CapitalAllocator()
