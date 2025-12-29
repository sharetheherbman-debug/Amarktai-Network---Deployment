"""
Funding Plan Manager
Creates and manages funding plans when bots need capital on exchanges
"""

import asyncio
from typing import Dict, List
from datetime import datetime, timezone
from uuid import uuid4
import logging

import database as db
from engines.wallet_manager import wallet_manager
from engines.ai_model_router import ai_model_router

logger = logging.getLogger(__name__)

# Create funding_plans collection
funding_plans_collection = db.funding_plans

class FundingPlanManager:
    """Manages cross-exchange funding requirements"""
    
    def __init__(self):
        self.plan_types = ['bot_creation', 'capital_reallocation', 'autopilot_spawning']
    
    async def create_funding_plan(self, user_id: str, target_exchange: str, 
                                  required_amount: float, reason: str, 
                                  bot_name: str = None) -> Dict:
        """
        Create a funding plan when capital is needed
        
        Args:
            user_id: User ID
            target_exchange: Exchange needing funds (binance, kucoin, etc.)
            required_amount: Amount needed in ZAR
            reason: Why funds are needed (bot_creation, reallocation, etc.)
            bot_name: Name of bot if for bot creation
        
        Returns:
            Funding plan with instructions
        """
        try:
            # Get master wallet balance
            master_balance = await wallet_manager.get_master_balance(user_id)
            
            available_in_master = master_balance.get('total_zar', 0)
            
            # Create plan ID
            plan_id = str(uuid4())
            
            # Determine funding source
            if available_in_master >= required_amount:
                # Sufficient in master wallet - can transfer
                source = "master_luno_wallet"
                status = "ready_to_execute"
                can_auto_execute = False  # Manual for now
            else:
                # Need to deposit to master wallet first
                source = "external_deposit_required"
                status = "awaiting_deposit"
                can_auto_execute = False
            
            # Generate AI-friendly message
            ai_message = await self._generate_funding_message(
                target_exchange,
                required_amount,
                available_in_master,
                reason,
                bot_name
            )
            
            # Create plan document
            plan = {
                "plan_id": plan_id,
                "user_id": user_id,
                "from_exchange": "luno" if source == "master_luno_wallet" else "external",
                "to_exchange": target_exchange,
                "asset": "ZAR",
                "amount_required": required_amount,
                "amount_available": available_in_master,
                "amount_deficit": max(0, required_amount - available_in_master),
                "reason": reason,
                "bot_name": bot_name,
                "status": status,
                "source": source,
                "can_auto_execute": can_auto_execute,
                "ai_message": ai_message,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "executed_at": None,
                "cancelled_at": None
            }
            
            # Store plan
            await funding_plans_collection.insert_one(plan)
            
            logger.info(f"📋 Created funding plan {plan_id[:8]} for {user_id[:8]}: R{required_amount} to {target_exchange}")
            
            return plan
            
        except Exception as e:
            logger.error(f"Create funding plan error: {e}")
            return {"error": str(e)}
    
    async def _generate_funding_message(self, target_exchange: str, 
                                       required_amount: float, 
                                       available: float, 
                                       reason: str, 
                                       bot_name: str) -> str:
        """Generate AI-friendly funding message"""
        
        try:
            if available >= required_amount:
                # Sufficient funds - just need transfer
                message = f"""
💰 **Funding Required for {target_exchange.capitalize()}**

You need R{required_amount:.2f} on {target_exchange.capitalize()} to {reason}.

✅ **Good news:** You have R{available:.2f} in your Luno master wallet.

**Next steps:**
1. Go to Wallet Hub
2. Click "Top Up {target_exchange.capitalize()}"
3. Transfer R{required_amount:.2f} from Luno to {target_exchange.capitalize()}

Or I can guide you through the transfer process.
"""
            else:
                deficit = required_amount - available
                message = f"""
💰 **Deposit Required**

You need R{required_amount:.2f} total to {reason} on {target_exchange.capitalize()}.

Current balance:
- Luno (Master): R{available:.2f}
- **Needed:** R{deficit:.2f} more

**Next steps:**
1. Deposit R{deficit:.2f} (or more) to your Luno wallet
2. Once deposited, transfer R{required_amount:.2f} to {target_exchange.capitalize()}
3. Then you can create the bot

I'll notify you once I detect the deposit.
"""
            
            return message.strip()
            
        except:
            # Fallback message
            return f"Please deposit R{required_amount:.2f} to {target_exchange.capitalize()} to continue."
    
    async def get_user_funding_plans(self, user_id: str, status: str = None) -> List[Dict]:
        """Get all funding plans for a user"""
        try:
            query = {"user_id": user_id}
            
            if status:
                query["status"] = status
            
            plans = await funding_plans_collection.find(
                query,
                {"_id": 0}
            ).sort("created_at", -1).limit(50).to_list(50)
            
            return plans
            
        except Exception as e:
            logger.error(f"Get funding plans error: {e}")
            return []
    
    async def get_funding_plan(self, plan_id: str) -> Dict:
        """Get specific funding plan"""
        try:
            plan = await funding_plans_collection.find_one(
                {"plan_id": plan_id},
                {"_id": 0}
            )
            
            return plan or {"error": "Plan not found"}
            
        except Exception as e:
            logger.error(f"Get funding plan error: {e}")
            return {"error": str(e)}
    
    async def cancel_funding_plan(self, plan_id: str) -> bool:
        """Cancel a funding plan"""
        try:
            await funding_plans_collection.update_one(
                {"plan_id": plan_id},
                {
                    "$set": {
                        "status": "cancelled",
                        "cancelled_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Cancel funding plan error: {e}")
            return False
    
    async def mark_plan_executed(self, plan_id: str) -> bool:
        """Mark funding plan as executed"""
        try:
            await funding_plans_collection.update_one(
                {"plan_id": plan_id},
                {
                    "$set": {
                        "status": "executed",
                        "executed_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Mark plan executed error: {e}")
            return False

# Global instance
funding_plan_manager = FundingPlanManager()
