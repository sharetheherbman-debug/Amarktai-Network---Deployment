"""
Trade Limiter - Enforces per-exchange trade limits and cooldowns
"""
import asyncio
from datetime import datetime, timezone, timedelta
import database as db
from config import EXCHANGE_TRADE_LIMITS, MAX_TRADES_PER_USER_PER_DAY
from logger_config import logger
import random


class TradeLimiter:
    def __init__(self):
        self.exchange_limits = EXCHANGE_TRADE_LIMITS
        self.max_user_daily_trades = MAX_TRADES_PER_USER_PER_DAY
    
    async def can_trade(self, bot_id: str) -> tuple[bool, str]:
        """Check if bot is allowed to trade now"""
        try:
            bot = await db.bots_collection.find_one({"id": bot_id}, {"_id": 0})
            
            if not bot:
                return False, "Bot not found"
            
            if bot.get('status') != 'active':
                return False, "Bot is not active"
            
            # Get exchange-specific limits
            exchange = bot.get('exchange', 'binance').lower()
            limits = self.exchange_limits.get(exchange, self.exchange_limits['binance'])
            
            max_daily = limits['max_trades_per_bot_per_day']
            min_cooldown = limits['min_cooldown_minutes']
            
            # Check daily limit
            daily_count = bot.get('daily_trade_count', 0)
            if daily_count >= max_daily:
                return False, f"Daily limit reached ({daily_count}/{max_daily} for {exchange})"
            
            # Check cooldown
            last_trade = bot.get('last_trade_time')
            if last_trade:
                if isinstance(last_trade, str):
                    last_trade = datetime.fromisoformat(last_trade.replace('Z', '+00:00'))
                
                # Random cooldown with jitter (min_cooldown + 0-5 minutes)
                cooldown = random.randint(min_cooldown, min_cooldown + 5)
                next_allowed = last_trade + timedelta(minutes=cooldown)
                
                now = datetime.now(timezone.utc)
                if now < next_allowed:
                    wait_minutes = int((next_allowed - now).total_seconds() / 60)
                    return False, f"Cooldown active ({wait_minutes} min remaining)"
            
            return True, "OK"
        
        except Exception as e:
            logger.error(f"Can trade check error: {e}")
            return False, f"Error: {str(e)}"
    
    async def record_trade(self, bot_id: str) -> bool:
        """Record that a trade was executed"""
        try:
            result = await db.bots_collection.update_one(
                {"id": bot_id},
                {
                    "$set": {"last_trade_time": datetime.now(timezone.utc).isoformat()},
                    "$inc": {
                        "daily_trade_count": 1,
                        "trades_count": 1
                    }
                }
            )
            
            return result.modified_count > 0
        
        except Exception as e:
            logger.error(f"Record trade error: {e}")
            return False
    
    async def get_bot_trade_status(self, bot_id: str) -> dict:
        """Get current trade status for a bot"""
        try:
            bot = await db.bots_collection.find_one({"id": bot_id}, {"_id": 0})
            
            if not bot:
                return {"error": "Bot not found"}
            
            exchange = bot.get('exchange', 'binance').lower()
            limits = self.exchange_limits.get(exchange, self.exchange_limits['binance'])
            max_daily = limits['max_trades_per_bot_per_day']
            
            daily_count = bot.get('daily_trade_count', 0)
            remaining = max_daily - daily_count
            
            can_trade, reason = await self.can_trade(bot_id)
            
            return {
                "bot_id": bot_id,
                "bot_name": bot.get('name'),
                "exchange": exchange,
                "daily_trades": daily_count,
                "daily_limit": max_daily,
                "remaining_today": max(0, remaining),
                "can_trade_now": can_trade,
                "reason": reason
            }
        
        except Exception as e:
            logger.error(f"Get trade status error: {e}")
            return {"error": str(e)}


trade_limiter = TradeLimiter()
