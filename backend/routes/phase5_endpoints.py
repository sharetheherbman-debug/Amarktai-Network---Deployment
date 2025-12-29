"""
Phase 5 API Endpoints - Risk Engine, Limits & Capital
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict
import logging

from auth import get_current_user
from engines.capital_allocator import capital_allocator
from engines.trade_staggerer import trade_staggerer
from engines.circuit_breaker import circuit_breaker
from engines.trade_limiter import trade_limiter
from risk_engine import risk_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/phase5", tags=["Phase 5 - Risk & Capital"])

# ============================================================================
# CAPITAL ALLOCATOR ENDPOINTS
# ============================================================================

@router.get("/capital/allocation-report")
async def get_allocation_report(current_user: Dict = Depends(get_current_user)):
    """Get capital allocation report for all bots"""
    try:
        report = await capital_allocator.get_allocation_report(current_user['id'])
        return report
    except Exception as e:
        logger.error(f"Allocation report error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/capital/rebalance")
async def rebalance_capital(current_user: Dict = Depends(get_current_user)):
    """Trigger capital rebalancing across all bots"""
    try:
        result = await capital_allocator.rebalance_all_bots(current_user['id'])
        return result
    except Exception as e:
        logger.error(f"Rebalance error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/capital/bot/{bot_id}/optimal")
async def get_optimal_allocation(bot_id: str, current_user: Dict = Depends(get_current_user)):
    """Get optimal capital allocation for a specific bot"""
    try:
        import database as db
        
        bot = await db.bots_collection.find_one({"id": bot_id, "user_id": current_user['id']}, {"_id": 0})
        
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        optimal = await capital_allocator.calculate_optimal_allocation(current_user['id'], bot)
        
        return {
            "bot_id": bot_id,
            "bot_name": bot.get('name'),
            "current_capital": bot.get('current_capital', 0),
            "optimal_capital": optimal,
            "difference": optimal - bot.get('current_capital', 0)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Optimal allocation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# TRADE STAGGERER ENDPOINTS
# ============================================================================

@router.get("/staggerer/schedule")
async def get_trade_schedule(current_user: Dict = Depends(get_current_user)):
    """Get 24-hour staggered trade schedule for all bots"""
    try:
        schedule = await trade_staggerer.calculate_daily_schedule(current_user['id'])
        return schedule
    except Exception as e:
        logger.error(f"Schedule error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/staggerer/queue-status")
async def get_queue_status():
    """Get current trade queue status"""
    try:
        status = await trade_staggerer.get_queue_status()
        return status
    except Exception as e:
        logger.error(f"Queue status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# CIRCUIT BREAKER ENDPOINTS
# ============================================================================

@router.get("/circuit-breaker/status/{bot_id}")
async def get_circuit_breaker_status(bot_id: str, current_user: Dict = Depends(get_current_user)):
    """Get circuit breaker status for a bot"""
    try:
        import database as db
        
        bot = await db.bots_collection.find_one({"id": bot_id, "user_id": current_user['id']}, {"_id": 0})
        
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        breach, reason = await circuit_breaker.check_bot_drawdown(bot)
        
        return {
            "bot_id": bot_id,
            "bot_name": bot.get('name'),
            "status": "breached" if breach else "ok",
            "reason": reason,
            "current_capital": bot.get('current_capital', 0),
            "initial_capital": bot.get('initial_capital', 0),
            "drawdown_pct": ((bot.get('initial_capital', 0) - bot.get('current_capital', 0)) / bot.get('initial_capital', 1)) * 100
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Circuit breaker status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/circuit-breaker/global-status")
async def get_global_circuit_breaker_status(current_user: Dict = Depends(get_current_user)):
    """Get global circuit breaker status"""
    try:
        breach, reason = await circuit_breaker.check_global_drawdown(current_user['id'])
        
        return {
            "status": "breached" if breach else "ok",
            "reason": reason
        }
    except Exception as e:
        logger.error(f"Global circuit breaker status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# TRADE LIMITER ENDPOINTS
# ============================================================================

@router.get("/limiter/bot/{bot_id}/status")
async def get_bot_trade_status(bot_id: str, current_user: Dict = Depends(get_current_user)):
    """Get trade limiter status for a bot"""
    try:
        status = await trade_limiter.get_bot_trade_status(bot_id)
        
        if status.get('error'):
            raise HTTPException(status_code=404, detail=status['error'])
        
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trade status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# RISK ENGINE ENDPOINTS
# ============================================================================

@router.post("/risk/check-trade")
async def check_trade_risk(
    bot_id: str,
    exchange: str,
    proposed_notional: float,
    risk_mode: str,
    current_user: Dict = Depends(get_current_user)
):
    """Check if a proposed trade passes risk checks"""
    try:
        allowed, reason = await risk_engine.check_trade_risk(
            current_user['id'],
            bot_id,
            exchange,
            proposed_notional,
            risk_mode
        )
        
        return {
            "allowed": allowed,
            "reason": reason,
            "bot_id": bot_id,
            "proposed_notional": proposed_notional
        }
    except Exception as e:
        logger.error(f"Risk check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
