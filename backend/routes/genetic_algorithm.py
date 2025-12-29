"""
Genetic Algorithm "DNA" Optimization Router
Manages bot evolution, mutation, and crossover for optimal trading strategies
"""

from fastapi import APIRouter, HTTPException, Depends, Body
from datetime import datetime, timezone
from typing import Dict, List
import logging

from auth import get_current_user
import database as db
from bot_dna_evolution import BotDNAEvolution

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/genetic", tags=["Genetic Algorithm"])

dna_evolution = BotDNAEvolution()


@router.post("/evolve")
async def evolve_bots(user_id: str = Depends(get_current_user)):
    """Run genetic algorithm evolution cycle on user's bots
    
    Evolution Process:
    1. Rank all bots by performance
    2. Select elite bots (top 30%)
    3. Identify weak bots (bottom 30%)
    4. Create offspring from elite bots
    5. Apply mutations
    6. Replace weak bots with evolved offspring
    
    Returns:
        - evolved_count: Number of bots evolved
        - generation: Current generation number
        - elite_count: Number of elite bots selected
    """
    try:
        result = await dna_evolution.evolve_bots(user_id)
        
        logger.info(f"Evolution cycle completed for user {user_id[:8]}: {result}")
        
        return {
            "success": result.get('evolved', 0) > 0,
            "evolved_count": result.get('evolved', 0),
            "generation": result.get('generation', 0),
            "elite_count": result.get('elite_count', 0),
            "message": result.get('message', 'Evolution completed'),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    except Exception as e:
        logger.error(f"Evolution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_evolution_status(user_id: str = Depends(get_current_user)):
    """Get current evolution status and bot DNA information
    
    Returns:
        - total_bots: Total number of bots
        - generation: Current generation
        - mutation_rate: Current mutation rate
        - elite_percent: Percentage of bots considered elite
        - bot_dna_summary: Summary of bot DNA diversity
    """
    try:
        # Get all bots
        bots = await db.bots_collection.find(
            {"user_id": user_id},
            {"_id": 0}
        ).to_list(1000)
        
        # Analyze DNA diversity
        risk_modes = {}
        exchanges = {}
        trading_pairs = {}
        
        for bot in bots:
            # Risk mode diversity
            risk_mode = bot.get('risk_mode', 'balanced')
            risk_modes[risk_mode] = risk_modes.get(risk_mode, 0) + 1
            
            # Exchange diversity
            exchange = bot.get('exchange', 'luno')
            exchanges[exchange] = exchanges.get(exchange, 0) + 1
            
            # Trading pair diversity
            trading_pair = bot.get('trading_pair', 'BTC/ZAR')
            trading_pairs[trading_pair] = trading_pairs.get(trading_pair, 0) + 1
        
        # Calculate diversity score (0-1, higher is more diverse)
        def calculate_diversity(distribution: Dict) -> float:
            if not distribution:
                return 0.0
            total = sum(distribution.values())
            return 1.0 - sum((count/total)**2 for count in distribution.values())
        
        diversity_score = (
            calculate_diversity(risk_modes) +
            calculate_diversity(exchanges) +
            calculate_diversity(trading_pairs)
        ) / 3
        
        return {
            "total_bots": len(bots),
            "generation": dna_evolution.generation,
            "mutation_rate": dna_evolution.mutation_rate,
            "elite_percent": dna_evolution.elite_percent,
            "bot_dna_summary": {
                "risk_modes": risk_modes,
                "exchanges": exchanges,
                "trading_pairs": trading_pairs,
                "diversity_score": round(diversity_score, 3)
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    except Exception as e:
        logger.error(f"Get evolution status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mutate/{bot_id}")
async def mutate_bot(
    bot_id: str,
    data: Dict = Body(default={}),
    user_id: str = Depends(get_current_user)
):
    """Manually mutate a specific bot's DNA
    
    Args:
        bot_id: Bot ID to mutate
        data: Optional mutation parameters
            - mutation_strength: 0.1-1.0 (default: 0.15)
    
    Returns:
        Updated bot with mutated DNA
    """
    try:
        # Verify bot belongs to user
        bot = await db.bots_collection.find_one({"id": bot_id, "user_id": user_id}, {"_id": 0})
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        mutation_strength = data.get('mutation_strength', 0.15)
        
        # Apply mutation
        new_dna = dna_evolution._mutate(bot)
        
        # Update bot
        await db.bots_collection.update_one(
            {"id": bot_id},
            {"$set": new_dna}
        )
        
        # Get updated bot
        updated_bot = await db.bots_collection.find_one({"id": bot_id}, {"_id": 0})
        
        logger.info(f"Bot {bot_id[:8]} manually mutated")
        
        return {
            "success": True,
            "bot": updated_bot,
            "mutations_applied": list(new_dna.keys()),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mutate bot error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/crossover")
async def crossover_bots(
    data: Dict = Body(...),
    user_id: str = Depends(get_current_user)
):
    """Create offspring from two parent bots
    
    Body:
        {
            "parent1_id": "bot_id_1",
            "parent2_id": "bot_id_2",
            "name": "Offspring Bot Name",
            "apply_mutation": true
        }
    
    Returns:
        New bot created from crossover
    """
    try:
        parent1_id = data.get('parent1_id')
        parent2_id = data.get('parent2_id')
        offspring_name = data.get('name', 'Evolved Bot')
        apply_mutation = data.get('apply_mutation', True)
        
        if not parent1_id or not parent2_id:
            raise HTTPException(status_code=400, detail="Both parent IDs are required")
        
        # Get parent bots
        parent1 = await db.bots_collection.find_one({"id": parent1_id, "user_id": user_id}, {"_id": 0})
        parent2 = await db.bots_collection.find_one({"id": parent2_id, "user_id": user_id}, {"_id": 0})
        
        if not parent1 or not parent2:
            raise HTTPException(status_code=404, detail="One or both parent bots not found")
        
        # Perform crossover
        offspring_dna = dna_evolution._crossover(parent1, parent2)
        
        # Apply mutation if requested
        if apply_mutation:
            offspring_dna = dna_evolution._mutate(offspring_dna)
        
        # Create new bot
        import uuid
        new_bot = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": offspring_name,
            **offspring_dna,
            "status": "active",
            "current_capital": offspring_dna.get('initial_capital', 1000),
            "total_profit": 0,
            "win_rate": 0,
            "trades_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "parents": [parent1_id, parent2_id],
            "generation": max(parent1.get('generation', 0), parent2.get('generation', 0)) + 1
        }
        
        await db.bots_collection.insert_one(new_bot)
        
        logger.info(f"Offspring bot created from {parent1_id[:8]} x {parent2_id[:8]}")
        
        return {
            "success": True,
            "bot": new_bot,
            "parents": [parent1_id, parent2_id],
            "mutations_applied": apply_mutation,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Crossover error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance-ranking")
async def get_performance_ranking(user_id: str = Depends(get_current_user)):
    """Get bots ranked by performance for evolution selection
    
    Returns bots sorted by fitness score (combination of profit, win rate, etc.)
    """
    try:
        from performance_ranker import performance_ranker
        
        ranked_bots = await performance_ranker.rank_bots(user_id)
        
        return {
            "bots": ranked_bots,
            "total": len(ranked_bots),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    except Exception as e:
        logger.error(f"Get performance ranking error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-evolve/enable")
async def enable_auto_evolution(
    data: Dict = Body(default={}),
    user_id: str = Depends(get_current_user)
):
    """Enable automatic evolution on schedule
    
    Body:
        {
            "interval_hours": 24,  # Run evolution every 24 hours
            "min_bots": 10  # Minimum bots required for evolution
        }
    """
    try:
        import database as db
        
        interval_hours = data.get('interval_hours', 24)
        min_bots = data.get('min_bots', 10)
        
        await db.users_collection.update_one(
            {"id": user_id},
            {
                "$set": {
                    "auto_evolution_enabled": True,
                    "auto_evolution_interval_hours": interval_hours,
                    "auto_evolution_min_bots": min_bots,
                    "auto_evolution_enabled_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        logger.info(f"Auto-evolution enabled for user {user_id[:8]}")
        
        return {
            "success": True,
            "message": f"Automatic evolution enabled (every {interval_hours} hours)",
            "interval_hours": interval_hours,
            "min_bots": min_bots,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    except Exception as e:
        logger.error(f"Enable auto-evolution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-evolve/disable")
async def disable_auto_evolution(user_id: str = Depends(get_current_user)):
    """Disable automatic evolution"""
    try:
        import database as db
        
        await db.users_collection.update_one(
            {"id": user_id},
            {
                "$set": {
                    "auto_evolution_enabled": False,
                    "auto_evolution_disabled_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        logger.info(f"Auto-evolution disabled for user {user_id[:8]}")
        
        return {
            "success": True,
            "message": "Automatic evolution disabled",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    except Exception as e:
        logger.error(f"Disable auto-evolution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
