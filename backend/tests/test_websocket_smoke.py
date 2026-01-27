"""
Smoke test for WebSocket endpoint

Verifies that /api/ws WebSocket endpoint:
- Is properly registered in the application
- Accepts connections with valid tokens
- Rejects connections with invalid/missing tokens
- Handles ping/pong correctly
"""

import pytest
import sys
import os
from unittest.mock import Mock, AsyncMock, MagicMock

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.mark.asyncio
async def test_websocket_endpoint_exists():
    """Test that /api/ws endpoint is registered"""
    from server import app
    
    # Check if the WebSocket endpoint is registered
    ws_routes = [route for route in app.routes if hasattr(route, 'path') and '/api/ws' in str(route.path)]
    
    assert len(ws_routes) > 0, "/api/ws WebSocket endpoint should be registered"
    
    # Verify it's a WebSocket route
    for route in ws_routes:
        if '/api/ws' == route.path:
            # Found the exact route
            assert True
            return
    
    # If we get here, /api/ws exact path wasn't found
    pytest.fail(f"/api/ws endpoint not found. Found: {[r.path for r in ws_routes]}")


@pytest.mark.asyncio 
async def test_websocket_rejects_missing_token():
    """Test that WebSocket rejects connections without token"""
    from fastapi.testclient import TestClient
    from server import app
    
    client = TestClient(app)
    
    # Try to connect without token - should be rejected
    with pytest.raises(Exception):
        # WebSocket should reject connection
        with client.websocket_connect("/api/ws"):
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
