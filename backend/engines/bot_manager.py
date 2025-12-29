"""
Bot Manager - Enforces limits and manages bot lifecycle
"""
import asyncio
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import database as db
from config import EXCHANGE_BOT_LIMITS, NEW_BOT_CAPITAL
from logger_config import logger


class BotManager:
    def __init__(self):
        self.limits = EXCHANGE_BOT_LIMITS
    
    async def can_create_bot(self, user_id: str, exchange: str) -> tuple[bool, str]:
        """Check if user can create a bot on this exchange"""
        try:
            # Get current bot count for this exchange
            count = await db.bots_collection.count_documents({
                "user_id": user_id,
                "exchange": exchange
            })
            
            limit = self.limits.get(exchange.lower(), 10)
            
            if count >= limit:
                return False, f"❌ Maximum {limit} bots allowed for {exchange.upper()}"
            
            return True, f"✅ Can create bot ({count + 1}/{limit})"
        except Exception as e:
            logger.error(f"Can create bot check error: {e}")
            return False, f"❌ Error: {str(e)}"
    
    async def create_bot(self, user_id: str, name: str, exchange: str, risk_mode: str = 'safe', capital: float = None) -> dict:
        """Create a new bot with all validations"""
        try:
            # Check limits
            can_create, message = await self.can_create_bot(user_id, exchange)
            if not can_create:
                return {"success": False, "message": message}
            
            # Validate capital
            if capital is None:
                capital = NEW_BOT_CAPITAL
            
            if capital < NEW_BOT_CAPITAL:
                return {"success": False, "message": f"❌ Minimum capital is R{NEW_BOT_CAPITAL}"}
            
            # Determine trading pair
            pair = "BTC/ZAR" if exchange.lower() in ['luno', 'valr'] else "BTC/USDT"
            
            # Create bot document
            bot = {
                "id": str(uuid4()),
                "user_id": user_id,
                "name": name,
                "status": "active",
                "exchange": exchange.lower(),
                "pair": pair,
                "risk_mode": risk_mode,
                "initial_capital": capital,
                "current_capital": capital,
                "mode": "paper",  # paper or live
                "trading_mode": "paper",
                "trades_count": 0,
                "daily_trade_count": 0,
                "last_trade_time": None,
                "win_count": 0,
                "loss_count": 0,
                "total_profit": 0,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "paper_start_date": datetime.now(timezone.utc).isoformat(),
                "paper_end_eligible_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                "learning_complete": False
            }
            
            await db.bots_collection.insert_one(bot)
            
            logger.info(f"✅ Created bot: {name} on {exchange} for user {user_id[:8]}")
            
            # Remove _id before returning (MongoDB adds it automatically)
            bot_clean = {k: v for k, v in bot.items() if k != '_id'}
            
            return {
                "success": True,
                "message": f"✅ Created '{name}' on {exchange.upper()} with R{capital:,.0f} ({risk_mode} mode)",
                "bot": bot_clean
            }
        
        except Exception as e:
            logger.error(f"Bot creation error: {e}")
            return {"success": False, "message": f"❌ Error: {str(e)}"}
    
    async def delete_bot(self, user_id: str, bot_id: str = None, bot_name: str = None) -> dict:
        """Delete a bot"""
        try:
            query = {"user_id": user_id}
            if bot_id:
                query["id"] = bot_id
            elif bot_name:
                query["name"] = bot_name
            else:
                return {"success": False, "message": "❌ No bot specified"}
            
            result = await db.bots_collection.delete_one(query)
            
            if result.deleted_count > 0:
                return {"success": True, "message": "✅ Bot deleted"}
            return {"success": False, "message": "❌ Bot not found"}
        
        except Exception as e:
            logger.error(f"Delete bot error: {e}")
            return {"success": False, "message": f"❌ Error: {str(e)}"}
    
    async def update_bot_status(self, user_id: str, bot_id: str, status: str) -> dict:
        """Update bot status (active/paused)"""
        try:
            result = await db.bots_collection.update_one(
                {"user_id": user_id, "id": bot_id},
                {"$set": {"status": status}}
            )
            
            if result.modified_count > 0:
                return {"success": True, "message": f"✅ Bot {status}"}
            return {"success": False, "message": "❌ Bot not found"}
        
        except Exception as e:
            logger.error(f"Update status error: {e}")
            return {"success": False, "message": f"❌ Error: {str(e)}"}
    
    async def reset_daily_trade_counts(self):
        """Reset daily trade counts for all bots (called at midnight)"""
        try:
            result = await db.bots_collection.update_many(
                {},
                {"$set": {"daily_trade_count": 0}}
            )
            logger.info(f"✅ Reset daily trade counts for {result.modified_count} bots")
        except Exception as e:
            logger.error(f"Reset daily counts error: {e}")


bot_manager = BotManager()
