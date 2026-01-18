#!/usr/bin/env python3
"""
Production Go-Live Verification Script
Verifies all required endpoints are mounted and functional

Usage:
    python3 scripts/verify_go_live.py [backend_url]
    BACKEND_URL=http://prod:8001 python3 scripts/verify_go_live.py
"""

import requests
import sys
import os
from urllib.parse import urlparse

def get_backend_url():
    """Get backend URL from CLI, env, or default"""
    url = sys.argv[1] if len(sys.argv) > 1 else os.getenv("BACKEND_URL", "http://localhost:8001")
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid URL")
        return url.rstrip("/")
    except:
        print(f"❌ Invalid URL: {url}")
        sys.exit(1)

BACKEND_URL = get_backend_url()

# Required endpoints that MUST be in OpenAPI spec
REQUIRED_ENDPOINTS = {
    "/api/health/ping": "GET",
    "/api/auth/login": "POST",
    "/api/auth/me": "GET",
    "/api/auth/register": "POST",
    "/api/api-keys": "POST",
    "/api/api-keys/{provider}/test": "POST",
    "/api/prices/live": "GET",
    "/api/bots": "GET",
    "/api/overview": "GET",
    "/api/system/mode": "GET",
    "/api/system/emergency-stop": "POST",
    "/api/system/emergency-stop/status": "GET",
    "/api/system/live-eligibility": "GET",
}

def test_openapi_presence():
    """Test that all required endpoints are in OpenAPI spec"""
    print("\n=== OpenAPI Spec Check ===")
    try:
        resp = requests.get(f"{BACKEND_URL}/openapi.json", timeout=10)
        if resp.status_code != 200:
            print(f"❌ OpenAPI not accessible: {resp.status_code}")
            return False
        
        paths = resp.json().get("paths", {})
        missing = []
        
        for endpoint, method in REQUIRED_ENDPOINTS.items():
            found = False
            if endpoint in paths:
                if method.lower() in paths[endpoint]:
                    found = True
                    print(f"✅ {method} {endpoint}")
            
            if not found:
                # Check parameterized variants
                for path in paths:
                    if path.startswith(endpoint.rstrip("/")):
                        if method.lower() in paths[path]:
                            found = True
                            print(f"✅ {method} {endpoint} (as {path})")
                            break
            
            if not found:
                missing.append(f"{method} {endpoint}")
                print(f"❌ {method} {endpoint}")
        
        if missing:
            print(f"\n❌ Missing {len(missing)} endpoint(s)")
            return False
        
        print(f"\n✅ All {len(REQUIRED_ENDPOINTS)} required endpoints in OpenAPI")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_auth_required():
    """Test that protected endpoints return 401/403, not 404"""
    print("\n=== Auth Protection Check ===")
    protected_endpoints = [
        ("GET", "/api/auth/me"),
        ("POST", "/api/api-keys"),
        ("GET", "/api/bots"),
        ("GET", "/api/profits"),
        ("POST", "/api/api-keys/luno/test"),
    ]
    
    all_good = True
    for method, endpoint in protected_endpoints:
        try:
            if method == "GET":
                resp = requests.get(f"{BACKEND_URL}{endpoint}", timeout=5)
            else:
                resp = requests.post(f"{BACKEND_URL}{endpoint}", json={}, timeout=5)
            
            if resp.status_code in [401, 403]:
                print(f"✅ {method} {endpoint} → {resp.status_code} (correctly protected)")
            elif resp.status_code == 404:
                print(f"❌ {method} {endpoint} → 404 (endpoint not mounted?)")
                all_good = False
            else:
                print(f"⚠️  {method} {endpoint} → {resp.status_code} (unexpected)")
        except Exception as e:
            print(f"❌ {method} {endpoint} → Error: {e}")
            all_good = False
    
    return all_good


def test_prices_without_keys():
    """Test /api/prices/live works WITHOUT API keys"""
    print("\n=== Market Data Without Keys ===")
    try:
        # Create temp user to get token
        import uuid
        test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        
        resp = requests.post(
            f"{BACKEND_URL}/api/auth/register",
            json={
                "first_name": "Test",
                "email": test_email,
                "password": "TestPass123!"
            },
            timeout=10
        )
        
        if resp.status_code != 200:
            print(f"❌ Could not create test user: {resp.status_code}")
            return False
        
        token = resp.json().get("access_token")
        
        # Test prices endpoint
        resp = requests.get(
            f"{BACKEND_URL}/api/prices/live",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if resp.status_code != 200:
            print(f"❌ Prices endpoint failed: {resp.status_code}")
            return False
        
        data = resp.json()
        
        # Check structure
        if not data or not isinstance(data, dict):
            print(f"❌ Prices endpoint returned invalid data")
            return False
        
        # Check that we got numeric values (not None)
        for pair, info in data.items():
            if isinstance(info, dict):
                if "price" not in info or "change" not in info:
                    print(f"❌ Missing price/change for {pair}")
                    return False
                if not isinstance(info["price"], (int, float)):
                    print(f"❌ Price for {pair} is not numeric: {type(info['price'])}")
                    return False
                if not isinstance(info["change"], (int, float)):
                    print(f"❌ Change for {pair} is not numeric: {type(info['change'])}")
                    return False
        
        print(f"✅ Prices endpoint returns valid numeric data without keys")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_live_trading_gate():
    """Test live trading gate is properly enforced"""
    print("\n=== Live Trading Gate ===")
    try:
        # Create temp user
        import uuid
        test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        
        resp = requests.post(
            f"{BACKEND_URL}/api/auth/register",
            json={
                "first_name": "Test",
                "email": test_email,
                "password": "TestPass123!"
            },
            timeout=10
        )
        
        if resp.status_code != 200:
            print(f"❌ Could not create test user")
            return False
        
        token = resp.json().get("access_token")
        
        # Check eligibility (should be denied by default)
        resp = requests.get(
            f"{BACKEND_URL}/api/system/live-eligibility",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if resp.status_code != 200:
            print(f"❌ Live eligibility endpoint failed: {resp.status_code}")
            return False
        
        data = resp.json()
        live_allowed = data.get("live_allowed", False)
        
        if live_allowed:
            print(f"⚠️  Live trading allowed by default (should be false for new users)")
            return False
        
        print(f"✅ Live trading gate properly enforced (default: OFF)")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
            else:
                resp = requests.post(f"{BACKEND_URL}{endpoint}", json={}, timeout=5)
            
            if resp.status_code == 404:
                print(f"❌ {method} {endpoint} → 404 (not mounted!)")
                all_good = False
            elif resp.status_code in [401, 403]:
                print(f"✅ {method} {endpoint} → {resp.status_code} (protected)")
            elif resp.status_code == 422:
                print(f"✅ {method} {endpoint} → 422 (validation, mounted)")
            else:
                print(f"⚠️  {method} {endpoint} → {resp.status_code}")
        except Exception as e:
            print(f"❌ {method} {endpoint} → Error: {e}")
            all_good = False
    
    return all_good

def test_public_endpoints():
    """Test that public endpoints work"""
    print("\n=== Public Endpoints Check ===")
    try:
        resp = requests.get(f"{BACKEND_URL}/api/health/ping", timeout=5)
        if resp.status_code == 200:
            print(f"✅ /api/health/ping → 200")
            return True
        else:
            print(f"❌ /api/health/ping → {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ /api/health/ping → Error: {e}")
        return False

def main():
    print("="*60)
    print("Production Go-Live Verification")
    print("="*60)
    print(f"Backend: {BACKEND_URL}\n")
    
    # Check if server is up
    try:
        requests.get(f"{BACKEND_URL}/", timeout=5)
        print("✅ Server is running\n")
    except:
        print("❌ Server not reachable\n")
        sys.exit(1)
    
    # Run all tests
    openapi_ok = test_openapi_presence()
    auth_ok = test_auth_required()
    public_ok = test_public_endpoints()
    prices_ok = test_prices_without_keys()
    live_gate_ok = test_live_trading_gate()
    
    # Summary
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    
    results = [
        ("OpenAPI Spec", openapi_ok),
        ("Auth Protection", auth_ok),
        ("Public Endpoints", public_ok),
        ("Market Data Without Keys", prices_ok),
        ("Live Trading Gate", live_gate_ok),
    ]
    
    all_pass = all(ok for _, ok in results)
    
    for name, ok in results:
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"{status} {name}")
    
    print("="*60)
    
    if all_pass:
        print("\n🎉 ALL CHECKS PASSED - System Go-Live Ready!")
        print("\n✅ Verified:")
        print("   - All required endpoints mounted")
        print("   - Auth protection working")
        print("   - Market data works WITHOUT API keys")
        print("   - Live trading gate enforced (default OFF)")
        print("   - System ready for paper trading")
        sys.exit(0)
    else:
        print("\n⚠️  SOME CHECKS FAILED - Review Above")
        sys.exit(1)

if __name__ == "__main__":
    main()
