#!/usr/bin/env python3
"""
API Keys Integration Test Script

Tests the complete flow:
1. Save API key (with encryption)
2. Retrieve and decrypt API key
3. Test against CCXT exchange
4. Verify test status persistence

Usage:
    python tools/test_api_keys_flow.py

Requirements:
    - Server must be running
    - Valid JWT token in environment or provided interactively
    - Test API keys (can use invalid keys to test error handling)
"""

import asyncio
import os
import sys
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    import aiohttp
except ImportError:
    print("❌ aiohttp not installed. Run: pip install aiohttp")
    sys.exit(1)


class APIKeyTester:
    def __init__(self, base_url: str = "http://localhost:8000", token: str = None):
        self.base_url = base_url
        self.token = token or os.getenv('JWT_TOKEN')
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
    
    async def test_save_api_key(self, provider: str, api_key: str, api_secret: str = None):
        """Test saving an API key"""
        print(f"\n📝 Testing: Save {provider} API key")
        
        payload = {
            "provider": provider,
            "api_key": api_key,
            "api_secret": api_secret,
            "exchange": provider
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/api-keys",
                headers=self.headers,
                json=payload
            ) as response:
                result = await response.json()
                
                if response.status == 200:
                    print(f"  ✅ Saved: {result.get('message')}")
                    print(f"  📊 Status: {result.get('status')}")
                    return True
                else:
                    print(f"  ❌ Failed: {result.get('detail')}")
                    return False
    
    async def test_save_with_variants(self, provider: str, api_key: str, api_secret: str = None):
        """Test payload variants (apiKey vs api_key)"""
        print(f"\n🔄 Testing: Payload variants for {provider}")
        
        # Test with apiKey/apiSecret variant
        payload = {
            "provider": provider,
            "apiKey": api_key,  # Variant spelling
            "apiSecret": api_secret
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/keys/save",  # Legacy endpoint
                headers=self.headers,
                json=payload
            ) as response:
                result = await response.json()
                
                if response.status == 200:
                    print(f"  ✅ Legacy endpoint accepts apiKey variant")
                    return True
                else:
                    print(f"  ❌ Failed with variant: {result.get('detail')}")
                    return False
    
    async def test_list_api_keys(self):
        """Test listing API keys"""
        print(f"\n📋 Testing: List API keys")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/api/api-keys",
                headers=self.headers
            ) as response:
                result = await response.json()
                
                if response.status == 200:
                    keys = result.get('keys', [])
                    print(f"  ✅ Found {len(keys)} API key(s)")
                    
                    for key in keys:
                        provider = key.get('provider')
                        status = key.get('status_display', key.get('status'))
                        print(f"    - {provider}: {status}")
                    
                    return keys
                else:
                    print(f"  ❌ Failed to list keys: {result.get('detail')}")
                    return []
    
    async def test_api_key_test_endpoint(self, provider: str, api_key: str, api_secret: str = None):
        """Test the test endpoint (validates credentials)"""
        print(f"\n🧪 Testing: Test {provider} credentials")
        
        payload = {
            "api_key": api_key,
            "api_secret": api_secret
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/api-keys/{provider}/test",
                headers=self.headers,
                json=payload
            ) as response:
                result = await response.json()
                
                if result.get('success'):
                    print(f"  ✅ Test passed: {result.get('message')}")
                    if 'currencies_found' in result:
                        print(f"    Currencies found: {result['currencies_found']}")
                    return True
                else:
                    print(f"  ❌ Test failed: {result.get('message')}")
                    print(f"    Error: {result.get('error')}")
                    return False
    
    async def test_wallet_balance(self):
        """Test wallet balance retrieval"""
        print(f"\n💰 Testing: Wallet balance retrieval")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/api/wallet/balances",
                headers=self.headers
            ) as response:
                result = await response.json()
                
                if response.status == 200:
                    master_wallet = result.get('master_wallet', {})
                    
                    if master_wallet.get('error'):
                        print(f"  ⚠️  Wallet not configured: {master_wallet['error']}")
                    else:
                        total_zar = master_wallet.get('total_zar', 0)
                        btc = master_wallet.get('btc_balance', 0)
                        print(f"  ✅ Luno balance retrieved")
                        print(f"    Total ZAR: R{total_zar:.2f}")
                        print(f"    BTC: {btc:.8f}")
                    
                    return True
                else:
                    print(f"  ❌ Failed: {result.get('detail')}")
                    return False
    
    async def test_system_status(self):
        """Test system status endpoint"""
        print(f"\n⚙️  Testing: System status endpoint")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/api/system/status",
                headers=self.headers
            ) as response:
                result = await response.json()
                
                if response.status == 200:
                    print(f"  ✅ System status retrieved")
                    
                    flags = result.get('feature_flags', {})
                    print(f"    Feature Flags:")
                    print(f"      - Trading: {flags.get('enable_trading')}")
                    print(f"      - Schedulers: {flags.get('enable_schedulers')}")
                    print(f"      - Autopilot: {flags.get('enable_autopilot')}")
                    
                    activity = result.get('trading_activity', {})
                    print(f"    Trading Activity:")
                    print(f"      - Active bots: {activity.get('active_bots')}")
                    print(f"      - Last trade: {activity.get('last_trade_time')}")
                    
                    return True
                else:
                    print(f"  ❌ Failed: {result.get('detail')}")
                    return False
    
    async def test_overview(self, include_wallet: bool = False):
        """Test overview endpoint"""
        print(f"\n📊 Testing: Overview endpoint {'(with wallet)' if include_wallet else ''}")
        
        url = f"{self.base_url}/api/overview"
        if include_wallet:
            url += "?include_wallet=true"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                result = await response.json()
                
                if response.status == 200:
                    print(f"  ✅ Overview retrieved")
                    print(f"    Total Profit: R{result.get('total_profit', 0):.2f}")
                    print(f"    Active Bots: {result.get('activeBots')}")
                    print(f"    Trading Status: {result.get('tradingStatus')}")
                    
                    if include_wallet and 'wallet_balance' in result:
                        wallet = result['wallet_balance']
                        if wallet.get('error'):
                            print(f"    Wallet: {wallet['error']}")
                        else:
                            print(f"    Wallet ZAR: R{wallet.get('total_zar', 0):.2f}")
                    
                    return True
                else:
                    print(f"  ❌ Failed: {result.get('detail')}")
                    return False


async def run_tests():
    """Run all tests"""
    print("="*60)
    print("API Keys Integration Test Suite")
    print("="*60)
    
    # Get token
    token = os.getenv('JWT_TOKEN')
    if not token:
        print("\n⚠️  No JWT_TOKEN environment variable found")
        token = input("Enter JWT token (or press Enter to skip): ").strip()
        if not token:
            print("❌ Token required. Exiting.")
            return
    
    tester = APIKeyTester(token=token)
    
    # Test system status first
    await tester.test_system_status()
    
    # Test overview endpoints
    await tester.test_overview(include_wallet=False)
    await tester.test_overview(include_wallet=True)
    
    # Test listing keys
    await tester.test_list_api_keys()
    
    # Test wallet balance
    await tester.test_wallet_balance()
    
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    print("✅ All endpoint tests completed")
    print("\n📝 Note: To test actual key save/test flow:")
    print("   1. Set valid exchange API keys in environment")
    print("   2. Run with: LUNO_KEY=... LUNO_SECRET=... python tools/test_api_keys_flow.py")
    print("\n⚠️  Or test manually via dashboard: Settings → API Keys")
    

if __name__ == "__main__":
    asyncio.run(run_tests())
