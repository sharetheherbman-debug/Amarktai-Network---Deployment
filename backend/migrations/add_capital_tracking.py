#!/usr/bin/env python3
"""
Migration Script - Add Capital Tracking Fields
Adds balance tracking fields to users and bots for capital allocation integrity.
Safe, idempotent, and non-destructive.
"""
import asyncio
import sys
import os
from datetime import datetime, timezone

# Add parent directory to path (migrations -> backend -> project root -> backend)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import database as db
from logger_config import logger


async def migrate_users():
    """Add balance tracking fields to users collection"""
    print("\n" + "="*60)
    print("MIGRATING USERS COLLECTION")
    print("="*60)
    
    try:
        # Get all users
        users = await db.users_collection.find({}).to_list(None)
        print(f"Found {len(users)} users")
        
        updated_count = 0
        for user in users:
            user_id = user.get("id")
            
            # Check if already has balance fields
            has_balance = "balance" in user
            has_allocated = "allocated_balance" in user
            has_reserved = "reserved_balance" in user
            
            if has_balance and has_allocated and has_reserved:
                print(f"  ✓ User {user_id[:8]} already has balance fields")
                continue
            
            # Calculate allocated balance from active bots
            active_bots = await db.bots_collection.find({
                "user_id": user_id,
                "status": {"$in": ["active", "paused"]}
            }).to_list(None)
            
            total_allocated = sum(
                bot.get("allocated_capital", bot.get("current_capital", 0.0))
                for bot in active_bots
            )
            
            # Set default balance (we'll use a reasonable default)
            # In production, this should be set based on actual exchange balances
            default_balance = total_allocated * 1.5  # Give 50% buffer
            
            # Update user document
            update_fields = {}
            
            if not has_balance:
                update_fields["balance"] = default_balance
            
            if not has_allocated:
                update_fields["allocated_balance"] = total_allocated
            
            if not has_reserved:
                update_fields["reserved_balance"] = 0.0
            
            if update_fields:
                update_fields["migration_updated_at"] = datetime.now(timezone.utc).isoformat()
                update_fields["migration_note"] = "Added capital tracking fields"
                
                await db.users_collection.update_one(
                    {"id": user_id},
                    {"$set": update_fields}
                )
                
                print(f"  ✓ Updated user {user_id[:8]}: balance={default_balance:.2f}, allocated={total_allocated:.2f}")
                updated_count += 1
        
        print(f"\n✅ Updated {updated_count} users")
        return True
    
    except Exception as e:
        print(f"\n❌ Error migrating users: {e}")
        logger.error(f"Migration error (users): {e}")
        return False


async def migrate_bots():
    """Add allocated_capital field to bots collection"""
    print("\n" + "="*60)
    print("MIGRATING BOTS COLLECTION")
    print("="*60)
    
    try:
        # Get all bots
        bots = await db.bots_collection.find({}).to_list(None)
        print(f"Found {len(bots)} bots")
        
        updated_count = 0
        for bot in bots:
            bot_id = bot.get("id")
            
            # Check if already has allocated_capital
            if "allocated_capital" in bot:
                print(f"  ✓ Bot {bot_id[:8]} already has allocated_capital")
                continue
            
            # Set allocated_capital based on initial_capital or current_capital
            allocated_capital = bot.get("initial_capital", bot.get("current_capital", 0.0))
            
            # Update bot document
            await db.bots_collection.update_one(
                {"id": bot_id},
                {
                    "$set": {
                        "allocated_capital": allocated_capital,
                        "migration_updated_at": datetime.now(timezone.utc).isoformat(),
                        "migration_note": "Added allocated_capital field"
                    }
                }
            )
            
            print(f"  ✓ Updated bot {bot_id[:8]}: allocated_capital={allocated_capital:.2f}")
            updated_count += 1
        
        print(f"\n✅ Updated {updated_count} bots")
        return True
    
    except Exception as e:
        print(f"\n❌ Error migrating bots: {e}")
        logger.error(f"Migration error (bots): {e}")
        return False


async def verify_migration():
    """Verify that migration was successful"""
    print("\n" + "="*60)
    print("VERIFYING MIGRATION")
    print("="*60)
    
    try:
        # Check users
        users_without_balance = await db.users_collection.count_documents({
            "$or": [
                {"balance": {"$exists": False}},
                {"allocated_balance": {"$exists": False}},
                {"reserved_balance": {"$exists": False}}
            ]
        })
        
        # Check bots
        bots_without_allocated = await db.bots_collection.count_documents({
            "allocated_capital": {"$exists": False}
        })
        
        print(f"\nUsers without balance fields: {users_without_balance}")
        print(f"Bots without allocated_capital: {bots_without_allocated}")
        
        if users_without_balance == 0 and bots_without_allocated == 0:
            print("\n✅ Migration verification PASSED")
            return True
        else:
            print("\n⚠️  Migration verification found missing fields")
            return False
    
    except Exception as e:
        print(f"\n❌ Error verifying migration: {e}")
        logger.error(f"Verification error: {e}")
        return False


async def main():
    """Main migration entry point"""
    print("\n" + "="*60)
    print("CAPITAL TRACKING MIGRATION SCRIPT")
    print("="*60)
    print(f"Started at: {datetime.now(timezone.utc).isoformat()}")
    
    try:
        # Connect to database
        print("\nConnecting to database...")
        await db.connect()
        print("✅ Database connected")
        
        # Run migrations
        users_ok = await migrate_users()
        bots_ok = await migrate_bots()
        
        # Verify
        if users_ok and bots_ok:
            verified = await verify_migration()
            
            if verified:
                print("\n" + "="*60)
                print("✅ MIGRATION COMPLETED SUCCESSFULLY")
                print("="*60)
                return True
            else:
                print("\n" + "="*60)
                print("⚠️  MIGRATION COMPLETED WITH WARNINGS")
                print("="*60)
                return False
        else:
            print("\n" + "="*60)
            print("❌ MIGRATION FAILED")
            print("="*60)
            return False
    
    except Exception as e:
        print(f"\n❌ Migration error: {e}")
        logger.error(f"Migration error: {e}")
        return False
    finally:
        # Disconnect from database
        if hasattr(db, 'client') and db.client:
            db.client.close()
            print("\nDatabase connection closed")


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
