"""
AI Command Router - Chat-based Command Issuance System

Allows users to issue key backend actions via chat interface:
- Bot lifecycle management (start, pause, resume, stop)
- Emergency stop and status checks
- Portfolio summary display
- Profits series display
- Triggering reinvest cycles (paper trading only)
- Sending test reports (admin-only)

Requires confirmation for trading-related commands.
Returns real-time feedback to the UI.
"""

import re
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class AICommandRouter:
    """Routes AI chat messages to appropriate backend commands"""
    
    def __init__(self, db):
        self.db = db
        self.bots_collection = db["bots"]
        self.users_collection = db["users"]
        self.system_modes_collection = db["system_modes"]
        self.trades_collection = db["trades"]
        
        # Command patterns with regex
        self.command_patterns = {
            # Bot lifecycle
            "start_bot": r"(start|activate|enable)\s+bot\s+(.+)",
            "pause_bot": r"(pause|stop|disable)\s+bot\s+(.+)",
            "resume_bot": r"(resume|restart|unpause)\s+bot\s+(.+)",
            "stop_bot": r"(terminate|delete|remove)\s+bot\s+(.+)",
            "pause_all": r"(pause|stop)\s+all\s+bots",
            "resume_all": r"(resume|start)\s+all\s+bots",
            
            # Emergency
            "emergency_stop": r"emergency\s+stop|halt\s+all|stop\s+everything",
            
            # Status
            "bot_status": r"(status|info)\s+(?:of\s+)?bot\s+(.+)",
            "portfolio_summary": r"(show|display|get)\s+(portfolio|summary|balance)",
            "profits": r"(show|display|get)\s+profit",
            
            # Reinvest (paper only)
            "reinvest": r"reinvest|trigger\s+reinvest|run\s+reinvest",
            
            # Admin
            "send_test_report": r"send\s+test\s+report|test\s+email|test\s+report",
        }
        
        # Commands that require confirmation
        self.requires_confirmation = {
            "start_bot", "stop_bot", "emergency_stop", "reinvest"
        }
        
        # Admin-only commands
        self.admin_only = {"send_test_report"}
    
    async def parse_and_execute(
        self,
        user_id: str,
        message: str,
        confirmed: bool = False,
        is_admin: bool = False
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Parse message and execute command if detected
        
        Args:
            user_id: User ID
            message: Chat message
            confirmed: Whether user has confirmed the action
            is_admin: Whether user is admin
            
        Returns:
            (is_command, result_dict)
        """
        message_lower = message.lower().strip()
        
        # Try to match command patterns
        for command_name, pattern in self.command_patterns.items():
            match = re.search(pattern, message_lower)
            if match:
                # Check admin permission
                if command_name in self.admin_only and not is_admin:
                    return True, {
                        "success": False,
                        "command": command_name,
                        "message": "❌ This command requires admin privileges",
                        "error": "permission_denied"
                    }
                
                # Check if confirmation required
                if command_name in self.requires_confirmation and not confirmed:
                    return True, {
                        "success": False,
                        "command": command_name,
                        "message": f"⚠️ This action requires confirmation. Please confirm to proceed.",
                        "requires_confirmation": True,
                        "match_groups": match.groups()
                    }
                
                # Execute command
                result = await self._execute_command(
                    user_id, command_name, match.groups(), is_admin
                )
                return True, result
        
        # Not a command
        return False, {}
    
    async def _execute_command(
        self,
        user_id: str,
        command: str,
        match_groups: tuple,
        is_admin: bool
    ) -> Dict[str, Any]:
        """Execute the parsed command"""
        try:
            if command == "start_bot":
                return await self._start_bot(user_id, match_groups[1])
            
            elif command == "pause_bot":
                return await self._pause_bot(user_id, match_groups[1])
            
            elif command == "resume_bot":
                return await self._resume_bot(user_id, match_groups[1])
            
            elif command == "stop_bot":
                return await self._stop_bot(user_id, match_groups[1])
            
            elif command == "pause_all":
                return await self._pause_all_bots(user_id)
            
            elif command == "resume_all":
                return await self._resume_all_bots(user_id)
            
            elif command == "emergency_stop":
                return await self._emergency_stop(user_id)
            
            elif command == "bot_status":
                return await self._get_bot_status(user_id, match_groups[1])
            
            elif command == "portfolio_summary":
                return await self._get_portfolio_summary(user_id)
            
            elif command == "profits":
                return await self._get_profits(user_id)
            
            elif command == "reinvest":
                return await self._trigger_reinvest(user_id)
            
            elif command == "send_test_report":
                return await self._send_test_report(user_id, is_admin)
            
            else:
                return {
                    "success": False,
                    "command": command,
                    "message": "❌ Unknown command",
                    "error": "unknown_command"
                }
        
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return {
                "success": False,
                "command": command,
                "message": f"❌ Error executing command: {str(e)}",
                "error": "execution_error"
            }
    
    async def _find_bot_by_name(self, user_id: str, bot_name: str):
        """Find bot by name or ID"""
        # Try exact ID match first
        bot = await self.bots_collection.find_one(
            {"user_id": user_id, "id": bot_name},
            {"_id": 0}
        )
        if bot:
            return bot
        
        # Try name match (case-insensitive)
        bot = await self.bots_collection.find_one(
            {"user_id": user_id, "name": {"$regex": f"^{bot_name}$", "$options": "i"}},
            {"_id": 0}
        )
        return bot
    
    async def _start_bot(self, user_id: str, bot_identifier: str) -> Dict[str, Any]:
        """Start a bot"""
        bot = await self._find_bot_by_name(user_id, bot_identifier)
        if not bot:
            return {
                "success": False,
                "command": "start_bot",
                "message": f"❌ Bot '{bot_identifier}' not found"
            }
        
        # Update bot status
        await self.bots_collection.update_one(
            {"id": bot["id"]},
            {"$set": {"status": "active"}}
        )
        
        return {
            "success": True,
            "command": "start_bot",
            "message": f"✅ Bot '{bot['name']}' started successfully",
            "bot_id": bot["id"],
            "bot_name": bot["name"]
        }
    
    async def _pause_bot(self, user_id: str, bot_identifier: str) -> Dict[str, Any]:
        """Pause a bot"""
        bot = await self._find_bot_by_name(user_id, bot_identifier)
        if not bot:
            return {
                "success": False,
                "command": "pause_bot",
                "message": f"❌ Bot '{bot_identifier}' not found"
            }
        
        await self.bots_collection.update_one(
            {"id": bot["id"]},
            {"$set": {"status": "paused"}}
        )
        
        return {
            "success": True,
            "command": "pause_bot",
            "message": f"⏸️ Bot '{bot['name']}' paused",
            "bot_id": bot["id"],
            "bot_name": bot["name"]
        }
    
    async def _resume_bot(self, user_id: str, bot_identifier: str) -> Dict[str, Any]:
        """Resume a bot"""
        bot = await self._find_bot_by_name(user_id, bot_identifier)
        if not bot:
            return {
                "success": False,
                "command": "resume_bot",
                "message": f"❌ Bot '{bot_identifier}' not found"
            }
        
        await self.bots_collection.update_one(
            {"id": bot["id"]},
            {"$set": {"status": "active"}}
        )
        
        return {
            "success": True,
            "command": "resume_bot",
            "message": f"▶️ Bot '{bot['name']}' resumed",
            "bot_id": bot["id"],
            "bot_name": bot["name"]
        }
    
    async def _stop_bot(self, user_id: str, bot_identifier: str) -> Dict[str, Any]:
        """Stop/delete a bot"""
        bot = await self._find_bot_by_name(user_id, bot_identifier)
        if not bot:
            return {
                "success": False,
                "command": "stop_bot",
                "message": f"❌ Bot '{bot_identifier}' not found"
            }
        
        await self.bots_collection.update_one(
            {"id": bot["id"]},
            {"$set": {"status": "stopped"}}
        )
        
        return {
            "success": True,
            "command": "stop_bot",
            "message": f"🛑 Bot '{bot['name']}' stopped",
            "bot_id": bot["id"],
            "bot_name": bot["name"]
        }
    
    async def _pause_all_bots(self, user_id: str) -> Dict[str, Any]:
        """Pause all user's bots"""
        result = await self.bots_collection.update_many(
            {"user_id": user_id, "status": "active"},
            {"$set": {"status": "paused"}}
        )
        
        return {
            "success": True,
            "command": "pause_all",
            "message": f"⏸️ Paused {result.modified_count} bot(s)",
            "count": result.modified_count
        }
    
    async def _resume_all_bots(self, user_id: str) -> Dict[str, Any]:
        """Resume all user's bots"""
        result = await self.bots_collection.update_many(
            {"user_id": user_id, "status": "paused"},
            {"$set": {"status": "active"}}
        )
        
        return {
            "success": True,
            "command": "resume_all",
            "message": f"▶️ Resumed {result.modified_count} bot(s)",
            "count": result.modified_count
        }
    
    async def _emergency_stop(self, user_id: str) -> Dict[str, Any]:
        """Emergency stop - pause all bots and disable trading"""
        # Pause all bots
        await self.bots_collection.update_many(
            {"user_id": user_id},
            {"$set": {"status": "paused"}}
        )
        
        # Disable trading modes
        await self.system_modes_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "paperTrading": False,
                    "liveTrading": False,
                    "autopilot": False,
                    "emergency_stop_triggered": True,
                    "emergency_stop_at": datetime.now(timezone.utc).isoformat()
                }
            },
            upsert=True
        )
        
        return {
            "success": True,
            "command": "emergency_stop",
            "message": "🚨 EMERGENCY STOP ACTIVATED - All trading halted",
            "details": "All bots paused, trading modes disabled"
        }
    
    async def _get_bot_status(self, user_id: str, bot_identifier: str) -> Dict[str, Any]:
        """Get bot status"""
        bot = await self._find_bot_by_name(user_id, bot_identifier)
        if not bot:
            return {
                "success": False,
                "command": "bot_status",
                "message": f"❌ Bot '{bot_identifier}' not found"
            }
        
        return {
            "success": True,
            "command": "bot_status",
            "message": f"📊 Bot '{bot['name']}' Status",
            "bot": {
                "name": bot.get("name"),
                "status": bot.get("status"),
                "trading_mode": bot.get("trading_mode", "paper"),
                "exchange": bot.get("exchange"),
                "risk_mode": bot.get("risk_mode"),
                "current_capital": round(bot.get("current_capital", 0), 2),
                "total_profit": round(bot.get("total_profit", 0), 2),
                "trades_count": bot.get("trades_count", 0),
                "win_rate": round(bot.get("win_rate", 0), 2)
            }
        }
    
    async def _get_portfolio_summary(self, user_id: str) -> Dict[str, Any]:
        """Get portfolio summary from ledger"""
        try:
            from services.ledger_service import get_ledger_service
            ledger = get_ledger_service(self.db)
            
            equity = await ledger.compute_equity(user_id)
            realized_pnl = await ledger.compute_realized_pnl(user_id)
            fees_total = await ledger.compute_fees_paid(user_id)
            current_dd, max_dd = await ledger.compute_drawdown(user_id)
            
            # Get bot counts
            bots = await self.bots_collection.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
            active_count = len([b for b in bots if b.get("status") == "active"])
            
            return {
                "success": True,
                "command": "portfolio_summary",
                "message": "📊 Portfolio Summary",
                "portfolio": {
                    "equity": round(equity, 2),
                    "realized_pnl": round(realized_pnl, 2),
                    "fees_total": round(fees_total, 2),
                    "net_pnl": round(realized_pnl - fees_total, 2),
                    "drawdown_current": round(current_dd * 100, 2),
                    "drawdown_max": round(max_dd * 100, 2),
                    "total_bots": len(bots),
                    "active_bots": active_count
                }
            }
        except Exception as e:
            logger.error(f"Portfolio summary error: {e}")
            # Fallback to bot-based calculation
            bots = await self.bots_collection.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
            total_capital = sum(b.get("current_capital", 0) for b in bots)
            total_initial = sum(b.get("initial_capital", 0) for b in bots)
            total_profit = total_capital - total_initial
            
            return {
                "success": True,
                "command": "portfolio_summary",
                "message": "📊 Portfolio Summary (from bots)",
                "portfolio": {
                    "total_capital": round(total_capital, 2),
                    "total_profit": round(total_profit, 2),
                    "bot_count": len(bots),
                    "data_source": "bots"
                }
            }
    
    async def _get_profits(self, user_id: str) -> Dict[str, Any]:
        """Get profits series from ledger"""
        try:
            from services.ledger_service import get_ledger_service
            ledger = get_ledger_service(self.db)
            
            series = await ledger.profit_series(user_id, period="daily", limit=7)
            
            return {
                "success": True,
                "command": "profits",
                "message": "💰 Profit Series (Last 7 Days)",
                "profits": {
                    "labels": series["labels"],
                    "values": series["values"],
                    "total": round(series["total"], 2)
                }
            }
        except Exception as e:
            logger.error(f"Profits error: {e}")
            return {
                "success": False,
                "command": "profits",
                "message": "❌ Error retrieving profits data",
                "error": str(e)
            }
    
    async def _trigger_reinvest(self, user_id: str) -> Dict[str, Any]:
        """Trigger reinvestment cycle (paper only)"""
        # Check if paper trading mode
        modes = await self.system_modes_collection.find_one(
            {"user_id": user_id},
            {"_id": 0}
        )
        
        if modes and modes.get("liveTrading"):
            return {
                "success": False,
                "command": "reinvest",
                "message": "❌ Reinvest command only available in paper trading mode",
                "error": "live_mode_not_allowed"
            }
        
        try:
            from engines.capital_allocator import capital_allocator
            result = await capital_allocator.reinvest_daily_profits(user_id)
            
            return {
                "success": True,
                "command": "reinvest",
                "message": "✅ Reinvestment cycle triggered",
                "result": result
            }
        except Exception as e:
            logger.error(f"Reinvest error: {e}")
            return {
                "success": False,
                "command": "reinvest",
                "message": f"❌ Reinvestment failed: {str(e)}",
                "error": "reinvest_error"
            }
    
    async def _send_test_report(self, user_id: str, is_admin: bool) -> Dict[str, Any]:
        """Send test email report (admin only)"""
        if not is_admin:
            return {
                "success": False,
                "command": "send_test_report",
                "message": "❌ Admin privileges required",
                "error": "permission_denied"
            }
        
        try:
            from routes.daily_report import daily_report_service
            
            user = await self.users_collection.find_one(
                {"id": user_id},
                {"_id": 0}
            )
            
            if not user or not user.get("email"):
                return {
                    "success": False,
                    "command": "send_test_report",
                    "message": "❌ User email not found"
                }
            
            # Send test report
            success = await daily_report_service.send_report_to_user(user_id)
            
            if success:
                return {
                    "success": True,
                    "command": "send_test_report",
                    "message": f"✅ Test report sent to {user['email']}"
                }
            else:
                return {
                    "success": False,
                    "command": "send_test_report",
                    "message": "❌ Failed to send report (SMTP not configured?)"
                }
        
        except Exception as e:
            logger.error(f"Send test report error: {e}")
            return {
                "success": False,
                "command": "send_test_report",
                "message": f"❌ Error sending report: {str(e)}",
                "error": "send_error"
            }


def get_ai_command_router(db):
    """Factory function to get command router"""
    return AICommandRouter(db)
