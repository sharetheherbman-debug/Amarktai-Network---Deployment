"""
Wallet Hub API Endpoints
Provides balance information and funding plans
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict
import logging

from auth import get_current_user
from engines.wallet_manager import wallet_manager
from engines.funding_plan_manager import funding_plan_manager
from jobs.wallet_balance_monitor import wallet_balances_collection
import database as db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wallet", tags=["Wallet Hub"])

@router.get("/balances")
async def get_wallet_balances(user_id: str = Depends(get_current_user)):
    """Get all wallet balances for user"""
    try:
        
        # Get cached balances
        cached = await wallet_balances_collection.find_one(
            {"user_id": user_id},
            {"_id": 0}
        )
        
        if cached:
            # Normalize field names for frontend compatibility
            if cached.get('master_wallet'):
                mw = cached['master_wallet']
                cached['master_wallet'] = {
                    "total_zar": mw.get('total_zar', 0),
                    "btc_balance": mw.get('btc', mw.get('btc_balance', 0)),
                    "eth_balance": mw.get('eth', mw.get('eth_balance', 0)),
                    "xrp_balance": mw.get('xrp', mw.get('xrp_balance', 0)),
                    "exchange": mw.get('exchange', 'luno')
                }
            return cached
        
        # If no cached data, fetch fresh
        master_balance = await wallet_manager.get_master_balance(user_id)
        
        # Handle API key not configured case
        if master_balance.get('error'):
            normalized_master = {
                "total_zar": 0,
                "btc_balance": 0,
                "eth_balance": 0,
                "xrp_balance": 0,
                "exchange": "luno",
                "error": master_balance['error']
            }
        else:
            # Normalize master_balance field names for frontend
            normalized_master = {
                "total_zar": master_balance.get('total_zar', 0),
                "btc_balance": master_balance.get('btc', 0),
                "eth_balance": master_balance.get('eth', 0),
                "xrp_balance": master_balance.get('xrp', 0),
                "exchange": master_balance.get('exchange', 'luno')
            }
        
        # Get exchange balances (placeholder for now - will be populated by wallet monitor job)
        exchange_balances = {}
        
        return {
            "user_id": user_id,
            "master_wallet": normalized_master,
            "exchanges": exchange_balances,
            "timestamp": None,
            "last_updated": "just_now"
        }
        
    except Exception as e:
        import traceback
        logger.error(f"Get wallet balances error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/requirements")
async def get_capital_requirements(user_id: str = Depends(get_current_user)):
    """Get capital requirements per exchange based on active bots"""
    try:
        
        # Get all active bots
        bots = await db.bots_collection.find(
            {"user_id": user_id, "status": "active"},
            {"_id": 0}
        ).to_list(1000)
        
        # Calculate required capital per exchange
        requirements = {}
        
        for bot in bots:
            exchange = bot.get('exchange', 'unknown')
            capital = bot.get('current_capital', 0)
            
            if exchange not in requirements:
                requirements[exchange] = {
                    "required": 0,
                    "bots": 0,
                    "available": 0,
                    "surplus_deficit": 0,
                    "health": "unknown"
                }
            
            requirements[exchange]['required'] += capital
            requirements[exchange]['bots'] += 1
        
        # Get actual balances
        balances = await wallet_balances_collection.find_one(
            {"user_id": user_id},
            {"_id": 0}
        )
        
        if balances:
            for exchange, req in requirements.items():
                exchange_balance = balances.get('exchanges', {}).get(exchange, {})
                available = exchange_balance.get('zar_balance', 0)
                req['available'] = available
                req['surplus_deficit'] = available - req['required']
                
                # Determine health
                if req['surplus_deficit'] >= 1000:
                    req['health'] = 'healthy'
                elif req['surplus_deficit'] >= 0:
                    req['health'] = 'adequate'
                elif req['surplus_deficit'] >= -500:
                    req['health'] = 'warning'
                else:
                    req['health'] = 'critical'
        
        return {
            "user_id": user_id,
            "requirements": requirements,
            "timestamp": balances.get('timestamp') if balances else None
        }
        
    except Exception as e:
        logger.error(f"Get capital requirements error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/funding-plans")
async def get_funding_plans(
    status: str = None,
    user_id: str = Depends(get_current_user)
):
    """Get all funding plans for user"""
    try:
        plans = await funding_plan_manager.get_user_funding_plans(
            user_id,
            status=status
        )
        
        return {
            "user_id": user_id,
            "plans": plans,
            "count": len(plans)
        }
        
    except Exception as e:
        logger.error(f"Get funding plans error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/funding-plans/{plan_id}")
async def get_funding_plan(plan_id: str, user_id: str = Depends(get_current_user)):
    """Get specific funding plan"""
    try:
        plan = await funding_plan_manager.get_funding_plan(plan_id)
        
        if plan.get('error'):
            raise HTTPException(status_code=404, detail=plan['error'])
        
        # Verify ownership
        if plan.get('user_id') != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        return plan
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get funding plan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/funding-plans/{plan_id}/cancel")
async def cancel_funding_plan(plan_id: str, user_id: str = Depends(get_current_user)):
    """Cancel a funding plan"""
    try:
        plan = await funding_plan_manager.get_funding_plan(plan_id)
        
        if plan.get('error'):
            raise HTTPException(status_code=404, detail=plan['error'])
        
        # Verify ownership
        if plan.get('user_id') != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        success = await funding_plan_manager.cancel_funding_plan(plan_id)
        
        return {
            "success": success,
            "plan_id": plan_id,
            "message": "Funding plan cancelled"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cancel funding plan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/transfer")
async def create_transfer(
    from_exchange: str,
    to_exchange: str,
    amount: float,
    user_id: str = Depends(get_current_user)
):
    """
    Create a transfer request (manual for now)
    Future: Can be automated with whitelisted addresses
    """
    try:
        # For now, just create a transfer instruction
        return {
            "success": True,
            "message": "Transfer instructions generated",
            "instructions": {
                "from": from_exchange,
                "to": to_exchange,
                "amount": amount,
                "steps": [
                    f"1. Log into {from_exchange.capitalize()}",
                    f"2. Navigate to Withdraw/Send",
                    f"3. Select ZAR",
                    f"4. Enter amount: R{amount:.2f}",
                    f"5. Use destination address for {to_exchange.capitalize()}",
                    "6. Confirm withdrawal",
                    "7. Wait for confirmation (10-60 minutes)"
                ],
                "note": "Auto-transfer coming soon! For now, follow these manual steps."
            }
        }
        
    except Exception as e:
        logger.error(f"Create transfer error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
