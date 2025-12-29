#!/usr/bin/env python3
"""
Preflight check - validates that server.py can be imported without errors
Run before deploying: python -m backend.preflight
"""
import sys
import os

def main():
    try:
        print("🔍 Preflight check starting...")
        
        # Check environment
        mongo_uri = os.getenv('MONGO_URI') or os.getenv('MONGO_URL')
        if not mongo_uri:
            print("⚠️  Warning: MONGO_URI not set, will use default mongodb://localhost:27017")
        else:
            print(f"✅ MongoDB URI configured: {mongo_uri[:20]}...")
        
        # Import server (this triggers all imports)
        print("📦 Importing server module...")
        from server import app
        
        print("✅ Server imported successfully")
        
        # Check database exports
        print("📦 Checking database module exports...")
        from database import (
            users_collection, bots_collection, api_keys_collection,
            trades_collection, system_modes_collection, alerts_collection,
            chat_messages_collection, learning_logs_collection,
            autopilot_actions_collection, rogue_detections_collection,
            wallets_collection, ledger_collection, profits_collection,
            close_db, init_db, db, client
        )
        print("✅ All required database collections present")
        
        # Check auth exports
        print("📦 Checking auth module exports...")
        from auth import create_access_token, get_current_user, is_admin
        print("✅ All required auth functions present")
        
        # Check autopilot engine
        print("📦 Checking autopilot engine...")
        from autopilot_engine import autopilot
        if autopilot.scheduler is None:
            print("❌ FAILED - Autopilot scheduler is None (should be initialized in __init__)")
            return 1
        print("✅ Autopilot engine initialized correctly")
        
        print("\n🎉 PREFLIGHT PASSED - Server can start safely")
        return 0
        
    except ImportError as e:
        print(f"\n❌ PREFLIGHT FAILED - Import error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ PREFLIGHT FAILED - Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
