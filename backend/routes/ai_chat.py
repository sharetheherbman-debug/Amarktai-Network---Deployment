"""
AI Super Intelligence Chat Router
Real-time AI chat with action confirmation and tool routing
"""

from fastapi import APIRouter, HTTPException, Depends, Body
from datetime import datetime, timezone
from typing import Optional, List, Dict
import logging
import json

from auth import get_current_user
import database as db
from ai_super_brain import AISuperBrain
from engines.trade_budget_manager import trade_budget_manager
from websocket_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["AI Chat"])

ai_brain = AISuperBrain()

# Action confirmation tokens storage (in production, use Redis)
confirmation_tokens = {}


class AIActionRouter:
    """Routes AI actions to appropriate system functions"""
    
    @staticmethod
    async def get_system_state(user_id: str) -> Dict:
        """Get comprehensive system state for AI context"""
        # Get bots
        bots = await db.bots_collection.find(
            {"user_id": user_id},
            {"_id": 0}
        ).to_list(1000)
        
        # Get system modes
        modes = await db.system_modes_collection.find_one(
            {"user_id": user_id},
            {"_id": 0}
        )
        
        # Get recent trades
        recent_trades = await db.trades_collection.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("timestamp", -1).limit(10).to_list(10)
        
        # Get wallet summary
        total_capital = sum(bot.get('current_capital', 0) for bot in bots)
        total_profit = sum(bot.get('total_profit', 0) for bot in bots)
        
        # Get budget status
        budget_status = await trade_budget_manager.get_all_exchanges_budget_report()
        
        return {
            "bots": {
                "total": len(bots),
                "active": len([b for b in bots if b.get('status') == 'active']),
                "paused": len([b for b in bots if b.get('status') == 'paused']),
                "stopped": len([b for b in bots if b.get('status') == 'stopped'])
            },
            "capital": {
                "total": round(total_capital, 2),
                "total_profit": round(total_profit, 2)
            },
            "recent_performance": {
                "recent_trades_count": len(recent_trades),
                "recent_pnl": round(sum(t.get('profit_loss', 0) for t in recent_trades), 2)
            },
            "system_modes": modes or {},
            "budget_status": budget_status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    @staticmethod
    async def execute_action(action: str, params: Dict, user_id: str) -> Dict:
        """Execute an AI-requested action with appropriate permissions"""
        try:
            if action == "start_bot":
                bot_id = params.get('bot_id')
                result = await db.bots_collection.update_one(
                    {"id": bot_id, "user_id": user_id},
                    {"$set": {"status": "active"}}
                )
                return {"success": result.modified_count > 0, "action": "start_bot", "bot_id": bot_id}
            
            elif action == "pause_bot":
                bot_id = params.get('bot_id')
                reason = params.get('reason', 'AI recommendation')
                result = await db.bots_collection.update_one(
                    {"id": bot_id, "user_id": user_id},
                    {"$set": {
                        "status": "paused",
                        "pause_reason": reason,
                        "paused_by_system": True
                    }}
                )
                return {"success": result.modified_count > 0, "action": "pause_bot", "bot_id": bot_id}
            
            elif action == "stop_bot":
                bot_id = params.get('bot_id')
                result = await db.bots_collection.update_one(
                    {"id": bot_id, "user_id": user_id},
                    {"$set": {"status": "stopped"}}
                )
                return {"success": result.modified_count > 0, "action": "stop_bot", "bot_id": bot_id}
            
            elif action == "emergency_stop":
                result = await db.system_modes_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"emergencyStop": True}},
                    upsert=True
                )
                # Pause all bots
                await db.bots_collection.update_many(
                    {"user_id": user_id, "status": "active"},
                    {"$set": {
                        "status": "paused",
                        "pause_reason": "Emergency stop activated by AI",
                        "paused_by_system": True
                    }}
                )
                return {"success": True, "action": "emergency_stop"}
            
            elif action == "get_limits":
                limits = await trade_budget_manager.get_all_exchanges_budget_report()
                return {"success": True, "action": "get_limits", "data": limits}
            
            elif action == "get_performance_graph":
                # Return data for graphs
                from routes.analytics_api import get_pnl_timeseries
                # This would need to be called differently, but showing the concept
                return {"success": True, "action": "get_performance_graph", "info": "Use /api/analytics/pnl_timeseries"}
            
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        
        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            return {"success": False, "error": str(e)}


action_router = AIActionRouter()


@router.post("/chat")
async def ai_chat(
    message: Dict = Body(...),
    user_id: str = Depends(get_current_user)
):
    """AI chat endpoint with action routing and confirmation
    
    Body:
        {
            "content": "user message",
            "request_action": false,  # if true, AI can propose actions
            "confirmation_token": null  # for confirming dangerous actions
        }
    """
    try:
        content = message.get('content', '')
        request_action = message.get('request_action', False)
        confirmation_token = message.get('confirmation_token')
        
        # Save user message
        user_msg = {
            "user_id": user_id,
            "role": "user",
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await db.chat_messages_collection.insert_one(user_msg)
        
        # Get system state for AI context
        system_state = await action_router.get_system_state(user_id)
        
        # Check if this is a confirmation for a dangerous action
        if confirmation_token and confirmation_token in confirmation_tokens:
            action_data = confirmation_tokens[confirmation_token]
            
            # Verify it's for this user
            if action_data['user_id'] == user_id:
                # Execute the confirmed action
                result = await action_router.execute_action(
                    action_data['action'],
                    action_data['params'],
                    user_id
                )
                
                # Remove token
                del confirmation_tokens[confirmation_token]
                
                ai_response = f"Action confirmed and executed: {action_data['action']}. Result: {result}"
                
                # Send WebSocket notification
                await manager.send_message(user_id, {
                    "type": "ai_action_executed",
                    "action": action_data['action'],
                    "result": result
                })
            else:
                ai_response = "Invalid confirmation token or unauthorized."
        else:
            # Generate AI response with OpenAI
            try:
                import openai
                import os
                
                openai.api_key = os.getenv('OPENAI_API_KEY', '')
                
                if not openai.api_key:
                    ai_response = "AI service not configured. Please set OPENAI_API_KEY."
                else:
                    # Prepare context for AI
                    context = f"""You are an AI trading assistant for the Amarktai Network.
                    
Current System State:
- Total Bots: {system_state['bots']['total']} (Active: {system_state['bots']['active']}, Paused: {system_state['bots']['paused']})
- Total Capital: R{system_state['capital']['total']}
- Total Profit: R{system_state['capital']['total_profit']}
- Recent Performance: {system_state['recent_performance']['recent_trades_count']} trades, R{system_state['recent_performance']['recent_pnl']} PnL

User Question: {content}

Available Actions (if requested):
- start_bot: Start a paused bot
- pause_bot: Pause a running bot
- stop_bot: Stop a bot permanently
- emergency_stop: CRITICAL - Stop all trading immediately
- get_limits: Show trade budget limits
- get_performance_graph: Get performance data

Instructions:
- Be helpful and explain the system state clearly
- If user asks for an action, explain what it will do
- For dangerous actions (emergency_stop, stop_bot), require explicit confirmation
- Provide recommendations based on performance data
"""
                    
                    response = openai.chat.completions.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": context},
                            {"role": "user", "content": content}
                        ],
                        max_tokens=500,
                        temperature=0.7
                    )
                    
                    ai_response = response.choices[0].message.content
                    
                    # Check if AI recommends an action
                    if request_action and any(keyword in content.lower() for keyword in ['start', 'pause', 'stop', 'emergency']):
                        # Detect action intent
                        action_detected = None
                        params = {}
                        
                        if 'emergency' in content.lower() and 'stop' in content.lower():
                            action_detected = 'emergency_stop'
                            requires_confirmation = True
                        elif 'pause' in content.lower():
                            action_detected = 'pause_bot'
                            requires_confirmation = False
                        # Add more action detection logic...
                        
                        if action_detected:
                            if requires_confirmation:
                                # Generate confirmation token
                                import uuid
                                token = str(uuid.uuid4())
                                confirmation_tokens[token] = {
                                    "user_id": user_id,
                                    "action": action_detected,
                                    "params": params,
                                    "created_at": datetime.now(timezone.utc).isoformat()
                                }
                                
                                ai_response += f"\n\n⚠️ **This is a dangerous action that requires confirmation.**\n"
                                ai_response += f"To proceed, reply with confirmation token: `{token}`"
                            else:
                                # Safe action - execute immediately
                                result = await action_router.execute_action(action_detected, params, user_id)
                                ai_response += f"\n\n✅ Action executed: {result}"
            
            except Exception as e:
                logger.error(f"OpenAI API error: {e}")
                ai_response = "I'm having trouble connecting to my AI services. Please try again."
        
        # Save AI response
        ai_msg = {
            "user_id": user_id,
            "role": "assistant",
            "content": ai_response,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await db.chat_messages_collection.insert_one(ai_msg)
        
        # Send real-time update
        await manager.send_message(user_id, {
            "type": "ai_chat_message",
            "message": ai_response
        })
        
        return {
            "role": "assistant",
            "content": ai_response,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system_state": system_state
        }
    
    except Exception as e:
        logger.error(f"AI chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/history")
async def get_chat_history(
    limit: int = 50,
    user_id: str = Depends(get_current_user)
):
    """Get chat history for user"""
    try:
        messages = await db.chat_messages_collection.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit).to_list(limit)
        
        # Reverse to get chronological order
        messages.reverse()
        
        return {
            "messages": messages,
            "count": len(messages),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    except Exception as e:
        logger.error(f"Get chat history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/chat/history")
async def clear_chat_history(user_id: str = Depends(get_current_user)):
    """Clear chat history for user"""
    try:
        result = await db.chat_messages_collection.delete_many({"user_id": user_id})
        
        return {
            "success": True,
            "deleted_count": result.deleted_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    except Exception as e:
        logger.error(f"Clear chat history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/action/execute")
async def execute_ai_action(
    action_data: Dict = Body(...),
    user_id: str = Depends(get_current_user)
):
    """Execute an AI action directly (for frontend buttons)
    
    Body:
        {
            "action": "start_bot" | "pause_bot" | "stop_bot" | "emergency_stop" | "get_limits",
            "params": {"bot_id": "...", ...},
            "require_2fa": false  # if true, requires 2FA code
        }
    """
    try:
        action = action_data.get('action')
        params = action_data.get('params', {})
        require_2fa = action_data.get('require_2fa', False)
        
        # Check if 2FA is required
        if require_2fa:
            user = await db.users_collection.find_one({"id": user_id}, {"_id": 0})
            if user and user.get('two_factor_enabled'):
                otp_code = action_data.get('otp_code')
                if not otp_code:
                    return {
                        "success": False,
                        "error": "2FA code required",
                        "require_2fa": True
                    }
                
                # Verify 2FA
                import pyotp
                totp = pyotp.TOTP(user.get('two_factor_secret'))
                if not totp.verify(otp_code, valid_window=1):
                    return {
                        "success": False,
                        "error": "Invalid 2FA code"
                    }
        
        # Execute action
        result = await action_router.execute_action(action, params, user_id)
        
        # Log action
        logger.info(f"User {user_id[:8]} executed AI action: {action}")
        
        return result
    
    except Exception as e:
        logger.error(f"Execute AI action error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
