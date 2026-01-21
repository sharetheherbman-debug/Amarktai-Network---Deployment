"""
Migration: Add missing baseline fields to paused bots
Ensures all bots have starting_capital, peak_capital, and pause_reason fields
"""
import asyncio
from datetime import datetime, timezone
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database as db
from logger_config import logger


async def migrate_baseline_fields():
    """Add missing baseline fields to all bots"""
    try:
        # Connect to database
        await db.connect()
        logger.info("✅ Connected to database")
        
        # Find all bots missing baseline fields
        bots_missing_fields = await db.bots_collection.find({
            "$or": [
                {"starting_capital": {"$exists": False}},
                {"peak_capital": {"$exists": False}},
                {"pause_reason": {"$exists": False}}
            ]
        }, {"_id": 0}).to_list(1000)
        
        logger.info(f"Found {len(bots_missing_fields)} bots with missing baseline fields")
        
        if not bots_missing_fields:
            logger.info("No bots need migration")
            return
        
        # Update each bot with missing fields
        updated_count = 0
        for bot in bots_missing_fields:
            bot_id = bot.get('id')
            if not bot_id:
                continue
                
            updates = {}
            
            # Add starting_capital if missing (use current or initial capital)
            if 'starting_capital' not in bot:
                starting_capital = bot.get('current_capital', bot.get('initial_capital', 1000))
                updates['starting_capital'] = starting_capital
                logger.info(f"Bot {bot_id}: Adding starting_capital={starting_capital}")
            
            # Add peak_capital if missing (use current capital or starting capital)
            if 'peak_capital' not in bot:
                peak_capital = bot.get('current_capital', bot.get('starting_capital', bot.get('initial_capital', 1000)))
                updates['peak_capital'] = peak_capital
                logger.info(f"Bot {bot_id}: Adding peak_capital={peak_capital}")
            
            # Add pause_reason if missing and bot is paused
            if 'pause_reason' not in bot:
                if bot.get('status') == 'paused':
                    updates['pause_reason'] = "migrated_missing_field"
                    logger.info(f"Bot {bot_id}: Adding pause_reason=migrated_missing_field")
                else:
                    updates['pause_reason'] = None
            
            # Apply updates
            if updates:
                result = await db.bots_collection.update_one(
                    {"id": bot_id},
                    {"$set": updates}
                )
                
                if result.modified_count > 0:
                    updated_count += 1
        
        logger.info(f"✅ Migration complete: Updated {updated_count} bots")
        
    except Exception as e:
        logger.error(f"Migration error: {e}", exc_info=True)
        raise
    finally:
        await db.close_db()


async def repair_on_startup():
    """Safe startup repair that ensures baseline fields exist"""
    try:
        logger.info("🔧 Running startup baseline field repair...")
        
        # Find bots without required baseline fields
        result = await db.bots_collection.update_many(
            {"starting_capital": {"$exists": False}},
            [{"$set": {
                "starting_capital": {"$ifNull": ["$current_capital", {"$ifNull": ["$initial_capital", 1000]}]}
            }}]
        )
        logger.info(f"Added starting_capital to {result.modified_count} bots")
        
        result = await db.bots_collection.update_many(
            {"peak_capital": {"$exists": False}},
            [{"$set": {
                "peak_capital": {"$ifNull": ["$current_capital", {"$ifNull": ["$starting_capital", {"$ifNull": ["$initial_capital", 1000]}]}]}
            }}]
        )
        logger.info(f"Added peak_capital to {result.modified_count} bots")
        
        result = await db.bots_collection.update_many(
            {
                "status": "paused",
                "pause_reason": {"$exists": False}
            },
            {"$set": {"pause_reason": "system_startup_repair"}}
        )
        logger.info(f"Added pause_reason to {result.modified_count} paused bots")
        
        logger.info("✅ Startup baseline field repair complete")
        
    except Exception as e:
        logger.error(f"Startup repair error: {e}", exc_info=True)
        # Don't fail startup on repair errors


if __name__ == "__main__":
    asyncio.run(migrate_baseline_fields())
