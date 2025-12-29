"""
AI Backend Scheduler - Runs nightly AI tasks automatically
No manual intervention needed - system manages itself
"""
import asyncio
import logging
from datetime import datetime, timezone, time, timedelta
import database as db
from bot_lifecycle import bot_lifecycle
from performance_ranker import performance_ranker
from engines.capital_allocator import capital_allocator
from bot_dna_evolution import bot_dna_evolution
from ai_super_brain import ai_super_brain

logger = logging.getLogger(__name__)

class AIScheduler:
    def __init__(self):
        self.is_running = False
        self.last_run = None
    
    async def run_nightly_ai_cycle(self):
        """Run all AI systems - executes once per day at 2 AM"""
        logger.info("🧠 Starting nightly AI cycle...")
        
        try:
            # Get all users
            users = await db.users_collection.find({}, {"_id": 0, "id": 1}).to_list(1000)
            
            for user in users:
                user_id = user['id']
                logger.info(f"Processing AI for user: {user_id[:8]}...")
                
                # 1. Check bot promotions (7-day paper → live)
                try:
                    promoted = await bot_lifecycle.check_promotions(user_id)
                    if promoted:
                        logger.info(f"✅ Promoted {len(promoted)} bots for {user_id[:8]}")
                except Exception as e:
                    logger.error(f"Bot lifecycle error for {user_id[:8]}: {e}")
                
                # 2. Rank bot performance
                try:
                    ranked = await performance_ranker.rank_bots(user_id)
                    logger.info(f"✅ Ranked {len(ranked)} bots for {user_id[:8]}")
                except Exception as e:
                    logger.error(f"Performance ranking error for {user_id[:8]}: {e}")
                
                # 3. Reallocate capital (reward winners, reduce losers)
                try:
                    result = await capital_allocator.reallocate_capital(user_id)
                    logger.info(f"✅ Reallocated capital for {user_id[:8]}: {result.get('message', 'OK')}")
                except Exception as e:
                    logger.error(f"Capital allocation error for {user_id[:8]}: {e}")
                
                # 4. AI Super Brain analysis (once per week)
                if datetime.now(timezone.utc).weekday() == 0:  # Monday
                    try:
                        insights = await ai_super_brain.generate_insights(user_id)
                        logger.info(f"✅ Generated insights for {user_id[:8]}")
                    except Exception as e:
                        logger.error(f"Super Brain error for {user_id[:8]}: {e}")
                
                # 5. DNA Evolution (once per week, spawn new bots)
                if datetime.now(timezone.utc).weekday() == 6:  # Sunday
                    try:
                        result = await bot_dna_evolution.evolve_generation(user_id)
                        if result and result.get('evolved', 0) > 0:
                            logger.info(f"✅ Evolved {result['evolved']} new bots for {user_id[:8]}")
                    except Exception as e:
                        logger.error(f"DNA evolution error for {user_id[:8]}: {e}")
            
            self.last_run = datetime.now(timezone.utc)
            logger.info("🧠 ✅ Nightly AI cycle complete!")
            
        except Exception as e:
            logger.error(f"AI cycle error: {e}")
    
    async def schedule_loop(self):
        """Run AI tasks at 2 AM daily"""
        self.is_running = True
        logger.info("🧠 AI Scheduler started - runs daily at 2 AM")
        
        while self.is_running:
            now = datetime.now(timezone.utc)
            target_time = time(2, 0)  # 2 AM
            
            # Calculate seconds until next 2 AM
            target_datetime = datetime.combine(now.date(), target_time).replace(tzinfo=timezone.utc)
            if now.time() >= target_time:
                # Already past 2 AM today, schedule for tomorrow
                target_datetime = target_datetime + timedelta(days=1)
            
            seconds_until_run = (target_datetime - now).total_seconds()
            
            logger.info(f"🧠 Next AI cycle in {seconds_until_run/3600:.1f} hours")
            
            # Sleep until 2 AM
            await asyncio.sleep(seconds_until_run)
            
            # Run the AI cycle
            await self.run_nightly_ai_cycle()
    
    async def start(self):
        """Start the scheduler"""
        asyncio.create_task(self.schedule_loop())
    
    def stop(self):
        """Stop the scheduler"""
        self.is_running = False

# Global instance
ai_scheduler = AIScheduler()
