#!/usr/bin/env python3
"""
Production Readiness Validation Script

Validates that all critical environment variables and configurations
are properly set before allowing server startup in production mode.

Run before deployment: python3 scripts/validate_production_config.py
"""

import os
import sys
from typing import List, Tuple

# Color codes for output
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def check_critical_env_vars() -> Tuple[List[str], List[str]]:
    """Check critical environment variables"""
    errors = []
    warnings = []
    
    # Critical database config
    mongo_url = os.getenv('MONGO_URL', '')
    if not mongo_url or 'localhost' in mongo_url:
        errors.append("MONGO_URL must be set to a production MongoDB instance (not localhost)")
    
    # Critical security config
    jwt_secret = os.getenv('JWT_SECRET', '')
    if not jwt_secret or 'your-secret' in jwt_secret or 'change' in jwt_secret or len(jwt_secret) < 32:
        errors.append("JWT_SECRET must be a strong secret (32+ chars, no default values)")
    
    encryption_key = os.getenv('API_KEY_ENCRYPTION_KEY', '') or os.getenv('ENCRYPTION_KEY', '')
    if not encryption_key:
        errors.append("API_KEY_ENCRYPTION_KEY must be set for secure API key storage")
    
    # Check feature flags for production safety
    paper_trading = os.getenv('PAPER_TRADING', '0')
    live_trading = os.getenv('LIVE_TRADING', '0')
    autopilot = os.getenv('AUTOPILOT_ENABLED', '0')
    
    if paper_trading == '0' and live_trading == '0':
        warnings.append("Both PAPER_TRADING and LIVE_TRADING are disabled - no trading will occur")
    
    if autopilot == '1' and live_trading == '0' and paper_trading == '0':
        warnings.append("AUTOPILOT_ENABLED=1 but no trading mode enabled")
    
    return errors, warnings


def check_max_bots_config() -> Tuple[List[str], List[str]]:
    """Verify MAX_BOTS configuration"""
    errors = []
    warnings = []
    
    max_bots = int(os.getenv('MAX_BOTS', '45'))
    max_bots_per_user = int(os.getenv('MAX_BOTS_PER_USER', '45'))
    
    if max_bots != 45:
        warnings.append(f"MAX_BOTS is {max_bots}, expected 45")
    
    if max_bots_per_user != 45:
        warnings.append(f"MAX_BOTS_PER_USER is {max_bots_per_user}, expected 45")
    
    return errors, warnings


def check_exchange_keys() -> Tuple[List[str], List[str]]:
    """Check if exchange API keys are configured"""
    errors = []
    warnings = []
    
    live_trading = os.getenv('LIVE_TRADING', '0')
    
    if live_trading == '1':
        # If live trading is enabled, warn about API key requirements
        warnings.append("LIVE_TRADING=1: Ensure users have valid exchange API keys configured")
    
    return errors, warnings


def check_database_collections() -> Tuple[List[str], List[str]]:
    """Basic check that database.py is importable"""
    errors = []
    warnings = []
    
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
        import database
        # Just check import works
    except ImportError as e:
        errors.append(f"Cannot import database module: {e}")
    except Exception as e:
        warnings.append(f"Database module issue: {e}")
    
    return errors, warnings


def check_route_collisions() -> Tuple[List[str], List[str]]:
    """Check if test file exists for route collision detection"""
    errors = []
    warnings = []
    
    test_file = os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'backend', 
        'tests', 
        'test_route_collisions.py'
    )
    
    if not os.path.exists(test_file):
        warnings.append("Route collision test file not found - CI will not catch duplicates")
    
    return errors, warnings


def main():
    """Run all validation checks"""
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}Production Readiness Validation{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")
    
    all_errors = []
    all_warnings = []
    
    # Run all checks
    checks = [
        ("Critical Environment Variables", check_critical_env_vars),
        ("MAX_BOTS Configuration", check_max_bots_config),
        ("Exchange API Keys", check_exchange_keys),
        ("Database Configuration", check_database_collections),
        ("Route Collision Tests", check_route_collisions),
    ]
    
    for check_name, check_func in checks:
        print(f"Checking: {check_name}...")
        errors, warnings = check_func()
        all_errors.extend(errors)
        all_warnings.extend(warnings)
    
    # Print results
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}Validation Results{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")
    
    if all_errors:
        print(f"{RED}❌ CRITICAL ERRORS ({len(all_errors)}):{RESET}")
        for error in all_errors:
            print(f"   {RED}•{RESET} {error}")
        print()
    
    if all_warnings:
        print(f"{YELLOW}⚠️  WARNINGS ({len(all_warnings)}):{RESET}")
        for warning in all_warnings:
            print(f"   {YELLOW}•{RESET} {warning}")
        print()
    
    if not all_errors and not all_warnings:
        print(f"{GREEN}✅ All checks passed!{RESET}")
        print(f"{GREEN}   System is ready for production deployment.{RESET}\n")
        return 0
    elif all_errors:
        print(f"{RED}{'='*80}{RESET}")
        print(f"{RED}❌ VALIDATION FAILED{RESET}")
        print(f"{RED}{'='*80}{RESET}")
        print(f"{RED}Fix all critical errors before deploying to production.{RESET}\n")
        return 1
    else:
        print(f"{YELLOW}{'='*80}{RESET}")
        print(f"{YELLOW}⚠️  VALIDATION PASSED WITH WARNINGS{RESET}")
        print(f"{YELLOW}{'='*80}{RESET}")
        print(f"{YELLOW}Review warnings before deploying to production.{RESET}\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
