"""
Automatic Promotion Manager
- Checks bots daily for eligibility
- Auto-promotes after 7 days if criteria met
- Sends notifications
- Runs as scheduled job
"""

import asyncio
from typing import List, Dict
from datetime import datetime, timezone, timedelta
import logging

import database as db
from engines.promotion_engine import promotion_engine

logger = logging.getLogger(__name__)

class AutoPromotionManager:
    def __init__(self):
        self.check_interval_hours = 24  # Check daily
        self.min_paper_days = 7
        self.running = False
    
    async def check_bot_eligibility(self, bot: Dict) -> tuple[bool, str]:
        """Check if a single bot is eligible for auto-promotion"""
        try:
            # Check if in paper mode
            if bot.get('mode') != 'paper':
                return False, "Not in paper mode"
            
            # Check if 7 days have passed
            paper_start = bot.get('paper_start_date')
            if not paper_start:
                return False, "No paper start date"
            
            start_date = datetime.fromisoformat(paper_start.replace('Z', '+00:00'))
            days_in_paper = (datetime.now(timezone.utc) - start_date).days
            
            if days_in_paper < self.min_paper_days:
                return False, f"Only {days_in_paper} days in paper (need {self.min_paper_days})"
            
            # Check performance criteria
            eligible, message, performance = await promotion_engine.is_eligible_for_live(bot['id'])
            
            return eligible, message
            
        except Exception as e:
            logger.error(f"Eligibility check error: {e}")
            return False, str(e)
    
    async def auto_promote_bot(self, bot: Dict) -> Dict:
        """Automatically promote a bot to live"""
        try:
            bot_id = bot['id']
            user_id = bot['user_id']
            
            # Promote to live
            await db.bots_collection.update_one(
                {"id": bot_id},
                {"$set": {
                    "mode": "live",
                    "promoted_at": datetime.now(timezone.utc).isoformat(),
                    "auto_promoted": True
                }}
            )
            
            # Create alert
            await db.alerts_collection.insert_one({
                "user_id": user_id,
                "type": "auto_promotion",
                "severity": "high",
                "message": f"🎉 AUTO-PROMOTED: {bot['name']} → LIVE trading! 7-day paper period complete with passing performance.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dismissed": False,
                "bot_id": bot_id
            })
            
            logger.info(f"✅ AUTO-PROMOTED {bot['name']} to live trading")
            
            return {
                "success": True,
                "bot_id": bot_id,
                "bot_name": bot['name']
            }
            
        except Exception as e:
            logger.error(f"Auto-promotion error: {e}")
            return {"success": False, "error": str(e)}
    
    async def check_all_bots_for_promotion(self, user_id: str = None) -> Dict:
        """Check all bots and auto-promote eligible ones"""
        try:
            # Get all paper bots
            query = {"mode": "paper", "status": "active"}
            if user_id:
                query["user_id"] = user_id
            
            paper_bots = await db.bots_collection.find(query, {"_id": 0}).to_list(1000)
            
            promoted = []
            not_ready = []
            
            for bot in paper_bots:
                eligible, message = await self.check_bot_eligibility(bot)
                
                if eligible:
                    # Auto-promote
                    result = await self.auto_promote_bot(bot)
                    if result.get('success'):
                        promoted.append({
                            "bot_name": bot['name'],
                            "bot_id": bot['id']
                        })
                else:
                    not_ready.append({
                        "bot_name": bot['name'],
                        "reason": message
                    })
            
            summary = {
                "success": True,
                "checked": len(paper_bots),
                "promoted": len(promoted),
                "not_ready": len(not_ready),
                "promoted_bots": promoted,
                "not_ready_bots": not_ready[:5],  # Show first 5
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            if promoted:
                logger.info(f"🎉 Auto-promoted {len(promoted)} bots to live")
            
            return summary
            
        except Exception as e:
            logger.error(f"Auto-promotion check error: {e}")
            return {"success": False, "error": str(e)}
    
    async def run_daily_check(self):
        """Run daily auto-promotion check (called by scheduler)"""
        logger.info("🔄 Running daily auto-promotion check...")
        
        try:
            # Check all users' bots
            result = await self.check_all_bots_for_promotion()
            
            logger.info(f"✅ Daily check complete: {result.get('promoted', 0)} bots promoted")
            
            return result
            
        except Exception as e:
            logger.error(f"Daily check error: {e}")
            return {"success": False, "error": str(e)}
    
    def start(self):
        """Start the auto-promotion manager"""
        if not self.running:
            self.running = True
            logger.info("🚀 Auto-promotion manager started")
    
    def stop(self):
        """Stop the auto-promotion manager"""
        self.running = False
        logger.info("⏹️ Auto-promotion manager stopped")

# Global instance
auto_promotion_manager = AutoPromotionManager()
