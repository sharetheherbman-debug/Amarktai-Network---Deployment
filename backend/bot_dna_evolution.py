"""
Bot DNA Evolution System
- Genetic algorithm for bot optimization
- Mutation and crossover of successful bots
- Natural selection based on performance
"""

import asyncio
import random
from datetime import datetime, timezone
from logger_config import logger
import database as db
from performance_ranker import performance_ranker


class BotDNAEvolution:
    def __init__(self):
        self.mutation_rate = 0.15  # 15% chance of mutation
        self.elite_percent = 0.30  # Top 30% survive
        self.generation = 0
    
    async def evolve_bots(self, user_id: str):
        """Run evolution cycle on user's bots"""
        try:
            logger.info(f"Starting bot evolution for user {user_id}")
            
            # Get ranked bots
            ranked_bots = await performance_ranker.rank_bots(user_id)
            
            if len(ranked_bots) < 10:
                logger.info("Insufficient bots for evolution (need 10+)")
                return {"evolved": 0, "message": "Need 10+ bots for evolution"}
            
            # Identify elite bots (top 30%)
            elite_count = max(int(len(ranked_bots) * self.elite_percent), 3)
            elite_bots = ranked_bots[:elite_count]
            
            # Identify weak bots (bottom 30%)
            weak_count = max(int(len(ranked_bots) * 0.30), 3)
            weak_bots = ranked_bots[-weak_count:]
            
            # Evolve weak bots based on elite DNA
            evolved_count = 0
            
            for weak_bot in weak_bots:
                # Select two elite parents
                parent1 = random.choice(elite_bots)
                parent2 = random.choice(elite_bots)
                
                # Create child DNA
                new_dna = self._crossover(parent1, parent2)
                
                # Apply mutation
                new_dna = self._mutate(new_dna)
                
                # Update weak bot with new DNA
                await self._update_bot_dna(weak_bot['id'], new_dna)
                evolved_count += 1
            
            self.generation += 1
            logger.info(f"Evolution complete: {evolved_count} bots evolved (Generation {self.generation})")
            
            return {
                "evolved": evolved_count,
                "generation": self.generation,
                "elite_count": elite_count,
                "message": f"Evolution cycle {self.generation} complete"
            }
            
        except Exception as e:
            logger.error(f"Bot evolution failed: {e}")
            return {"evolved": 0, "error": str(e)}
    
    def _crossover(self, parent1: dict, parent2: dict) -> dict:
        """Combine DNA from two parents"""
        dna = {}
        
        # Risk mode (50/50 chance from each parent)
        dna['risk_mode'] = random.choice([parent1.get('risk_mode'), parent2.get('risk_mode')])
        
        # Trading pair (favor parent1 if better performing)
        dna['trading_pair'] = parent1.get('trading_pair', 'BTC/ZAR')
        
        # Capital (average of parents)
        dna['initial_capital'] = (
            parent1.get('initial_capital', 1000) + parent2.get('initial_capital', 1000)
        ) / 2
        
        # Exchange (from better parent)
        dna['exchange'] = parent1.get('exchange', 'luno')
        
        return dna
    
    def _mutate(self, dna: dict) -> dict:
        """Apply random mutations to DNA"""
        if random.random() < self.mutation_rate:
            # Mutate risk mode
            risk_modes = ['safe', 'balanced', 'risky']
            dna['risk_mode'] = random.choice(risk_modes)
            logger.info(f"Mutation: risk_mode -> {dna['risk_mode']}")
        
        if random.random() < self.mutation_rate:
            # Mutate trading pair
            pairs = ['BTC/ZAR', 'ETH/ZAR', 'XRP/ZAR']
            dna['trading_pair'] = random.choice(pairs)
            logger.info(f"Mutation: trading_pair -> {dna['trading_pair']}")
        
        if random.random() < self.mutation_rate:
            # Mutate capital (±20%)
            factor = random.uniform(0.8, 1.2)
            dna['initial_capital'] = dna['initial_capital'] * factor
            logger.info(f"Mutation: capital -> R{dna['initial_capital']:.2f}")
        
        return dna
    
    async def _update_bot_dna(self, bot_id: str, new_dna: dict):
        """Update bot with evolved DNA"""
        try:
            update_data = {
                "risk_mode": new_dna['risk_mode'],
                "trading_pair": new_dna.get('trading_pair', 'BTC/ZAR'),
                "initial_capital": new_dna['initial_capital'],
                "current_capital": new_dna['initial_capital'],
                "exchange": new_dna.get('exchange', 'luno'),
                "evolved_at": datetime.now(timezone.utc).isoformat(),
                "generation": self.generation
            }
            
            await db.bots_collection.update_one(
                {"id": bot_id},
                {
                    "$set": update_data,
                    "$push": {
                        "evolution_history": {
                            "generation": self.generation,
                            "dna": new_dna,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    }
                }
            )
            
            logger.info(f"Bot {bot_id} evolved to generation {self.generation}")
            
        except Exception as e:
            logger.error(f"Bot DNA update failed: {e}")


# Global instance
bot_dna_evolution = BotDNAEvolution()
