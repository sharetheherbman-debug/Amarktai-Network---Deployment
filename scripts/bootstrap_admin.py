#!/usr/bin/env python3
"""
Admin Bootstrap Script
Creates or updates admin user with credentials from environment variables.
Can be run multiple times safely (upserts admin user).

Usage:
    python scripts/bootstrap_admin.py

Environment Variables:
    MONGO_URL - MongoDB connection URL (default: mongodb://localhost:27017)
    DB_NAME - Database name (default: amarktai_trading)
    JWT_SECRET - JWT secret for token generation
    AMK_ADMIN_EMAIL - Admin email (default: admin@amarktai.online)
    AMK_ADMIN_PASS - Admin password (required)
    INVITE_CODE - Optional invite code for the platform
"""

import os
import sys
import asyncio
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import database as db
from auth import get_password_hash
from datetime import datetime, timezone
from uuid import uuid4


async def bootstrap_admin():
    """Bootstrap admin user from environment variables"""
    
    # Load environment variables
    mongo_url = os.getenv('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.getenv('DB_NAME', 'amarktai_trading')
    jwt_secret = os.getenv('JWT_SECRET')
    admin_email = os.getenv('AMK_ADMIN_EMAIL', 'admin@amarktai.online').lower().strip()
    admin_password = os.getenv('AMK_ADMIN_PASS')
    
    # Validate required variables
    if not jwt_secret:
        print("❌ ERROR: JWT_SECRET environment variable is required")
        sys.exit(1)
    
    if not admin_password:
        print("❌ ERROR: AMK_ADMIN_PASS environment variable is required")
        sys.exit(1)
    
    print("=" * 60)
    print("Admin Bootstrap Script")
    print("=" * 60)
    print(f"MongoDB URL: {mongo_url}")
    print(f"Database: {db_name}")
    print(f"Admin Email: {admin_email}")
    print("=" * 60)
    
    try:
        # Connect to database
        print("\n🔌 Connecting to MongoDB...")
        await db.connect()
        print("✅ Connected to MongoDB")
        
        # Check if admin user exists
        existing_admin = await db.users_collection.find_one(
            {"email": admin_email},
            {"_id": 0}
        )
        
        # Hash password
        password_hash = get_password_hash(admin_password)
        
        if existing_admin:
            print(f"\n📝 Updating existing admin user: {admin_email}")
            
            # Update admin user
            await db.users_collection.update_one(
                {"email": admin_email},
                {
                    "$set": {
                        "password_hash": password_hash,
                        "is_admin": True,
                        "role": "admin",
                        "blocked": False
                    }
                }
            )
            
            print(f"✅ Admin user updated: {admin_email}")
        else:
            print(f"\n➕ Creating new admin user: {admin_email}")
            
            # Create admin user
            admin_id = str(uuid4())
            admin_user = {
                "id": admin_id,
                "email": admin_email,
                "first_name": "Admin",
                "password_hash": password_hash,
                "is_admin": True,
                "role": "admin",
                "currency": "ZAR",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "system_mode": "testing",
                "autopilot_enabled": True,
                "bodyguard_enabled": True,
                "learning_enabled": True,
                "emergency_stop": False,
                "blocked": False,
                "two_factor_enabled": False
            }
            
            await db.users_collection.insert_one(admin_user)
            print(f"✅ Admin user created: {admin_email}")
        
        print("\n" + "=" * 60)
        print("✅ OK admin ensured")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Close database connection
        await db.close_db()
        print("\n🔌 Database connection closed")


if __name__ == "__main__":
    asyncio.run(bootstrap_admin())
