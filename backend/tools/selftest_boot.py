#!/usr/bin/env python3
"""
Backend Boot Self-Test Script

This script verifies that the backend can boot properly without running uvicorn.
It checks:
1. Database connection
2. Required collection attributes exist
3. No ImportErrors or AttributeErrors

Usage:
    python backend/tools/selftest_boot.py
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

async def run_selftest():
    """Run self-test checks"""
    print("=" * 70)
    print("🧪 Amarktai Network Backend Boot Self-Test")
    print("=" * 70)
    
    passed = []
    failed = []
    
    # Test 1: Import database module
    print("\n[1/5] Testing database module import...")
    try:
        import database as db
        print("✅ PASS: database module imported")
        passed.append("Import database module")
    except Exception as e:
        print(f"❌ FAIL: Could not import database module: {e}")
        failed.append(f"Import database module: {e}")
        return passed, failed
    
    # Test 2: Connect to database
    print("\n[2/5] Testing database connection...")
    try:
        await db.connect()
        print("✅ PASS: Database connected successfully")
        passed.append("Database connection")
    except Exception as e:
        print(f"❌ FAIL: Database connection failed: {e}")
        failed.append(f"Database connection: {e}")
        return passed, failed
    
    # Test 3: Verify wallet_balances attribute exists
    print("\n[3/5] Testing wallet_balances attribute...")
    try:
        if hasattr(db, 'wallet_balances') and db.wallet_balances is not None:
            print(f"✅ PASS: db.wallet_balances exists (type: {type(db.wallet_balances).__name__})")
            passed.append("db.wallet_balances attribute")
        else:
            raise AttributeError("db.wallet_balances is None or missing")
    except Exception as e:
        print(f"❌ FAIL: db.wallet_balances check failed: {e}")
        failed.append(f"db.wallet_balances: {e}")
    
    # Test 4: Verify capital_injections attribute exists
    print("\n[4/5] Testing capital_injections attribute...")
    try:
        if hasattr(db, 'capital_injections') and db.capital_injections is not None:
            print(f"✅ PASS: db.capital_injections exists (type: {type(db.capital_injections).__name__})")
            passed.append("db.capital_injections attribute")
        else:
            raise AttributeError("db.capital_injections is None or missing")
    except Exception as e:
        print(f"❌ FAIL: db.capital_injections check failed: {e}")
        failed.append(f"db.capital_injections: {e}")
    
    # Test 5: Verify core collections exist
    print("\n[5/5] Testing core collection attributes...")
    core_collections = [
        'users_collection',
        'bots_collection',
        'trades_collection',
        'wallet_balances_collection',
        'capital_injections_collection'
    ]
    
    missing_collections = []
    for collection_name in core_collections:
        if not hasattr(db, collection_name) or getattr(db, collection_name) is None:
            missing_collections.append(collection_name)
    
    if not missing_collections:
        print(f"✅ PASS: All {len(core_collections)} core collections exist")
        passed.append("Core collections")
    else:
        msg = f"Missing collections: {', '.join(missing_collections)}"
        print(f"❌ FAIL: {msg}")
        failed.append(msg)
    
    # Close database connection
    await db.close_db()
    
    return passed, failed


def main():
    """Main entry point"""
    passed, failed = asyncio.run(run_selftest())
    
    print("\n" + "=" * 70)
    print("📊 SELF-TEST RESULTS")
    print("=" * 70)
    print(f"✅ PASSED: {len(passed)} tests")
    for test in passed:
        print(f"   • {test}")
    
    if failed:
        print(f"\n❌ FAILED: {len(failed)} tests")
        for test in failed:
            print(f"   • {test}")
        print("\n" + "=" * 70)
        print("❌ OVERALL: FAIL")
        print("=" * 70)
        sys.exit(1)
    else:
        print("\n" + "=" * 70)
        print("✅ OVERALL: PASS - Backend is ready to boot!")
        print("=" * 70)
        sys.exit(0)


if __name__ == "__main__":
    main()
