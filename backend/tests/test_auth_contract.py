"""
Test new auth contract with backward compatibility
Tests registration with password and password_hash fields
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


@pytest.mark.asyncio
async def test_register_with_password(client):
    """Test registration with password field (preferred)"""
    from uuid import uuid4
    
    test_email = f"test_password_{uuid4().hex[:8]}@example.com"
    
    response = await client.post(
        "/api/auth/register",
        json={
            "first_name": "Test",
            "email": test_email,
            "password": "testpass123"
        }
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    
    # Check new standard fields
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"
    
    # Check legacy field for backward compatibility
    assert "token" in data
    assert data["token"] == data["access_token"]
    
    # Check user data
    assert "user" in data
    assert data["user"]["email"] == test_email.lower()
    assert data["user"]["first_name"] == "Test"
    assert "password_hash" not in data["user"]
    assert "_id" not in data["user"]
    
    # Cleanup
    await db.users_collection.delete_one({"email": test_email.lower()})


@pytest.mark.asyncio
async def test_register_with_password_hash_legacy(client):
    """Test registration with password_hash field (backward compatibility)"""
    from uuid import uuid4
    
    test_email = f"test_legacy_{uuid4().hex[:8]}@example.com"
    
    response = await client.post(
        "/api/auth/register",
        json={
            "first_name": "Legacy",
            "email": test_email,
            "password_hash": "legacypass123"
        }
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    
    # Should work the same as password field
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"
    assert "token" in data
    
    # Cleanup
    await db.users_collection.delete_one({"email": test_email.lower()})


@pytest.mark.asyncio
async def test_register_requires_one_password(client):
    """Test that exactly one of password or password_hash is required"""
    from uuid import uuid4
    
    test_email = f"test_both_{uuid4().hex[:8]}@example.com"
    
    # Test with both (should fail)
    response = await client.post(
        "/api/auth/register",
        json={
            "first_name": "Test",
            "email": test_email,
            "password": "pass1",
            "password_hash": "pass2"
        }
    )
    
    assert response.status_code == 400
    
    # Test with neither (should fail)
    response = await client.post(
        "/api/auth/register",
        json={
            "first_name": "Test",
            "email": test_email
        }
    )
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_register_with_invite_code_header(client):
    """Test registration with invite code in header"""
    from uuid import uuid4
    import os
    
    # Only test if INVITE_CODE is set
    invite_code = os.getenv("INVITE_CODE", "").strip()
    if not invite_code:
        pytest.skip("INVITE_CODE not set, skipping invite code test")
    
    test_email = f"test_invite_{uuid4().hex[:8]}@example.com"
    
    # Test with correct invite code in header
    response = await client.post(
        "/api/auth/register",
        json={
            "first_name": "Test",
            "email": test_email,
            "password": "testpass123"
        },
        headers={"X-Invite-Code": invite_code}
    )
    
    assert response.status_code == 200
    
    # Cleanup
    await db.users_collection.delete_one({"email": test_email.lower()})


@pytest.mark.asyncio
async def test_register_with_invite_code_body(client):
    """Test registration with invite code in body"""
    from uuid import uuid4
    import os
    
    # Only test if INVITE_CODE is set
    invite_code = os.getenv("INVITE_CODE", "").strip()
    if not invite_code:
        pytest.skip("INVITE_CODE not set, skipping invite code test")
    
    test_email = f"test_invite_body_{uuid4().hex[:8]}@example.com"
    
    # Test with correct invite code in body
    response = await client.post(
        "/api/auth/register",
        json={
            "first_name": "Test",
            "email": test_email,
            "password": "testpass123",
            "invite_code": invite_code
        }
    )
    
    assert response.status_code == 200
    
    # Cleanup
    await db.users_collection.delete_one({"email": test_email.lower()})


@pytest.mark.asyncio
async def test_login_returns_standard_fields(client):
    """Test that login returns both standard and legacy token fields"""
    from uuid import uuid4
    from auth import get_password_hash
    from datetime import datetime, timezone
    
    test_email = f"test_login_{uuid4().hex[:8]}@example.com"
    test_user_id = str(uuid4())
    
    # Create test user
    user_data = {
        "id": test_user_id,
        "email": test_email,
        "password_hash": get_password_hash("loginpass123"),
        "first_name": "Login",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users_collection.insert_one(user_data)
    
    # Test login
    response = await client.post(
        "/api/auth/login",
        json={
            "email": test_email,
            "password": "loginpass123"
        }
    )
    
    assert response.status_code == 200
    
    data = response.json()
    
    # Check new standard fields
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"
    
    # Check legacy field
    assert "token" in data
    assert data["token"] == data["access_token"]
    
    # Check user data doesn't contain sensitive fields
    assert "user" in data
    assert "password_hash" not in data["user"]
    
    # Cleanup
    await db.users_collection.delete_one({"id": test_user_id})


@pytest.mark.asyncio
async def test_profile_excludes_password_hash(client):
    """Test that GET /auth/me excludes password_hash"""
    from uuid import uuid4
    from auth import get_password_hash, create_access_token
    from datetime import datetime, timezone
    
    test_user_id = str(uuid4())
    test_email = f"test_profile_{uuid4().hex[:8]}@example.com"
    
    # Create test user
    user_data = {
        "id": test_user_id,
        "email": test_email,
        "password_hash": get_password_hash("profilepass123"),
        "first_name": "Profile",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users_collection.insert_one(user_data)
    
    # Generate token
    token = create_access_token({"user_id": test_user_id})
    
    # Test GET /auth/me
    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    
    data = response.json()
    
    # Should not contain sensitive fields
    assert "password_hash" not in data
    assert "_id" not in data
    
    # Cleanup
    await db.users_collection.delete_one({"id": test_user_id})


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
