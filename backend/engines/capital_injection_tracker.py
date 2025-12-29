"""
Capital Injection Tracker - Separates Trading Profits from Capital Injections
Solves the profit corruption issue when autopilot reinvests capital
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict
import logging

import database as db

logger = logging.getLogger(__name__)

# Create collection for tracking capital injections
capital_injections_collection = db.capital_injections

class CapitalInjectionTracker:
    """
    Tracks all capital injections separate from trading profits
    
    Real Profit = (Current Capital - Total Injections) - Initial Capital
    """
    
    def __init__(self):
        pass
    
    async def record_injection(self, bot_id: str, amount: float, source: str, reason: str) -> bool:
        """
        Record a capital injection into a bot
        
        Args:
            bot_id: Bot receiving the injection
            amount: Amount of capital injected
            source: Where capital came from ('autopilot', 'user', 'rebalance')
            reason: Reason for injection
        """
        try:
            injection_doc = {
                "bot_id": bot_id,
                "amount": amount,
                "source": source,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await capital_injections_collection.insert_one(injection_doc)
            
            # Update bot's total_injections field
            await db.bots_collection.update_one(
                {"id": bot_id},
                {
                    "$inc": {"total_injections": amount},
                    "$set": {"last_injection_at": datetime.now(timezone.utc).isoformat()}
                }
            )
            
            logger.info(f"💉 Capital injection: R{amount:.2f} → Bot {bot_id[:8]} ({source})")
            return True
            
        except Exception as e:
            logger.error(f"Record injection error: {e}")
            return False
    
    async def get_bot_injections(self, bot_id: str) -> float:
        """Get total capital injected into a bot"""
        try:
            injections = await capital_injections_collection.find(
                {"bot_id": bot_id},
                {"_id": 0}
            ).to_list(1000)
            
            total = sum(inj.get('amount', 0) for inj in injections)
            return total
            
        except Exception as e:
            logger.error(f"Get injections error: {e}")
            return 0.0
    
    async def calculate_real_profit(self, bot_id: str) -> Dict:
        """
        Calculate real trading profit excluding injections
        
        Returns:
            {
                "current_capital": float,
                "initial_capital": float,
                "total_injections": float,
                "gross_profit": float,  # current - initial
                "real_profit": float,   # gross_profit - injections
                "roi": float            # (real_profit / initial_capital) * 100
            }
        """
        try:
            bot = await db.bots_collection.find_one({"id": bot_id}, {"_id": 0})
            
            if not bot:
                return {"error": "Bot not found"}
            
            current_capital = bot.get('current_capital', 0)
            initial_capital = bot.get('initial_capital', 0)
            total_injections = bot.get('total_injections', 0)
            
            # Gross profit = current - initial (includes injections)
            gross_profit = current_capital - initial_capital
            
            # Real profit = gross - injections (pure trading profit)
            real_profit = gross_profit - total_injections
            
            # ROI based on initial capital
            roi = (real_profit / initial_capital * 100) if initial_capital > 0 else 0
            
            return {
                "bot_id": bot_id,
                "bot_name": bot.get('name'),
                "current_capital": current_capital,
                "initial_capital": initial_capital,
                "total_injections": total_injections,
                "gross_profit": gross_profit,
                "real_profit": real_profit,
                "roi": roi,
                "calculated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Calculate real profit error: {e}")
            return {"error": str(e)}
    
    async def calculate_user_real_profit(self, user_id: str) -> Dict:
        """Calculate total real profit for all user's bots"""
        try:
            bots = await db.bots_collection.find(
                {"user_id": user_id},
                {"_id": 0}
            ).to_list(1000)
            
            total_current = 0
            total_initial = 0
            total_injections = 0
            
            for bot in bots:
                total_current += bot.get('current_capital', 0)
                total_initial += bot.get('initial_capital', 0)
                total_injections += bot.get('total_injections', 0)
            
            gross_profit = total_current - total_initial
            real_profit = gross_profit - total_injections
            roi = (real_profit / total_initial * 100) if total_initial > 0 else 0
            
            return {
                "user_id": user_id,
                "total_current_capital": total_current,
                "total_initial_capital": total_initial,
                "total_injections": total_injections,
                "gross_profit": gross_profit,
                "real_profit": real_profit,
                "roi": roi,
                "calculated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Calculate user real profit error: {e}")
            return {"error": str(e)}
    
    async def get_injection_history(self, bot_id: str = None, user_id: str = None, limit: int = 100) -> list:
        """Get history of capital injections"""
        try:
            query = {}
            
            if bot_id:
                query["bot_id"] = bot_id
            elif user_id:
                # Get all bot IDs for user
                bots = await db.bots_collection.find(
                    {"user_id": user_id},
                    {"_id": 0, "id": 1}
                ).to_list(1000)
                
                bot_ids = [b['id'] for b in bots]
                query["bot_id"] = {"$in": bot_ids}
            
            injections = await capital_injections_collection.find(
                query,
                {"_id": 0}
            ).sort("timestamp", -1).limit(limit).to_list(limit)
            
            return injections
            
        except Exception as e:
            logger.error(f"Get injection history error: {e}")
            return []
    
    async def initialize_existing_bots(self):
        """
        Initialize total_injections field for existing bots
        Run once on first startup
        """
        try:
            # Set total_injections = 0 for all bots that don't have it
            result = await db.bots_collection.update_many(
                {"total_injections": {"$exists": False}},
                {"$set": {"total_injections": 0}}
            )
            
            logger.info(f"✅ Initialized capital tracking for {result.modified_count} bots")
            return True
            
        except Exception as e:
            logger.error(f"Initialize bots error: {e}")
            return False

# Global instance
capital_tracker = CapitalInjectionTracker()
