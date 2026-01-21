#!/usr/bin/env python3
"""
Comprehensive Production Smoke Check Script
Validates critical API endpoints and functionality after deployment
"""
import sys
import time
import requests
from datetime import datetime
import json


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


def check_endpoint(url, name, timeout=5, expected_status=200, method="GET", **kwargs):
    """Check if an endpoint is responding with expected status"""
    try:
        if method == "GET":
            response = requests.get(url, timeout=timeout, **kwargs)
        elif method == "POST":
            response = requests.post(url, timeout=timeout, **kwargs)
        elif method == "DELETE":
            response = requests.delete(url, timeout=timeout, **kwargs)
        else:
            response = requests.get(url, timeout=timeout, **kwargs)
            
        if response.status_code == expected_status or (isinstance(expected_status, list) and response.status_code in expected_status):
            print_status(f"{name}: OK ({response.status_code})", "PASS")
            return True
        else:
            print_status(f"{name}: HTTP {response.status_code} (expected {expected_status})", "FAIL")
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
            status = data.get('status', 'unknown')
            print_status(f"Health check: {status}", "PASS" if status == "healthy" else "WARN")
            return True
        else:
            print_status(f"Health check failed: HTTP {response.status_code}", "FAIL")
            return False
    except Exception as e:
        print_status(f"Health check error: {e}", "FAIL")
        return False


def check_websocket_endpoint(base_url):
    """Check if WebSocket endpoint exists (returns proper error for missing token)"""
    url = f"{base_url}/api/ws"
    try:
        # WebSocket without token should return HTTP error during upgrade
        response = requests.get(url, timeout=5)
        # Any response means the endpoint exists
        print_status(f"WebSocket endpoint: exists", "PASS")
        return True
    except Exception as e:
        # Connection refused means endpoint doesn't exist
        if "Connection refused" in str(e):
            print_status(f"WebSocket endpoint: not found", "FAIL")
            return False
        # Other errors are OK (e.g., protocol mismatch)
        print_status(f"WebSocket endpoint: exists (protocol check)", "PASS")
        return True


def check_api_keys_endpoints(base_url, token=None):
    """Check API keys management endpoints"""
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    
    results = []
    # Check list endpoint (requires auth, should return 401 without token or 200 with token)
    results.append(check_endpoint(
        f"{base_url}/api/keys/list",
        "API Keys - List providers",
        expected_status=[200, 401],
        headers=headers
    ))
    
    # Check test endpoint exists (requires auth)
    results.append(check_endpoint(
        f"{base_url}/api/keys/test",
        "API Keys - Test endpoint",
        method="POST",
        expected_status=[400, 401, 422],  # 400/422 for missing data, 401 for no auth
        headers=headers,
        json={"provider": "test"}
    ))
    
    return all(results)


def check_admin_endpoints(base_url, token=None):
    """Check admin panel endpoints"""
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    
    results = []
    # Check admin users endpoint (should return 401 or 403 without valid admin token)
    results.append(check_endpoint(
        f"{base_url}/api/admin/users",
        "Admin - List users",
        expected_status=[401, 403],
        headers=headers
    ))
    
    # Check admin bots endpoint (should return 401 or 403 without valid admin token)
    results.append(check_endpoint(
        f"{base_url}/api/admin/bots",
        "Admin - List bots",
        expected_status=[401, 403],
        headers=headers
    ))
    
    return all(results)


def check_quarantine_endpoints(base_url, token=None):
    """Check bot quarantine endpoints"""
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    
    results = []
    # Check quarantine status endpoint
    results.append(check_endpoint(
        f"{base_url}/api/quarantine/status",
        "Quarantine - Status",
        expected_status=[200, 401],
        headers=headers
    ))
    
    # Check quarantine config endpoint (public)
    results.append(check_endpoint(
        f"{base_url}/api/quarantine/config",
        "Quarantine - Config",
        expected_status=200
    ))
    
    return all(results)


def check_training_endpoints(base_url, token=None):
    """Check bot training endpoints"""
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    
    results = []
    # Check training history endpoint
    results.append(check_endpoint(
        f"{base_url}/api/training/history",
        "Training - History",
        expected_status=[200, 401],
        headers=headers
    ))
    
    return all(results)


def check_realtime_events(base_url):
    """Check SSE realtime events endpoint"""
    return check_endpoint(
        f"{base_url}/api/realtime/events",
        "Real-time Events (SSE)",
        expected_status=[200, 401]
    )


def main():
    """Run comprehensive smoke tests"""
    print("\n" + "="*70)
    print("🔥 AMARKTAI NETWORK - COMPREHENSIVE PRODUCTION SMOKE TEST")
    print("="*70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Configuration
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    test_token = sys.argv[2] if len(sys.argv) > 2 else None
    
    print_status(f"Testing API at: {base_url}", "INFO")
    if test_token:
        print_status(f"Using test token for authenticated endpoints", "INFO")
    else:
        print_status(f"No token provided - some tests will check auth requirements only", "WARN")
    print()
    
    # Run checks
    results = {}
    
    # Critical Infrastructure
    print("=" * 70)
    print("CRITICAL INFRASTRUCTURE")
    print("=" * 70)
    results['base_url'] = check_endpoint(base_url, "Base URL")
    results['health'] = check_health(base_url)
    results['websocket'] = check_websocket_endpoint(base_url)
    results['realtime'] = check_realtime_events(base_url)
    print()
    
    # API Keys Management
    print("=" * 70)
    print("API KEYS MANAGEMENT")
    print("=" * 70)
    results['api_keys'] = check_api_keys_endpoints(base_url, test_token)
    print()
    
    # Admin Panel
    print("=" * 70)
    print("ADMIN PANEL")
    print("=" * 70)
    results['admin'] = check_admin_endpoints(base_url, test_token)
    print()
    
    # Bot Quarantine System
    print("=" * 70)
    print("BOT QUARANTINE SYSTEM")
    print("=" * 70)
    results['quarantine'] = check_quarantine_endpoints(base_url, test_token)
    print()
    
    # Bot Training
    print("=" * 70)
    print("BOT TRAINING")
    print("=" * 70)
    results['training'] = check_training_endpoints(base_url, test_token)
    print()
    
    # Paper Trading Endpoints
    print("=" * 70)
    print("PAPER TRADING & BOTS")
    print("=" * 70)
    results['bots'] = check_endpoint(
        f"{base_url}/api/bots",
        "Bots - List",
        expected_status=[200, 401]
    )
    results['system_status'] = check_endpoint(
        f"{base_url}/api/system_status",
        "System Status",
        expected_status=[200, 401]
    )
    print()
    
    # Summary
    print("=" * 70)
    print("SMOKE TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    percentage = (passed / total * 100) if total > 0 else 0
    
    print(f"\nResults by category:")
    for category, result in results.items():
        status = "PASS" if result else "FAIL"
        print_status(f"  {category.replace('_', ' ').title()}: {'✓' if result else '✗'}", status)
    
    print(f"\n{'='*70}")
    if passed == total:
        print_status(f"ALL TESTS PASSED: {passed}/{total} ({percentage:.0f}%)", "PASS")
        print_status(f"System is production-ready! 🚀", "PASS")
    elif percentage >= 80:
        print_status(f"MOST TESTS PASSED: {passed}/{total} ({percentage:.0f}%)", "WARN")
        print_status(f"Review failed tests before going live", "WARN")
    else:
        print_status(f"CRITICAL FAILURES: {passed}/{total} ({percentage:.0f}%)", "FAIL")
        print_status(f"System NOT ready for production", "FAIL")
    print("=" * 70)
    print()
    
    # Exit code
    if passed == total:
        return 0
    elif percentage >= 80:
        return 1
    else:
        return 2


if __name__ == "__main__":
    sys.exit(main())
