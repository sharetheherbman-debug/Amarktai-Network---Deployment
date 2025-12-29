"""
Migration: Add lifecycle fields to existing bots
Run once to update all existing bots with new lifecycle tracking fields
"""

import asyncio
from datetime import datetime, timezone, timedelta
import database as db
import logging

logger = logging.getLogger(__name__)

async def migrate_bot_lifecycle_fields():
    """Add lifecycle fields to all existing bots"""
    
    try:
        # Get all bots without lifecycle fields
        bots = await db.bots_collection.find({}, {"_id": 0}).to_list(10000)
        
        updated_count = 0
        
        for bot in bots:
            updates = {}
            
            # Add created_at if missing
            if 'created_at' not in bot:
                # Use paper_start_date if available, otherwise current time
                if 'paper_start_date' in bot:
                    updates['created_at'] = bot['paper_start_date']
                else:
                    updates['created_at'] = datetime.now(timezone.utc).isoformat()
            
            # Add lifecycle_stage if missing
            if 'lifecycle_stage' not in bot:
                mode = bot.get('mode') or bot.get('trading_mode', 'paper')
                if mode == 'live':
                    updates['lifecycle_stage'] = 'live_trading'
                else:
                    updates['lifecycle_stage'] = 'paper_training'
            
            # Add first_trade_at if missing
            if 'first_trade_at' not in bot:
                updates['first_trade_at'] = None
            
            # Add last_trade_at if missing
            if 'last_trade_at' not in bot:
                updates['last_trade_at'] = bot.get('last_trade_time')  # Use old field if exists
            
            # Add paper_start_date if missing
            if 'paper_start_date' not in bot:
                updates['paper_start_date'] = bot.get('created_at', datetime.now(timezone.utc).isoformat())
            
            # Add paper_end_eligible_at if missing
            if 'paper_end_eligible_at' not in bot:
                paper_start = bot.get('paper_start_date')
                if paper_start:
                    try:
                        start_dt = datetime.fromisoformat(paper_start.replace('Z', '+00:00'))
                        eligible_dt = start_dt + timedelta(days=7)
                        updates['paper_end_eligible_at'] = eligible_dt.isoformat()
                    except:
                        updates['paper_end_eligible_at'] = None
                else:
                    updates['paper_end_eligible_at'] = None
            
            # Add promoted_to_live_at if missing
            if 'promoted_to_live_at' not in bot:
                mode = bot.get('mode') or bot.get('trading_mode', 'paper')
                if mode == 'live':
                    # Estimate promotion date as 7 days after paper start
                    paper_start = bot.get('paper_start_date')
                    if paper_start:
                        try:
                            start_dt = datetime.fromisoformat(paper_start.replace('Z', '+00:00'))
                            promoted_dt = start_dt + timedelta(days=7)
                            updates['promoted_to_live_at'] = promoted_dt.isoformat()
                        except:
                            updates['promoted_to_live_at'] = None
                    else:
                        updates['promoted_to_live_at'] = None
                else:
                    updates['promoted_to_live_at'] = None
            
            # Add total_injections if missing
            if 'total_injections' not in bot:
                updates['total_injections'] = 0
            
            # Ensure trading_mode matches mode for consistency
            if 'trading_mode' not in bot:
                updates['trading_mode'] = bot.get('mode', 'paper')
            
            # Apply updates
            if updates:
                await db.bots_collection.update_one(
                    {"id": bot['id']},
                    {"$set": updates}
                )
                updated_count += 1
        
        logger.info(f"✅ Migration complete: Updated {updated_count} bots with lifecycle fields")
        
        return {
            "success": True,
            "bots_updated": updated_count,
            "total_bots": len(bots)
        }
        
    except Exception as e:
        logger.error(f"Migration error: {e}")
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    # Run migration
    result = asyncio.run(migrate_bot_lifecycle_fields())
    print(f"Migration result: {result}")
