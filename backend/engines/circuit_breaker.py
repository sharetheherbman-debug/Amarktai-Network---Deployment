"""
Circuit Breaker System - LEDGER-FIRST
Monitors drawdowns and automatically pauses/quarantines bots/system
Uses immutable ledger data as single source of truth
"""

import asyncio
from typing import Dict, Tuple
from datetime import datetime, timezone, timedelta
import logging

import database as db
from config import MAX_DRAWDOWN_PERCENT

logger = logging.getLogger(__name__)

class CircuitBreaker:
    def __init__(self):
        self.max_bot_drawdown = MAX_DRAWDOWN_PERCENT  # 20% default
        self.max_daily_loss_percent = 0.10  # 10% per day
        self.max_global_drawdown = 0.15  # 15% total system
        self.max_consecutive_losses = 5  # 5 losses in a row
        self.max_errors_per_hour = 10  # 10 errors/hour
        
    async def check_bot_drawdown_ledger(self, user_id: str, bot_id: str, ledger_service) -> Tuple[bool, str]:
        """Check if bot has exceeded drawdown limits - LEDGER-BASED"""
        try:
            # Get drawdown from ledger (single source of truth)
            current_dd, max_dd = await ledger_service.compute_drawdown(user_id, bot_id=bot_id)
            
            if current_dd > self.max_bot_drawdown:
                return True, f"Drawdown {current_dd*100:.1f}% exceeds limit {self.max_bot_drawdown*100:.0f}%"
            
            return False, "OK"
            
        except Exception as e:
            logger.error(f"Ledger-based drawdown check error: {e}")
            # Fallback to bot-based check
            return await self._check_bot_drawdown_fallback(bot_id)
    
    async def _check_bot_drawdown_fallback(self, bot_id: str) -> Tuple[bool, str]:
        """Fallback to bot-based drawdown check"""
        try:
            bot = await db.bots_collection.find_one({"id": bot_id}, {"_id": 0})
            if not bot:
                return False, "Bot not found"
            
            initial_capital = bot.get('initial_capital', 1000)
            current_capital = bot.get('current_capital', 1000)
            
            # Calculate total drawdown
            total_drawdown_pct = (initial_capital - current_capital) / initial_capital if initial_capital > 0 else 0
            
            if total_drawdown_pct > self.max_bot_drawdown:
                return True, f"Total drawdown {total_drawdown_pct*100:.1f}% exceeds limit {self.max_bot_drawdown*100:.0f}%"
            
            return False, "OK"
            
        except Exception as e:
            logger.error(f"Drawdown check error: {e}")
            return False, str(e)
    
    async def check_daily_loss_ledger(self, user_id: str, bot_id: str, ledger_service) -> Tuple[bool, str]:
        """Check if bot has exceeded daily loss limit - LEDGER-BASED"""
        try:
            # Get today's profit from ledger
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            
            series = await ledger_service.profit_series(
                user_id,
                period="daily",
                limit=1,
                bot_id=bot_id,
                since=today_start
            )
            
            if not series or not series.get("values"):
                return False, "OK"
            
            daily_pnl = series["values"][0]
            
            # Get initial capital from ledger
            initial_capital = await ledger_service.compute_funded_capital(user_id, bot_id=bot_id)
            
            if initial_capital == 0:
                return False, "OK"
            
            daily_loss_pct = abs(daily_pnl) / initial_capital if daily_pnl < 0 else 0
            
            if daily_loss_pct > self.max_daily_loss_percent:
                return True, f"Daily loss {daily_loss_pct*100:.1f}% exceeds limit {self.max_daily_loss_percent*100:.0f}%"
            
            return False, "OK"
            
        except Exception as e:
            logger.error(f"Daily loss check error: {e}")
            return False, str(e)
    
    async def check_consecutive_losses_ledger(self, user_id: str, bot_id: str, ledger_service) -> Tuple[bool, str]:
        """Check for consecutive losses - LEDGER-BASED"""
        try:
            # Get recent fills from ledger
            recent_fills = await ledger_service.get_fills(
                user_id,
                bot_id=bot_id,
                limit=self.max_consecutive_losses * 2  # Get enough to detect pattern
            )
            
            if not recent_fills:
                return False, "OK"
            
            # Count consecutive losses (simplified - assumes alternating buys/sells)
            consecutive_losses = 0
            for i in range(0, len(recent_fills) - 1, 2):
                if i + 1 >= len(recent_fills):
                    break
                
                buy_fill = recent_fills[i] if recent_fills[i]["side"] == "buy" else recent_fills[i+1]
                sell_fill = recent_fills[i+1] if recent_fills[i+1]["side"] == "sell" else recent_fills[i]
                
                # Check if this was a loss
                if sell_fill["price"] < buy_fill["price"]:
                    consecutive_losses += 1
                else:
                    consecutive_losses = 0  # Reset on win
                
                if consecutive_losses >= self.max_consecutive_losses:
                    return True, f"Consecutive losses: {consecutive_losses}"
            
            return False, "OK"
            
        except Exception as e:
            logger.error(f"Consecutive losses check error: {e}")
            return False, str(e)
    
    async def check_error_rate(self, user_id: str, bot_id: str) -> Tuple[bool, str]:
        """Check error rate from alerts"""
        try:
            one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
            
            error_count = await db.alerts_collection.count_documents({
                "user_id": user_id,
                "bot_id": bot_id,
                "severity": {"$in": ["error", "critical"]},
                "timestamp": {"$gte": one_hour_ago}
            })
            
            if error_count >= self.max_errors_per_hour:
                return True, f"Error rate: {error_count}/hour exceeds limit {self.max_errors_per_hour}"
            
            return False, "OK"
            
        except Exception as e:
            logger.error(f"Error rate check error: {e}")
            return False, str(e)
    
    async def check_global_drawdown(self, user_id: str) -> Tuple[bool, str]:
        """Check if total system drawdown exceeds limit"""
        try:
            bots = await db.bots_collection.find(
                {"user_id": user_id},
                {"_id": 0}
            ).to_list(1000)
            
            total_initial = sum(b.get('initial_capital', 0) for b in bots)
            total_current = sum(b.get('current_capital', 0) for b in bots)
            
            if total_initial == 0:
                return False, "OK"
            
            global_drawdown_pct = (total_initial - total_current) / total_initial
            
            if global_drawdown_pct > self.max_global_drawdown:
                return True, f"Global drawdown {global_drawdown_pct*100:.1f}% exceeds {self.max_global_drawdown*100:.0f}%"
            
            return False, "OK"
            
        except Exception as e:
            logger.error(f"Global drawdown check error: {e}")
            return False, str(e)
    
    async def trigger_bot_quarantine(self, bot_id: str, reason: str):
        """QUARANTINE a bot due to circuit breaker (requires manual reset)"""
        try:
            bot = await db.bots_collection.find_one({"id": bot_id}, {"_id": 0})
            if not bot:
                return
            
            # QUARANTINE bot (stricter than pause)
            await db.bots_collection.update_one(
                {"id": bot_id},
                {"$set": {
                    "status": "quarantined",
                    "quarantine_reason": f"Circuit breaker: {reason}",
                    "quarantined_at": datetime.now(timezone.utc).isoformat(),
                    "requires_manual_reset": True
                }}
            )
            
            # Log to rogue detections
            await db.rogue_detections_collection.insert_one({
                "user_id": bot['user_id'],
                "bot_id": bot_id,
                "bot_name": bot['name'],
                "type": "circuit_breaker",
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action_taken": "quarantined"
            })
            
            # Create critical alert
            await db.alerts_collection.insert_one({
                "user_id": bot['user_id'],
                "type": "circuit_breaker",
                "severity": "critical",
                "message": f"🚨 CIRCUIT BREAKER: {bot['name']} QUARANTINED - {reason}. Manual reset required.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dismissed": False,
                "requires_action": True
            })
            
            logger.critical(f"🚨 Circuit breaker triggered - BOT QUARANTINED: {bot['name']} - {reason}")
            
        except Exception as e:
            logger.error(f"Trigger quarantine error: {e}")
    
    async def trigger_bot_pause(self, bot_id: str, reason: str):
        """Pause a bot due to circuit breaker"""
        try:
            bot = await db.bots_collection.find_one({"id": bot_id}, {"_id": 0})
            if not bot:
                return
            
            # Pause bot
            await db.bots_collection.update_one(
                {"id": bot_id},
                {"$set": {
                    "status": "paused",
                    "paused_reason": f"Circuit breaker: {reason}",
                    "paused_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            
            # Log to rogue detections
            await db.rogue_detections_collection.insert_one({
                "user_id": bot['user_id'],
                "bot_id": bot_id,
                "bot_name": bot['name'],
                "type": "circuit_breaker",
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action_taken": "paused"
            })
            
            # Create alert
            await db.alerts_collection.insert_one({
                "user_id": bot['user_id'],
                "type": "circuit_breaker",
                "severity": "critical",
                "message": f"🚨 CIRCUIT BREAKER: {bot['name']} paused - {reason}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dismissed": False
            })
            
            logger.warning(f"🚨 Circuit breaker triggered: {bot['name']} - {reason}")
            
        except Exception as e:
            logger.error(f"Trigger pause error: {e}")
    
    async def trigger_emergency_stop(self, user_id: str, reason: str):
        """Trigger system-wide emergency stop"""
        try:
            # Enable emergency stop
            await db.system_modes_collection.update_one(
                {"user_id": user_id},
                {"$set": {
                    "emergencyStop": True,
                    "emergency_reason": reason,
                    "emergency_at": datetime.now(timezone.utc).isoformat()
                }},
                upsert=True
            )
            
            # Create critical alert
            await db.alerts_collection.insert_one({
                "user_id": user_id,
                "type": "emergency_stop",
                "severity": "critical",
                "message": f"🚨 EMERGENCY STOP ACTIVATED: {reason}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dismissed": False
            })
            
            logger.critical(f"🚨 EMERGENCY STOP: {reason}")
            
        except Exception as e:
            logger.error(f"Emergency stop trigger error: {e}")
    
    async def monitor_all_bots_ledger(self, user_id: str, ledger_service):
        """Monitor all bots for circuit breaker conditions - LEDGER-BASED"""
        try:
            # Check global drawdown first
            global_breach, global_reason = await self.check_global_drawdown(user_id)
            
            if global_breach:
                await self.trigger_emergency_stop(user_id, global_reason)
                return
            
            # Check individual bots
            bots = await db.bots_collection.find(
                {"user_id": user_id, "status": {"$in": ["active", "paused"]}},
                {"_id": 0}
            ).to_list(1000)
            
            for bot in bots:
                bot_id = bot['id']
                
                # Run all checks (ledger-based)
                checks = [
                    await self.check_bot_drawdown_ledger(user_id, bot_id, ledger_service),
                    await self.check_daily_loss_ledger(user_id, bot_id, ledger_service),
                    await self.check_consecutive_losses_ledger(user_id, bot_id, ledger_service),
                    await self.check_error_rate(user_id, bot_id)
                ]
                
                # Check if any breached
                for breach, reason in checks:
                    if breach:
                        # Critical breaches go to quarantine
                        if "drawdown" in reason.lower() or "consecutive" in reason.lower():
                            await self.trigger_bot_quarantine(bot_id, reason)
                        else:
                            await self.trigger_bot_pause(bot_id, reason)
                        break  # Only one action per bot
            
        except Exception as e:
            logger.error(f"Monitor bots error: {e}")

# Global instance
circuit_breaker = CircuitBreaker()
