"""
Phase 6 API Endpoints - AI, Learning & Autopilot
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List
import logging

from auth import get_current_user
from engines.ai_model_router import ai_model_router
from engines.self_learning import self_learning_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/phase6", tags=["Phase 6 - AI & Learning"])

# ============================================================================
# AI MODEL ROUTER ENDPOINTS
# ============================================================================

@router.get("/ai/health")
async def ai_health_check():
    """Check AI service health"""
    try:
        health = await ai_model_router.health_check()
        return health
    except Exception as e:
        logger.error(f"AI health check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ai/analyze-trade")
async def analyze_trade_opportunity(
    market_data: Dict,
    bot_config: Dict,
    current_user: Dict = Depends(get_current_user)
):
    """Use AI to analyze a trade opportunity"""
    try:
        analysis = await ai_model_router.analyze_trade_opportunity(market_data, bot_config)
        return analysis
    except Exception as e:
        logger.error(f"Trade analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ai/market-insight")
async def generate_market_insight(
    market_conditions: Dict,
    current_user: Dict = Depends(get_current_user)
):
    """Generate AI market insights"""
    try:
        insight = await ai_model_router.generate_market_insight(market_conditions)
        return {"insight": insight}
    except Exception as e:
        logger.error(f"Market insight error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ai/strategy-analysis/{bot_id}")
async def deep_strategy_analysis(
    bot_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Get deep AI strategy analysis for a bot"""
    try:
        import database as db
        
        # Get bot
        bot = await db.bots_collection.find_one({"id": bot_id, "user_id": current_user['id']}, {"_id": 0})
        
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        # Get recent trades
        recent_trades = await db.trades_collection.find(
            {"bot_id": bot_id},
            {"_id": 0}
        ).sort("timestamp", -1).limit(50).to_list(50)
        
        # Analyze
        bot_performance = {
            "trades_count": bot.get('trades_count', 0),
            "win_rate": (bot.get('win_count', 0) / bot.get('trades_count', 1)) * 100 if bot.get('trades_count', 0) > 0 else 0,
            "total_profit": bot.get('total_profit', 0),
            "avg_trade_size": bot.get('current_capital', 0) * 0.35,
            "risk_mode": bot.get('risk_mode', 'safe')
        }
        
        analysis = await ai_model_router.deep_strategy_analysis(bot_performance, recent_trades)
        
        return analysis
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Strategy analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# SELF-LEARNING ENGINE ENDPOINTS
# ============================================================================

@router.get("/learning/analyze/{bot_id}")
async def analyze_bot_performance(
    bot_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Analyze bot performance for learning"""
    try:
        analysis = await self_learning_engine.analyze_bot_performance(bot_id)
        return analysis
    except Exception as e:
        logger.error(f"Performance analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/learning/generate-adjustments/{bot_id}")
async def generate_bot_adjustments(
    bot_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Generate parameter adjustments for a bot"""
    try:
        # First analyze
        analysis = await self_learning_engine.analyze_bot_performance(bot_id)
        
        # Then generate adjustments
        adjustments = await self_learning_engine.generate_adjustments(bot_id, analysis)
        
        return adjustments
    except Exception as e:
        logger.error(f"Generate adjustments error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/learning/apply-adjustments/{bot_id}")
async def apply_bot_adjustments(
    bot_id: str,
    adjustments: List[Dict],
    current_user: Dict = Depends(get_current_user)
):
    """Apply approved adjustments to a bot"""
    try:
        result = await self_learning_engine.apply_adjustments(bot_id, adjustments)
        return result
    except Exception as e:
        logger.error(f"Apply adjustments error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/learning/run-cycle")
async def run_learning_cycle(current_user: Dict = Depends(get_current_user)):
    """Run full learning cycle for all user's bots"""
    try:
        result = await self_learning_engine.run_learning_cycle(current_user['id'])
        return result
    except Exception as e:
        logger.error(f"Learning cycle error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
