#!/usr/bin/env python3
"""
Production Smoke Check Script
Validates that the API is running and healthy after deployment
"""
import sys
import time
import requests
from datetime import datetime


def print_status(message, status="INFO"):
    """Print colored status message"""
    colors = {
        "PASS": "\033[92m✓",
        "FAIL": "\033[91m✗",
        "INFO": "\033[94mℹ",
        "WARN": "\033[93m⚠"
    }
    reset = "\033[0m"
    print(f"{colors.get(status, colors['INFO'])} {message}{reset}")


def check_endpoint(url, name, timeout=5):
    """Check if an endpoint is responding"""
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            print_status(f"{name}: OK (200)", "PASS")
            return True
        else:
            print_status(f"{name}: HTTP {response.status_code}", "FAIL")
            return False
    except requests.exceptions.ConnectionError:
        print_status(f"{name}: Connection refused", "FAIL")
        return False
    except requests.exceptions.Timeout:
        print_status(f"{name}: Timeout after {timeout}s", "FAIL")
        return False
    except Exception as e:
        print_status(f"{name}: {str(e)}", "FAIL")
        return False


def check_health(base_url):
    """Check health endpoint"""
    url = f"{base_url}/api/health"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_status(f"Health check: {data.get('status', 'unknown')}", "PASS")
            return True
        else:
            print_status(f"Health check failed: HTTP {response.status_code}", "FAIL")
            return False
    except Exception as e:
        print_status(f"Health check error: {e}", "FAIL")
        return False


def check_system_status(base_url):
    """Check system status endpoint (may require auth)"""
    url = f"{base_url}/api/system_status"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code in [200, 401]:  # 401 is OK, means auth is working
            print_status(f"System status endpoint: reachable", "PASS")
            return True
        else:
            print_status(f"System status: HTTP {response.status_code}", "WARN")
            return True  # Not critical
    except Exception as e:
        print_status(f"System status error: {e}", "WARN")
        return True  # Not critical


def main():
    """Run smoke tests"""
    print("\n" + "="*60)
    print("🔥 AMARKTAI NETWORK - PRODUCTION SMOKE TEST")
    print("="*60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Configuration
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    
    print_status(f"Testing API at: {base_url}", "INFO")
    print()
    
    # Run checks
    results = []
    
    # Critical checks
    print("Critical Checks:")
    print("-" * 60)
    results.append(check_endpoint(base_url, "Base URL"))
    results.append(check_health(base_url))
    
    print()
    
    # Non-critical checks
    print("Additional Checks:")
    print("-" * 60)
    results.append(check_system_status(base_url))
    
    print()
    
    # Summary
    print("="*60)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print_status(f"SMOKE TEST PASSED: {passed}/{total} checks successful", "PASS")
        print("="*60)
        print()
        return 0
    else:
        print_status(f"SMOKE TEST FAILED: {passed}/{total} checks successful", "FAIL")
        print("="*60)
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
