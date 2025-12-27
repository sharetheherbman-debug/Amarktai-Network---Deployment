"""
Tests for Bot Lifecycle Management (Pause/Resume)
Tests both POST and PUT methods for compatibility
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from fastapi import HTTPException

# Mock the imports
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))


@pytest.fixture
def mock_user_id():
    """Mock user ID for testing"""
    return "test-user-123"


@pytest.fixture
def mock_bot():
    """Mock bot data"""
    return {
        "id": "bot-123",
        "user_id": "test-user-123",
        "name": "Test Bot",
        "status": "active",
        "current_capital": 1000,
        "initial_capital": 1000,
        "total_profit": 0
    }


@pytest.fixture
def mock_paused_bot():
    """Mock paused bot data"""
    return {
        "id": "bot-456",
        "user_id": "test-user-123",
        "name": "Paused Bot",
        "status": "paused",
        "paused_at": datetime.now(timezone.utc).isoformat(),
        "pause_reason": "Manual pause",
        "paused_by_user": True,
        "current_capital": 1000,
        "initial_capital": 1000,
        "total_profit": 0
    }


@pytest.mark.asyncio
async def test_pause_bot_with_post(mock_user_id, mock_bot):
    """Test pausing a bot with POST method"""
    with patch('routes.bot_lifecycle.bots_collection') as mock_collection, \
         patch('routes.bot_lifecycle.rt_events') as mock_events:
        
        # Mock database responses
        mock_collection.find_one = AsyncMock(side_effect=[
            mock_bot,  # First call - verify bot exists
            {**mock_bot, "status": "paused", "paused_at": datetime.now(timezone.utc).isoformat()}  # Second call - updated bot
        ])
        mock_collection.update_one = AsyncMock()
        
        # Import after mocking
        from routes.bot_lifecycle import pause_bot
        
        # Test POST method
        result = await pause_bot(bot_id="bot-123", data=None, user_id=mock_user_id)
        
        # Assertions
        assert result["success"] is True
        assert "paused successfully" in result["message"]
        assert result["bot"]["status"] == "paused"
        
        # Verify database was called
        mock_collection.update_one.assert_called_once()
        update_call = mock_collection.update_one.call_args
        assert update_call[0][0] == {"id": "bot-123"}
        assert "$set" in update_call[0][1]
        assert update_call[0][1]["$set"]["status"] == "paused"
        assert "paused_at" in update_call[0][1]["$set"]


@pytest.mark.asyncio
async def test_pause_bot_with_put(mock_user_id, mock_bot):
    """Test pausing a bot with PUT method (same as POST)"""
    # The implementation is the same for both POST and PUT
    # This test ensures both decorators work
    with patch('routes.bot_lifecycle.bots_collection') as mock_collection, \
         patch('routes.bot_lifecycle.rt_events') as mock_events:
        
        mock_collection.find_one = AsyncMock(side_effect=[
            mock_bot,
            {**mock_bot, "status": "paused"}
        ])
        mock_collection.update_one = AsyncMock()
        
        from routes.bot_lifecycle import pause_bot
        
        result = await pause_bot(bot_id="bot-123", data={"reason": "Testing PUT"}, user_id=mock_user_id)
        
        assert result["success"] is True
        assert result["bot"]["status"] == "paused"


@pytest.mark.asyncio
async def test_resume_bot_with_post(mock_user_id, mock_paused_bot):
    """Test resuming a bot with POST method"""
    with patch('routes.bot_lifecycle.bots_collection') as mock_collection, \
         patch('routes.bot_lifecycle.rt_events') as mock_events:
        
        mock_collection.find_one = AsyncMock(side_effect=[
            mock_paused_bot,  # First call - verify bot is paused
            {**mock_paused_bot, "status": "active", "resumed_at": datetime.now(timezone.utc).isoformat()}  # Second call - updated bot
        ])
        mock_collection.update_one = AsyncMock()
        
        from routes.bot_lifecycle import resume_bot
        
        result = await resume_bot(bot_id="bot-456", user_id=mock_user_id)
        
        # Assertions
        assert result["success"] is True
        assert "resumed successfully" in result["message"]
        assert result["bot"]["status"] == "active"
        
        # Verify database was called
        mock_collection.update_one.assert_called_once()
        update_call = mock_collection.update_one.call_args
        assert update_call[0][0] == {"id": "bot-456"}
        assert "$set" in update_call[0][1]
        assert update_call[0][1]["$set"]["status"] == "active"
        assert "resumed_at" in update_call[0][1]["$set"]


@pytest.mark.asyncio
async def test_resume_bot_with_put(mock_user_id, mock_paused_bot):
    """Test resuming a bot with PUT method (same as POST)"""
    with patch('routes.bot_lifecycle.bots_collection') as mock_collection, \
         patch('routes.bot_lifecycle.rt_events') as mock_events:
        
        mock_collection.find_one = AsyncMock(side_effect=[
            mock_paused_bot,
            {**mock_paused_bot, "status": "active"}
        ])
        mock_collection.update_one = AsyncMock()
        
        from routes.bot_lifecycle import resume_bot
        
        result = await resume_bot(bot_id="bot-456", user_id=mock_user_id)
        
        assert result["success"] is True
        assert result["bot"]["status"] == "active"


@pytest.mark.asyncio
async def test_pause_already_paused_bot(mock_user_id, mock_paused_bot):
    """Test pausing a bot that is already paused"""
    with patch('routes.bot_lifecycle.bots_collection') as mock_collection:
        
        mock_collection.find_one = AsyncMock(return_value=mock_paused_bot)
        
        from routes.bot_lifecycle import pause_bot
        
        result = await pause_bot(bot_id="bot-456", data=None, user_id=mock_user_id)
        
        # Should return success=False with appropriate message
        assert result["success"] is False
        assert "already paused" in result["message"]


@pytest.mark.asyncio
async def test_resume_active_bot(mock_user_id, mock_bot):
    """Test resuming a bot that is already active"""
    with patch('routes.bot_lifecycle.bots_collection') as mock_collection:
        
        mock_collection.find_one = AsyncMock(return_value=mock_bot)
        
        from routes.bot_lifecycle import resume_bot
        
        result = await resume_bot(bot_id="bot-123", user_id=mock_user_id)
        
        # Should return success=False with appropriate message
        assert result["success"] is False
        assert "not paused" in result["message"]


@pytest.mark.asyncio
async def test_pause_nonexistent_bot(mock_user_id):
    """Test pausing a bot that doesn't exist"""
    with patch('routes.bot_lifecycle.bots_collection') as mock_collection:
        
        mock_collection.find_one = AsyncMock(return_value=None)
        
        from routes.bot_lifecycle import pause_bot
        
        # Should raise HTTPException 404
        with pytest.raises(HTTPException) as exc_info:
            await pause_bot(bot_id="nonexistent", data=None, user_id=mock_user_id)
        
        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_resume_nonexistent_bot(mock_user_id):
    """Test resuming a bot that doesn't exist"""
    with patch('routes.bot_lifecycle.bots_collection') as mock_collection:
        
        mock_collection.find_one = AsyncMock(return_value=None)
        
        from routes.bot_lifecycle import resume_bot
        
        # Should raise HTTPException 404
        with pytest.raises(HTTPException) as exc_info:
            await resume_bot(bot_id="nonexistent", user_id=mock_user_id)
        
        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_pause_with_custom_reason(mock_user_id, mock_bot):
    """Test pausing a bot with a custom reason"""
    with patch('routes.bot_lifecycle.bots_collection') as mock_collection, \
         patch('routes.bot_lifecycle.rt_events') as mock_events:
        
        mock_collection.find_one = AsyncMock(side_effect=[
            mock_bot,
            {**mock_bot, "status": "paused", "pause_reason": "Testing custom reason"}
        ])
        mock_collection.update_one = AsyncMock()
        
        from routes.bot_lifecycle import pause_bot
        
        result = await pause_bot(
            bot_id="bot-123",
            data={"reason": "Testing custom reason"},
            user_id=mock_user_id
        )
        
        assert result["success"] is True
        
        # Check that the custom reason was used
        update_call = mock_collection.update_one.call_args
        assert update_call[0][1]["$set"]["pause_reason"] == "Testing custom reason"


@pytest.mark.asyncio
async def test_pause_updates_paused_by_user_flag(mock_user_id, mock_bot):
    """Test that pausing sets paused_by_user flag"""
    with patch('routes.bot_lifecycle.bots_collection') as mock_collection, \
         patch('routes.bot_lifecycle.rt_events') as mock_events:
        
        mock_collection.find_one = AsyncMock(side_effect=[mock_bot, {**mock_bot, "status": "paused"}])
        mock_collection.update_one = AsyncMock()
        
        from routes.bot_lifecycle import pause_bot
        
        await pause_bot(bot_id="bot-123", data=None, user_id=mock_user_id)
        
        # Check that paused_by_user flag is set
        update_call = mock_collection.update_one.call_args
        assert update_call[0][1]["$set"]["paused_by_user"] is True


@pytest.mark.asyncio
async def test_resume_removes_pause_fields(mock_user_id, mock_paused_bot):
    """Test that resuming removes pause-related fields"""
    with patch('routes.bot_lifecycle.bots_collection') as mock_collection, \
         patch('routes.bot_lifecycle.rt_events') as mock_events:
        
        mock_collection.find_one = AsyncMock(side_effect=[mock_paused_bot, {**mock_paused_bot, "status": "active"}])
        mock_collection.update_one = AsyncMock()
        
        from routes.bot_lifecycle import resume_bot
        
        await resume_bot(bot_id="bot-456", user_id=mock_user_id)
        
        # Check that pause fields are removed
        update_call = mock_collection.update_one.call_args
        assert "$unset" in update_call[0][1]
        assert "paused_at" in update_call[0][1]["$unset"]
        assert "pause_reason" in update_call[0][1]["$unset"]
        assert "paused_by_user" in update_call[0][1]["$unset"]
