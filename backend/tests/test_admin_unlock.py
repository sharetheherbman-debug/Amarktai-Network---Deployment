"""
Test admin unlock endpoint
Run with: pytest backend/tests/test_admin_unlock.py -v
"""

import pytest
from httpx import AsyncClient
from fastapi import status
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


@pytest.fixture(scope="module")
async def test_user_token():
    """Create a test user and return auth token"""
    await db.connect()
    
    from auth import get_password_hash, create_access_token
    from uuid import uuid4
    
    test_user_id = str(uuid4())
    test_email = f"test_admin_{test_user_id[:8]}@example.com"
    
    user_data = {
        "id": test_user_id,
        "email": test_email,
        "password_hash": get_password_hash("testpassword123"),
        "first_name": "Admin",
        "last_name": "User",
        "is_admin": False,
        "created_at": "2026-01-14T00:00:00Z"
    }
    
    await db.users_collection.insert_one(user_data)
    
    # Create JWT token
    token = create_access_token(data={"user_id": test_user_id})  # Fixed: use user_id not sub
    
    yield token
    
    # Cleanup
    await db.users_collection.delete_one({"id": test_user_id})


@pytest.mark.asyncio
async def test_admin_unlock_correct_password(client, test_user_token):
    """Test admin unlock with correct password"""
    response = await client.post(
        "/api/admin/unlock",
        json={"password": "ashmor12@"},
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    assert "unlock_token" in data
    assert data["expires_in"] == 3600


@pytest.mark.asyncio
async def test_admin_unlock_case_insensitive(client, test_user_token):
    """Test admin unlock with uppercase password"""
    response = await client.post(
        "/api/admin/unlock",
        json={"password": "ASHMOR12@"},
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_admin_unlock_with_whitespace(client, test_user_token):
    """Test admin unlock with whitespace in password"""
    response = await client.post(
        "/api/admin/unlock",
        json={"password": "  ashmor12@  "},
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_admin_unlock_wrong_password(client, test_user_token):
    """Test admin unlock with wrong password"""
    response = await client.post(
        "/api/admin/unlock",
        json={"password": "wrongpassword"},
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    
    assert response.status_code == status.HTTP_403_FORBIDDEN
    data = response.json()
    assert "Invalid admin password" in data["detail"]


@pytest.mark.asyncio
async def test_admin_unlock_empty_password(client, test_user_token):
    """Test admin unlock with empty password"""
    response = await client.post(
        "/api/admin/unlock",
        json={"password": ""},
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "Password is required" in data["detail"]


@pytest.mark.asyncio
async def test_admin_unlock_no_auth(client):
    """Test admin unlock without authentication"""
    response = await client.post(
        "/api/admin/unlock",
        json={"password": "ashmor12@"}
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
