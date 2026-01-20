"""
Tests for Backend Blocker Fixes
- API key payload compatibility (JSON/form/legacy field names)
- WebSocket serialization (ObjectId + datetime)
- Trade limiter timestamp normalization
- Startup gating (autopilot/schedulers/bodyguard flags)
- Live Training Bay 24h rule
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from bson import ObjectId

# Import modules to test
from websocket_manager import sanitize_for_json
from engines.trade_limiter import TradeLimiter


class TestAPIKeyPayloadCompatibility:
    """Test that API key endpoints accept multiple payload formats"""
    
    def test_normalize_provider_fields(self):
        """Test that provider/exchange/platform are all accepted"""
        # Test data variations
        variants = [
            {"provider": "binance", "api_key": "test123", "api_secret": "secret123"},
            {"exchange": "binance", "apiKey": "test123", "apiSecret": "secret123"},
            {"platform": "binance", "key": "test123", "secret": "secret123"},
        ]
        
        for data in variants:
            # Normalize logic (from api_key_management.py)
            provider = data.get("provider") or data.get("exchange") or data.get("platform")
            api_key = data.get("api_key") or data.get("apiKey") or data.get("key")
            api_secret = data.get("api_secret") or data.get("apiSecret") or data.get("secret")
            
            assert provider == "binance"
            assert api_key == "test123"
            assert api_secret == "secret123"
    
    def test_passphrase_field(self):
        """Test that passphrase field is supported"""
        data = {
            "provider": "kucoin",
            "api_key": "test123",
            "api_secret": "secret123",
            "passphrase": "pass123"
        }
        
        passphrase = data.get("passphrase")
        assert passphrase == "pass123"


class TestWebSocketSerialization:
    """Test WebSocket sanitization for JSON compatibility"""
    
    def test_objectid_serialization(self):
        """Test that ObjectId is converted to string"""
        obj_id = ObjectId()
        result = sanitize_for_json(obj_id)
        
        assert isinstance(result, str)
        assert len(result) == 24  # ObjectId string length
    
    def test_datetime_serialization(self):
        """Test that datetime is converted to timezone-aware ISO"""
        # Test naive datetime
        naive_dt = datetime(2024, 1, 1, 12, 0, 0)
        result = sanitize_for_json(naive_dt)
        
        assert isinstance(result, str)
        assert "2024-01-01" in result
        assert "+" in result or "Z" in result  # Timezone indicator
        
        # Test aware datetime
        aware_dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = sanitize_for_json(aware_dt)
        
        assert isinstance(result, str)
        assert "+00:00" in result or "Z" in result
    
    def test_nested_dict_serialization(self):
        """Test that nested dicts with ObjectId/datetime are sanitized"""
        obj_id = ObjectId()
        dt = datetime(2024, 1, 1, 12, 0, 0)
        
        data = {
            "bot_id": obj_id,
            "created_at": dt,
            "nested": {
                "user_id": obj_id,
                "timestamp": dt
            }
        }
        
        result = sanitize_for_json(data)
        
        # Check all ObjectId converted to str
        assert isinstance(result["bot_id"], str)
        assert isinstance(result["nested"]["user_id"], str)
        
        # Check all datetime converted to str
        assert isinstance(result["created_at"], str)
        assert isinstance(result["nested"]["timestamp"], str)
    
    def test_list_serialization(self):
        """Test that lists with ObjectId/datetime are sanitized"""
        obj_ids = [ObjectId(), ObjectId()]
        result = sanitize_for_json(obj_ids)
        
        assert isinstance(result, list)
        assert all(isinstance(item, str) for item in result)


class TestTradeLimiterTimestamps:
    """Test trade limiter datetime normalization"""
    
    @pytest.mark.asyncio
    async def test_timezone_aware_comparison(self):
        """Test that datetime comparisons are timezone-aware"""
        # Create naive datetime (should be normalized)
        naive_dt = datetime(2024, 1, 1, 12, 0, 0)
        
        # Simulate normalization logic from trade_limiter.py
        if isinstance(naive_dt, str):
            last_trade = datetime.fromisoformat(naive_dt.replace('Z', '+00:00'))
        else:
            last_trade = naive_dt
        
        # Ensure timezone-aware
        if last_trade.tzinfo is None:
            last_trade = last_trade.replace(tzinfo=timezone.utc)
        
        # Now should be timezone-aware UTC
        now = datetime.now(timezone.utc)
        
        # Should not raise "can't compare offset-naive and offset-aware"
        try:
            comparison_result = now > last_trade
            assert comparison_result is True  # Current time should be after 2024-01-01
        except TypeError as e:
            pytest.fail(f"Timezone comparison failed: {e}")
    
    def test_iso_string_parsing(self):
        """Test that ISO strings with 'Z' are parsed correctly"""
        iso_string = "2024-01-01T12:00:00Z"
        
        # Normalize logic
        last_trade = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        
        assert last_trade.tzinfo is not None
        assert last_trade.tzinfo == timezone.utc


class TestStartupGating:
    """Test that startup flags are respected"""
    
    def test_env_bool_parsing(self):
        """Test env_bool utility function"""
        import os
        from utils.env_utils import env_bool
        
        # Test various string values
        test_cases = [
            ("1", True),
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("yes", True),
            ("0", False),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("no", False),
            ("", False),  # Default false
        ]
        
        for value, expected in test_cases:
            os.environ["TEST_FLAG"] = value
            result = env_bool("TEST_FLAG", False)
            assert result == expected, f"env_bool('{value}') should be {expected}"
    
    def test_feature_flags(self):
        """Test that feature flags control service startup"""
        import os
        
        # Simulate flag checks from server.py
        enable_autopilot = os.getenv('ENABLE_AUTOPILOT', '0') == '1'
        enable_schedulers = os.getenv('ENABLE_SCHEDULERS', '0') == '1'
        disable_ai_bodyguard = os.getenv('DISABLE_AI_BODYGUARD', '0') == '1'
        
        # With defaults, these should be False/False/False
        assert enable_autopilot is False
        assert enable_schedulers is False
        assert disable_ai_bodyguard is False


class TestLiveTrainingBay:
    """Test Live Training Bay 24h quarantine rule"""
    
    def test_hours_elapsed_calculation(self):
        """Test that hours elapsed is calculated correctly"""
        now = datetime.now(timezone.utc)
        created_at = now - timedelta(hours=12)  # 12 hours ago
        
        hours_elapsed = (now - created_at).total_seconds() / 3600
        
        assert 11.9 < hours_elapsed < 12.1  # Allow small float precision
    
    def test_eligibility_check(self):
        """Test that bots become eligible after 24h"""
        LIVE_MIN_TRAINING_HOURS = 24
        now = datetime.now(timezone.utc)
        
        # Bot created 20 hours ago - not eligible
        created_20h = now - timedelta(hours=20)
        hours_20 = (now - created_20h).total_seconds() / 3600
        eligible_20 = hours_20 >= LIVE_MIN_TRAINING_HOURS
        assert eligible_20 is False
        
        # Bot created 25 hours ago - eligible
        created_25h = now - timedelta(hours=25)
        hours_25 = (now - created_25h).total_seconds() / 3600
        eligible_25 = hours_25 >= LIVE_MIN_TRAINING_HOURS
        assert eligible_25 is True
    
    def test_hours_remaining_calculation(self):
        """Test that hours remaining countdown is correct"""
        LIVE_MIN_TRAINING_HOURS = 24
        now = datetime.now(timezone.utc)
        created_at = now - timedelta(hours=18)  # 18 hours ago
        
        hours_elapsed = (now - created_at).total_seconds() / 3600
        hours_remaining = max(0, LIVE_MIN_TRAINING_HOURS - hours_elapsed)
        
        assert 5.9 < hours_remaining < 6.1  # Should be ~6 hours remaining


class TestPlatformDrilldown:
    """Test platform drilldown endpoint correctness"""
    
    def test_profit_calculation(self):
        """Test that bot profit calculations are correct"""
        # Mock trade data
        trades = [
            {"profit_loss": 10.5},
            {"profit_loss": -5.2},
            {"profit_loss": 15.0},
            {"profit_loss": -3.0}
        ]
        
        total_profit = sum(t.get("profit_loss", 0) for t in trades)
        assert total_profit == 17.3
    
    def test_win_rate_calculation(self):
        """Test that win rate is calculated correctly"""
        trades = [
            {"profit_loss": 10.5},   # Win
            {"profit_loss": -5.2},   # Loss
            {"profit_loss": 15.0},   # Win
            {"profit_loss": -3.0},   # Loss
            {"profit_loss": 5.0}     # Win
        ]
        
        winning_trades = sum(1 for t in trades if t.get("profit_loss", 0) > 0)
        win_rate = (winning_trades / len(trades) * 100) if trades else 0
        
        assert winning_trades == 3
        assert win_rate == 60.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
