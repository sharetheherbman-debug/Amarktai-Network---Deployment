"""
Test Endpoint Compatibility and Dashboard Requirements
Tests that all required endpoints exist, return proper status codes, and don't leak sensitive data
"""

import pytest
from httpx import AsyncClient
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from server import app
import database as db


@pytest.fixture(scope="module")
async def client():
    """Create test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="module", autouse=True)
async def setup_db():
    """Setup database connection"""
    await db.connect()
    yield
    await db.close_db()


@pytest.fixture(scope="module")
async def auth_token(client):
    """Create test user and return auth token"""
    from uuid import uuid4
    
    test_email = f"test_compat_{uuid4().hex[:8]}@example.com"
    test_password = "testpass123"
    
    # Register user
    response = await client.post(
        "/api/auth/register",
        json={
            "first_name": "Test",
            "email": test_email,
            "password": test_password
        }
    )
    
    assert response.status_code == 200, f"Registration failed: {response.text}"
    data = response.json()
    token = data.get("access_token") or data.get("token")
    
    yield token
    
    # Cleanup
    await db.users_collection.delete_one({"email": test_email.lower()})


class TestEndpointExistence:
    """Test that all required endpoints exist and return proper status codes"""
    
    @pytest.mark.asyncio
    async def test_openapi_json_available(self, client):
        """Test that /openapi.json is accessible"""
        response = await client.get("/openapi.json")
        assert response.status_code == 200, "OpenAPI JSON should be accessible"
        
        openapi_spec = response.json()
        assert "openapi" in openapi_spec
        assert "paths" in openapi_spec
    
    @pytest.mark.asyncio
    async def test_health_ping_endpoint(self, client):
        """Test GET /api/health/ping returns 200"""
        response = await client.get("/api/health/ping")
        assert response.status_code == 200, "/api/health/ping should return 200"
    
    @pytest.mark.asyncio
    async def test_required_endpoints_in_openapi(self, client):
        """Test that all required endpoints are present in OpenAPI spec"""
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        
        openapi_spec = response.json()
        paths = openapi_spec.get("paths", {})
        
        required_endpoints = [
            "/api/wallet/requirements",
            "/api/system/emergency-stop",
            "/api/auth/profile",
            "/api/ai/insights",
            "/api/ml/predict",
            "/api/profits/reinvest",
            "/api/advanced/decisions/recent",
            "/api/keys/test",
        ]
        
        missing_endpoints = []
        for endpoint in required_endpoints:
            if endpoint not in paths:
                # Check if it's a parameterized endpoint
                if "{" not in endpoint and not any(endpoint in path for path in paths.keys()):
                    missing_endpoints.append(endpoint)
        
        assert len(missing_endpoints) == 0, f"Missing endpoints in OpenAPI: {missing_endpoints}"
    
    @pytest.mark.asyncio
    async def test_wallet_requirements_endpoint(self, client, auth_token):
        """Test GET /api/wallet/requirements is accessible"""
        response = await client.get(
            "/api/wallet/requirements",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, "/api/wallet/requirements should return 200"
        
        data = response.json()
        assert "user_id" in data
        assert "requirements" in data
        assert "summary" in data
    
    @pytest.mark.asyncio
    async def test_emergency_stop_endpoints(self, client, auth_token):
        """Test emergency stop endpoints exist and are accessible"""
        # Test status endpoint
        response = await client.get(
            "/api/system/emergency-stop/status",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, "Emergency stop status should return 200"
        
        # Test activate endpoint (just check it exists, don't activate)
        # We'll send a POST but verify the response format without actually activating
    
    @pytest.mark.asyncio
    async def test_ai_insights_endpoint(self, client, auth_token):
        """Test GET /api/ai/insights is accessible"""
        response = await client.get(
            "/api/ai/insights",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, "/api/ai/insights should return 200"
        
        data = response.json()
        assert "timestamp" in data
        assert "user_id" in data
    
    @pytest.mark.asyncio
    async def test_ml_predict_endpoint(self, client, auth_token):
        """Test GET /api/ml/predict with query params"""
        response = await client.get(
            "/api/ml/predict?symbol=BTC-ZAR&platform=luno",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, "/api/ml/predict should return 200"
    
    @pytest.mark.asyncio
    async def test_profits_reinvest_endpoint(self, client, auth_token):
        """Test POST /api/profits/reinvest is accessible"""
        response = await client.post(
            "/api/profits/reinvest",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, "/api/profits/reinvest should return 200"
        
        data = response.json()
        assert "success" in data
    
    @pytest.mark.asyncio
    async def test_advanced_decisions_recent_endpoint(self, client, auth_token):
        """Test GET /api/advanced/decisions/recent is accessible"""
        response = await client.get(
            "/api/advanced/decisions/recent",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, "/api/advanced/decisions/recent should return 200"
        
        data = response.json()
        assert "decisions" in data or "count" in data
    
    @pytest.mark.asyncio
    async def test_keys_test_endpoint(self, client, auth_token):
        """Test POST /api/keys/test exists and requires proper data"""
        # Test with missing data (should return 400, not 404)
        response = await client.post(
            "/api/keys/test",
            json={},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code in [400, 422], "/api/keys/test should return 400 for bad input, not 404"


class TestAuthenticationRequirements:
    """Test that protected endpoints return 401/403, not 404"""
    
    @pytest.mark.asyncio
    async def test_wallet_requirements_requires_auth(self, client):
        """Test /api/wallet/requirements returns 401 without auth"""
        response = await client.get("/api/wallet/requirements")
        assert response.status_code in [401, 403], "Should return 401/403 without auth, not 404"
    
    @pytest.mark.asyncio
    async def test_ai_insights_requires_auth(self, client):
        """Test /api/ai/insights returns 401 without auth"""
        response = await client.get("/api/ai/insights")
        assert response.status_code in [401, 403], "Should return 401/403 without auth, not 404"
    
    @pytest.mark.asyncio
    async def test_ml_predict_requires_auth(self, client):
        """Test /api/ml/predict returns 401 without auth"""
        response = await client.get("/api/ml/predict?symbol=BTC-ZAR")
        assert response.status_code in [401, 403], "Should return 401/403 without auth, not 404"
    
    @pytest.mark.asyncio
    async def test_profits_reinvest_requires_auth(self, client):
        """Test /api/profits/reinvest returns 401 without auth"""
        response = await client.post("/api/profits/reinvest")
        assert response.status_code in [401, 403], "Should return 401/403 without auth, not 404"
    
    @pytest.mark.asyncio
    async def test_advanced_decisions_requires_auth(self, client):
        """Test /api/advanced/decisions/recent returns 401 without auth"""
        response = await client.get("/api/advanced/decisions/recent")
        assert response.status_code in [401, 403], "Should return 401/403 without auth, not 404"
    
    @pytest.mark.asyncio
    async def test_keys_test_requires_auth(self, client):
        """Test /api/keys/test returns 401 without auth"""
        response = await client.post("/api/keys/test", json={"provider": "openai", "api_key": "test"})
        assert response.status_code in [401, 403], "Should return 401/403 without auth, not 404"
    
    @pytest.mark.asyncio
    async def test_emergency_stop_requires_auth(self, client):
        """Test /api/system/emergency-stop returns 401 without auth"""
        response = await client.post("/api/system/emergency-stop")
        assert response.status_code in [401, 403], "Should return 401/403 without auth, not 404"


class TestPasswordExclusion:
    """Test that auth responses don't include password fields"""
    
    @pytest.mark.asyncio
    async def test_register_response_no_password(self, client):
        """Test registration response doesn't include password"""
        from uuid import uuid4
        
        test_email = f"test_pwd_{uuid4().hex[:8]}@example.com"
        
        response = await client.post(
            "/api/auth/register",
            json={
                "first_name": "Test",
                "email": test_email,
                "password": "testpass123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check user object doesn't contain password fields
        if "user" in data:
            user = data["user"]
            assert "password" not in user, "User object should not contain 'password' field"
            assert "password_hash" not in user, "User object should not contain 'password_hash' field"
        
        # Cleanup
        await db.users_collection.delete_one({"email": test_email.lower()})
    
    @pytest.mark.asyncio
    async def test_login_response_no_password(self, client):
        """Test login response doesn't include password"""
        from uuid import uuid4
        
        test_email = f"test_login_pwd_{uuid4().hex[:8]}@example.com"
        test_password = "testpass123"
        
        # Register user first
        await client.post(
            "/api/auth/register",
            json={
                "first_name": "Test",
                "email": test_email,
                "password": test_password
            }
        )
        
        # Login
        response = await client.post(
            "/api/auth/login",
            json={
                "email": test_email,
                "password": test_password
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check user object doesn't contain password fields
        if "user" in data:
            user = data["user"]
            assert "password" not in user, "User object should not contain 'password' field"
            assert "password_hash" not in user, "User object should not contain 'password_hash' field"
        
        # Cleanup
        await db.users_collection.delete_one({"email": test_email.lower()})
    
    @pytest.mark.asyncio
    async def test_me_endpoint_no_password(self, client, auth_token):
        """Test /api/auth/me doesn't return password"""
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "password" not in data, "User data should not contain 'password' field"
        assert "password_hash" not in data, "User data should not contain 'password_hash' field"
    
    @pytest.mark.asyncio
    async def test_profile_endpoint_no_password(self, client, auth_token):
        """Test /api/auth/profile (GET) doesn't return password"""
        response = await client.get(
            "/api/auth/profile",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "password" not in data, "Profile data should not contain 'password' field"
        assert "password_hash" not in data, "Profile data should not contain 'password_hash' field"


class TestOpenAIKeyTesting:
    """Test OpenAI key testing functionality"""
    
    @pytest.mark.asyncio
    async def test_openai_key_test_missing_key(self, client, auth_token):
        """Test OpenAI key test with missing API key"""
        response = await client.post(
            "/api/keys/test",
            json={"provider": "openai"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Should return 400 for missing key, not 500
        assert response.status_code in [400, 422], "Should return 400 for missing API key"
    
    @pytest.mark.asyncio
    async def test_openai_key_test_invalid_key(self, client, auth_token):
        """Test OpenAI key test with invalid API key"""
        response = await client.post(
            "/api/keys/test",
            json={
                "provider": "openai",
                "api_key": "sk-invalid-test-key-12345"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Should return success:false, not crash
        assert response.status_code == 200, "Should return 200 with success:false for invalid key"
        data = response.json()
        assert "success" in data
        # Note: We can't actually test with a real invalid key as it would hit OpenAI API
    
    @pytest.mark.asyncio
    async def test_openai_key_test_response_format(self, client, auth_token):
        """Test OpenAI key test returns expected format"""
        response = await client.post(
            "/api/keys/test",
            json={
                "provider": "openai",
                "api_key": "sk-test-key"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "success" in data
        assert "message" in data or "error" in data
        assert "provider" in data


class TestSystemModeEndpoint:
    """Test that /api/system/mode is accessible"""
    
    @pytest.mark.asyncio
    async def test_system_mode_get_requires_auth(self, client):
        """Test GET /api/system/mode requires authentication"""
        response = await client.get("/api/system/mode")
        assert response.status_code in [401, 403], "Should require auth, not return 404"
    
    @pytest.mark.asyncio
    async def test_system_mode_get_with_auth(self, client, auth_token):
        """Test GET /api/system/mode works with auth"""
        response = await client.get(
            "/api/system/mode",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, "/api/system/mode should return 200 with auth"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
