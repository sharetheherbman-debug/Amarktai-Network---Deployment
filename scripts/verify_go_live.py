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
    "/api/wallet/requirements": "GET",
    "/api/system/emergency-stop": "POST",
    "/api/auth/profile": "GET",
    "/api/ai/insights": "GET",
    "/api/ml/predict": "GET",
    "/api/profits/reinvest": "POST",
    "/api/advanced/decisions/recent": "GET",
    "/api/keys/test": "POST",
    "/api/health/ping": "GET",
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
        ("GET", "/api/wallet/requirements"),
        ("POST", "/api/system/emergency-stop"),
        ("GET", "/api/auth/profile"),
        ("GET", "/api/ai/insights"),
        ("GET", "/api/ml/predict"),
        ("POST", "/api/profits/reinvest"),
        ("GET", "/api/advanced/decisions/recent"),
        ("POST", "/api/keys/test"),
    ]
    
    all_good = True
    for method, endpoint in protected_endpoints:
        try:
            if method == "GET":
                resp = requests.get(f"{BACKEND_URL}{endpoint}", timeout=5)
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
    
    # Summary
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    
    results = [
        ("OpenAPI Spec", openapi_ok),
        ("Auth Protection", auth_ok),
        ("Public Endpoints", public_ok),
    ]
    
    all_pass = all(ok for _, ok in results)
    
    for name, ok in results:
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"{status} {name}")
    
    print("="*60)
    
    if all_pass:
        print("\n🎉 ALL CHECKS PASSED - Production Ready")
        sys.exit(0)
    else:
        print("\n⚠️  SOME CHECKS FAILED - Review Above")
        sys.exit(1)

if __name__ == "__main__":
    main()
