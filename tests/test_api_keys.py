"""
Test API Keys Contract Unification
Tests backward compatibility for API key payloads and endpoint behavior
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# Import after path setup
from server import app

client = TestClient(app)


@pytest.fixture
def mock_auth():
    """Mock authentication to return a test user"""
    with patch('auth.get_current_user') as mock:
        mock.return_value = "test_user_123"
        yield mock


@pytest.fixture
def mock_db():
    """Mock database operations"""
    with patch('database.api_keys_collection') as mock:
        yield mock


class TestAPIKeyContractUnification:
    """Test suite for API key contract unification (TASK B)"""
    
    def test_save_api_key_canonical_format(self, mock_auth, mock_db):
        """Test saving API key with canonical format (provider, api_key, api_secret)"""
        mock_db.find_one = AsyncMock(return_value=None)
        mock_db.insert_one = AsyncMock(return_value=MagicMock())
        
        payload = {
            "provider": "binance",
            "api_key": "test_key_12345",
            "api_secret": "test_secret_67890"
        }
        
        response = client.post("/api/api-keys", json=payload)
        
        # Should accept canonical format
        assert response.status_code in [200, 201]
        data = response.json()
        assert data.get("success") is True
        assert "binance" in data.get("message", "").lower()
    
    def test_save_api_key_legacy_exchange_field(self, mock_auth, mock_db):
        """Test saving API key with legacy 'exchange' field instead of 'provider'"""
        mock_db.find_one = AsyncMock(return_value=None)
        mock_db.insert_one = AsyncMock(return_value=MagicMock())
        
        # Legacy format: uses 'exchange' instead of 'provider'
        payload = {
            "exchange": "kucoin",
            "api_key": "test_key_12345",
            "api_secret": "test_secret_67890"
        }
        
        # The backend should accept this and map exchange -> provider
        # This tests backward compatibility
        response = client.post("/api/api-keys", json=payload)
        
        # Should either accept or return clear error (not 422)
        assert response.status_code != 422
    
    def test_save_api_key_legacy_camelcase(self, mock_auth, mock_db):
        """Test saving API key with legacy camelCase fields"""
        mock_db.find_one = AsyncMock(return_value=None)
        mock_db.insert_one = AsyncMock(return_value=MagicMock())
        
        # Legacy format: camelCase
        payload = {
            "provider": "luno",
            "apiKey": "test_key_12345",
            "apiSecret": "test_secret_67890"
        }
        
        response = client.post("/api/api-keys", json=payload)
        
        # Should handle camelCase fields  
        assert response.status_code != 422
    
    def test_test_api_key_with_api_key_field(self, mock_auth, mock_db):
        """Test API key test endpoint with 'api_key' field"""
        mock_db.find_one = AsyncMock(return_value={"provider": "binance"})
        mock_db.update_one = AsyncMock(return_value=MagicMock())
        
        payload = {
            "api_key": "test_key_12345",
            "api_secret": "test_secret_67890"
        }
        
        with patch('services.keys_service.keys_service.test_api_key', 
                   new_callable=AsyncMock) as mock_test:
            mock_test.return_value = (True, {"currencies_found": 10}, None)
            
            response = client.post("/api/api-keys/binance/test", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data.get("success") is True or data.get("ok") is True
    
    def test_test_api_key_with_key_field(self, mock_auth, mock_db):
        """Test API key test endpoint with legacy 'key' field"""
        mock_db.find_one = AsyncMock(return_value={"provider": "binance"})
        mock_db.update_one = AsyncMock(return_value=MagicMock())
        
        # Legacy format: 'key' instead of 'api_key'
        payload = {
            "key": "test_key_12345",
            "secret": "test_secret_67890"
        }
        
        with patch('services.keys_service.keys_service.test_api_key',
                   new_callable=AsyncMock) as mock_test:
            mock_test.return_value = (True, {"currencies_found": 10}, None)
            
            response = client.post("/api/api-keys/binance/test", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            # Should accept legacy format
            assert data.get("success") is True or data.get("ok") is True
    
    def test_test_api_key_missing_key_returns_error(self, mock_auth, mock_db):
        """Test that test endpoint returns clear error when api_key is missing"""
        payload = {
            "provider": "binance"
            # Missing api_key intentionally
        }
        
        response = client.post("/api/api-keys/binance/test", json=payload)
        
        assert response.status_code == 200  # Should not crash
        data = response.json()
        assert data.get("success") is False
        assert "api key" in data.get("error", "").lower() or "required" in data.get("error", "").lower()
    
    def test_list_api_keys_returns_masked(self, mock_auth, mock_db):
        """Test that list endpoint returns masked keys, never plaintext"""
        mock_db.find = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[
            {
                "provider": "binance",
                "api_key": "full_key_should_be_masked",
                "last_test_ok": True
            }
        ])
        mock_db.find.return_value = mock_cursor
        
        response = client.get("/api/api-keys")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        keys = data.get("keys", [])
        
        if keys:
            # Should not contain full api_key
            for key in keys:
                assert "full_key_should_be_masked" not in str(key)
                # Should have masked version
                assert "api_key_masked" in key or "api_key" not in key


class TestOpenAPIEndpoint:
    """Test OpenAPI endpoint exists and is accessible"""
    
    def test_openapi_json_exists(self):
        """Test that /api/openapi.json returns 200"""
        response = client.get("/api/openapi.json")
        
        # Should return OpenAPI schema
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data or "swagger" in data or "paths" in data
    
    def test_docs_endpoint_exists(self):
        """Test that /docs endpoint exists"""
        response = client.get("/docs")
        
        # FastAPI automatically creates /docs
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
