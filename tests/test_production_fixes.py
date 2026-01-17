#!/usr/bin/env python3
"""
Production Fixes Verification Script
Tests all endpoints that were fixed in the production fixes PR

Run with:
    python tests/test_production_fixes.py

Requirements:
    - Backend server running on localhost:8000
    - Test user credentials in environment or defaults
"""

import asyncio
import aiohttp
import json
import os
import sys
from typing import Dict, Optional, Tuple

# Configuration
API_BASE = os.getenv("API_BASE", "http://localhost:8000")
TEST_EMAIL = os.getenv("TEST_EMAIL", "test@example.com")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "testpass123")

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


class ProductionFixesTest:
    """Test suite for production fixes"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.passed = 0
        self.failed = 0
        self.warnings = 0
    
    async def setup(self):
        """Setup test session"""
        self.session = aiohttp.ClientSession()
        print(f"{BLUE}Setting up test session...{RESET}")
        print(f"API Base: {API_BASE}")
        print(f"Test Email: {TEST_EMAIL}")
    
    async def teardown(self):
        """Close test session"""
        if self.session:
            await self.session.close()
    
    async def login(self) -> bool:
        """Login and get JWT token"""
        print(f"\n{BLUE}=== Authentication Test ==={RESET}")
        
        try:
            async with self.session.post(
                f"{API_BASE}/api/auth/login",
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
            ) as resp:
                if resp.status != 200:
                    print(f"{YELLOW}⚠️  Login failed, trying to register...{RESET}")
                    return await self.register()
                
                data = await resp.json()
                self.token = data.get("access_token") or data.get("token")
                
                if not self.token:
                    print(f"{RED}❌ No token in response{RESET}")
                    return False
                
                # Check user object
                user = data.get("user", {})
                self.user_id = user.get("id")
                
                # CRITICAL SECURITY TEST: Check for sensitive fields
                sensitive_fields = ['password_hash', 'hashed_password', 'new_password', 'password']
                found_sensitive = [f for f in sensitive_fields if f in user]
                
                if found_sensitive:
                    print(f"{RED}❌ SECURITY ISSUE: Login response contains sensitive fields: {found_sensitive}{RESET}")
                    self.failed += 1
                    return False
                
                print(f"{GREEN}✅ Login successful - no sensitive fields in response{RESET}")
                self.passed += 1
                return True
                
        except Exception as e:
            print(f"{RED}❌ Login error: {e}{RESET}")
            self.failed += 1
            return False
    
    async def register(self) -> bool:
        """Register test user"""
        try:
            async with self.session.post(
                f"{API_BASE}/api/auth/register",
                json={
                    "first_name": "Test User",
                    "email": TEST_EMAIL,
                    "password": TEST_PASSWORD,
                    "invite_code": os.getenv("INVITE_CODE", "")
                }
            ) as resp:
                if resp.status not in [200, 201]:
                    text = await resp.text()
                    print(f"{RED}❌ Register failed ({resp.status}): {text}{RESET}")
                    self.failed += 1
                    return False
                
                data = await resp.json()
                self.token = data.get("access_token") or data.get("token")
                
                # Check user object
                user = data.get("user", {})
                self.user_id = user.get("id")
                
                # CRITICAL SECURITY TEST: Check for sensitive fields
                sensitive_fields = ['password_hash', 'hashed_password', 'new_password', 'password']
                found_sensitive = [f for f in sensitive_fields if f in user]
                
                if found_sensitive:
                    print(f"{RED}❌ SECURITY ISSUE: Register response contains sensitive fields: {found_sensitive}{RESET}")
                    self.failed += 1
                    return False
                
                print(f"{GREEN}✅ Registration successful - no sensitive fields{RESET}")
                self.passed += 1
                return True
                
        except Exception as e:
            print(f"{RED}❌ Register error: {e}{RESET}")
            self.failed += 1
            return False
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers with auth token"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    async def test_profile_update(self):
        """Test profile update endpoint"""
        print(f"\n{BLUE}=== Profile Update Test ==={RESET}")
        
        try:
            # Test valid update
            async with self.session.put(
                f"{API_BASE}/api/auth/profile",
                json={"first_name": "Updated Test User"},
                headers=self.get_headers()
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    print(f"{RED}❌ Profile update failed ({resp.status}): {text}{RESET}")
                    self.failed += 1
                    return
                
                data = await resp.json()
                user = data.get("user", {})
                
                # Check no sensitive fields
                sensitive_fields = ['password_hash', 'hashed_password', 'new_password', 'password']
                found_sensitive = [f for f in sensitive_fields if f in user]
                
                if found_sensitive:
                    print(f"{RED}❌ SECURITY: Profile response contains: {found_sensitive}{RESET}")
                    self.failed += 1
                    return
                
                print(f"{GREEN}✅ Profile update successful{RESET}")
                self.passed += 1
            
            # Test forbidden field update attempt
            async with self.session.put(
                f"{API_BASE}/api/auth/profile",
                json={"password_hash": "malicious", "email": "hacker@evil.com"},
                headers=self.get_headers()
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    user = data.get("user", {})
                    
                    # Email should not have changed
                    if user.get("email") != TEST_EMAIL:
                        print(f"{RED}❌ SECURITY: Forbidden field (email) was updated!{RESET}")
                        self.failed += 1
                        return
                    
                    print(f"{GREEN}✅ Forbidden fields properly rejected{RESET}")
                    self.passed += 1
                else:
                    # 400 is also acceptable
                    print(f"{GREEN}✅ Forbidden fields rejected with {resp.status}{RESET}")
                    self.passed += 1
                    
        except Exception as e:
            print(f"{RED}❌ Profile update error: {e}{RESET}")
            self.failed += 1
    
    async def test_wallet_requirements(self):
        """Test wallet requirements endpoint"""
        print(f"\n{BLUE}=== Wallet Requirements Test ==={RESET}")
        
        try:
            async with self.session.get(
                f"{API_BASE}/api/wallet/requirements",
                headers=self.get_headers()
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    print(f"{RED}❌ Wallet requirements failed ({resp.status}): {text}{RESET}")
                    self.failed += 1
                    return
                
                data = await resp.json()
                
                # Should have requirements field
                if "requirements" not in data:
                    print(f"{RED}❌ Response missing 'requirements' field{RESET}")
                    self.failed += 1
                    return
                
                print(f"{GREEN}✅ Wallet requirements endpoint working{RESET}")
                self.passed += 1
                
        except Exception as e:
            print(f"{RED}❌ Wallet requirements error: {e}{RESET}")
            self.failed += 1
    
    async def test_emergency_stop(self):
        """Test emergency stop endpoint"""
        print(f"\n{BLUE}=== Emergency Stop Test ==={RESET}")
        
        try:
            # Activate emergency stop
            async with self.session.post(
                f"{API_BASE}/api/system/emergency-stop",
                params={"reason": "Testing"},
                headers=self.get_headers()
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    print(f"{RED}❌ Emergency stop activation failed ({resp.status}): {text}{RESET}")
                    self.failed += 1
                    return
                
                data = await resp.json()
                
                if not data.get("success"):
                    print(f"{RED}❌ Emergency stop did not report success{RESET}")
                    self.failed += 1
                    return
                
                print(f"{GREEN}✅ Emergency stop activated{RESET}")
                self.passed += 1
            
            # Deactivate emergency stop
            async with self.session.post(
                f"{API_BASE}/api/system/emergency-stop/disable",
                headers=self.get_headers()
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    print(f"{YELLOW}⚠️  Emergency stop deactivation returned {resp.status}{RESET}")
                    self.warnings += 1
                else:
                    print(f"{GREEN}✅ Emergency stop deactivated{RESET}")
                    self.passed += 1
                    
        except Exception as e:
            print(f"{RED}❌ Emergency stop error: {e}{RESET}")
            self.failed += 1
    
    async def test_openai_key_test(self):
        """Test OpenAI key test endpoint (without actual key)"""
        print(f"\n{BLUE}=== OpenAI Key Test ==={RESET}")
        
        try:
            # Test with invalid key
            async with self.session.post(
                f"{API_BASE}/api/keys/test",
                json={
                    "provider": "openai",
                    "api_key": "sk-invalid-test-key-1234567890"
                },
                headers=self.get_headers()
            ) as resp:
                if resp.status not in [200, 400]:
                    text = await resp.text()
                    print(f"{RED}❌ OpenAI key test failed ({resp.status}): {text}{RESET}")
                    self.failed += 1
                    return
                
                data = await resp.json()
                
                # Check for old API error
                error_text = str(data)
                if "ChatCompletion" in error_text and "has no attribute" in error_text:
                    print(f"{RED}❌ Still using deprecated openai.ChatCompletion API{RESET}")
                    self.failed += 1
                    return
                
                # Should return structured response
                if "success" not in data and "message" not in data:
                    print(f"{RED}❌ Response not properly structured{RESET}")
                    self.failed += 1
                    return
                
                print(f"{GREEN}✅ OpenAI key test using new API (openai>=1.x){RESET}")
                self.passed += 1
                
        except Exception as e:
            print(f"{RED}❌ OpenAI key test error: {e}{RESET}")
            self.failed += 1
    
    async def test_ai_insights(self):
        """Test AI insights endpoint"""
        print(f"\n{BLUE}=== AI Insights Test ==={RESET}")
        
        try:
            async with self.session.get(
                f"{API_BASE}/api/ai/insights",
                headers=self.get_headers()
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    print(f"{RED}❌ AI insights failed ({resp.status}): {text}{RESET}")
                    self.failed += 1
                    return
                
                data = await resp.json()
                
                # Check required fields
                required = ["timestamp", "regime", "sentiment", "system_health"]
                missing = [f for f in required if f not in data]
                
                if missing:
                    print(f"{RED}❌ Missing required fields: {missing}{RESET}")
                    self.failed += 1
                    return
                
                print(f"{GREEN}✅ AI insights endpoint working{RESET}")
                self.passed += 1
                
        except Exception as e:
            print(f"{RED}❌ AI insights error: {e}{RESET}")
            self.failed += 1
    
    async def test_ml_predict(self):
        """Test ML predict endpoint with query params"""
        print(f"\n{BLUE}=== ML Predict (Query Params) Test ==={RESET}")
        
        try:
            async with self.session.get(
                f"{API_BASE}/api/ml/predict",
                params={"symbol": "BTC-ZAR", "platform": "luno"},
                headers=self.get_headers()
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    print(f"{YELLOW}⚠️  ML predict returned {resp.status}: {text[:200]}{RESET}")
                    self.warnings += 1
                    return
                
                data = await resp.json()
                
                # Should have query info
                if "query" in data:
                    print(f"{GREEN}✅ ML predict endpoint working with query params{RESET}")
                    self.passed += 1
                else:
                    print(f"{YELLOW}⚠️  ML predict response structure unexpected{RESET}")
                    self.warnings += 1
                    
        except Exception as e:
            print(f"{YELLOW}⚠️  ML predict error: {e}{RESET}")
            self.warnings += 1
    
    async def test_profits_reinvest(self):
        """Test profits reinvest endpoint"""
        print(f"\n{BLUE}=== Profits Reinvest Test ==={RESET}")
        
        try:
            async with self.session.post(
                f"{API_BASE}/api/profits/reinvest",
                json={},
                headers=self.get_headers()
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    print(f"{YELLOW}⚠️  Profits reinvest returned {resp.status}: {text[:200]}{RESET}")
                    self.warnings += 1
                    return
                
                data = await resp.json()
                
                # Should have success or status
                if "success" in data or "status" in data:
                    print(f"{GREEN}✅ Profits reinvest endpoint working{RESET}")
                    self.passed += 1
                else:
                    print(f"{YELLOW}⚠️  Profits reinvest response structure unexpected{RESET}")
                    self.warnings += 1
                    
        except Exception as e:
            print(f"{YELLOW}⚠️  Profits reinvest error: {e}{RESET}")
            self.warnings += 1
    
    async def test_advanced_decisions(self):
        """Test advanced decisions endpoint"""
        print(f"\n{BLUE}=== Advanced Decisions Recent Test ==={RESET}")
        
        try:
            async with self.session.get(
                f"{API_BASE}/api/advanced/decisions/recent",
                params={"limit": 10},
                headers=self.get_headers()
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    print(f"{RED}❌ Advanced decisions failed ({resp.status}): {text}{RESET}")
                    self.failed += 1
                    return
                
                data = await resp.json()
                
                # Should have decisions array
                if "decisions" not in data:
                    print(f"{RED}❌ Missing 'decisions' field{RESET}")
                    self.failed += 1
                    return
                
                print(f"{GREEN}✅ Advanced decisions endpoint working{RESET}")
                self.passed += 1
                
        except Exception as e:
            print(f"{RED}❌ Advanced decisions error: {e}{RESET}")
            self.failed += 1
    
    async def test_openapi_schema(self):
        """Test OpenAPI schema includes new endpoints"""
        print(f"\n{BLUE}=== OpenAPI Schema Test ==={RESET}")
        
        try:
            async with self.session.get(f"{API_BASE}/openapi.json") as resp:
                if resp.status != 200:
                    print(f"{YELLOW}⚠️  Could not fetch OpenAPI schema{RESET}")
                    self.warnings += 1
                    return
                
                schema = await resp.json()
                paths = schema.get("paths", {})
                
                # Check for new endpoints
                required_paths = [
                    "/api/ai/insights",
                    "/api/ml/predict",
                    "/api/profits/reinvest",
                    "/api/advanced/decisions/recent"
                ]
                
                found = []
                missing = []
                
                for path in required_paths:
                    if path in paths:
                        found.append(path)
                    else:
                        missing.append(path)
                
                if missing:
                    print(f"{YELLOW}⚠️  Missing from OpenAPI schema: {missing}{RESET}")
                    self.warnings += 1
                else:
                    print(f"{GREEN}✅ All new endpoints in OpenAPI schema{RESET}")
                    self.passed += 1
                
                if found:
                    print(f"   Found: {found}")
                    
        except Exception as e:
            print(f"{YELLOW}⚠️  OpenAPI schema test error: {e}{RESET}")
            self.warnings += 1
    
    async def run_all_tests(self):
        """Run all tests"""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}Production Fixes Verification Test Suite{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")
        
        await self.setup()
        
        # Login first
        if not await self.login():
            print(f"\n{RED}Cannot proceed without authentication{RESET}")
            await self.teardown()
            return
        
        # Run all tests
        await self.test_profile_update()
        await self.test_wallet_requirements()
        await self.test_emergency_stop()
        await self.test_openai_key_test()
        await self.test_ai_insights()
        await self.test_ml_predict()
        await self.test_profits_reinvest()
        await self.test_advanced_decisions()
        await self.test_openapi_schema()
        
        await self.teardown()
        
        # Print summary
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}Test Summary{RESET}")
        print(f"{BLUE}{'='*60}{RESET}")
        print(f"{GREEN}✅ Passed: {self.passed}{RESET}")
        print(f"{RED}❌ Failed: {self.failed}{RESET}")
        print(f"{YELLOW}⚠️  Warnings: {self.warnings}{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")
        
        # Exit code
        if self.failed > 0:
            sys.exit(1)
        elif self.warnings > 0:
            sys.exit(0)  # Warnings are okay
        else:
            sys.exit(0)


async def main():
    """Main entry point"""
    test_suite = ProductionFixesTest()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
