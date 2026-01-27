"""
Tests for timestamp handling in ledger endpoints

Tests that the ledger service and endpoints correctly handle:
- String timestamps (from legacy data or JSON imports)
- Datetime objects (from proper insertions)
- Mixed timestamp types in the same collection

Regression tests for the 500 errors:
- /api/profits?period=daily&limit=5
- /api/portfolio/summary  
- /api/countdown/status
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.ledger_service import LedgerService


class MockFillsCollection:
    """Mock fills_ledger collection with mixed timestamp types"""
    def __init__(self):
        self.data = []
        self.indexes = []
        
        # Pre-populate with test data - mix of string and datetime timestamps
        base_time = datetime.utcnow() - timedelta(days=30)
        
        # Add fills with string timestamps (legacy data)
        for i in range(5):
            ts = base_time + timedelta(days=i)
            self.data.append({
                "_id": f"fill_str_{i}",
                "user_id": "test_user",
                "bot_id": "test_bot",
                "exchange": "binance",
                "symbol": "BTC/USDT",
                "side": "buy" if i % 2 == 0 else "sell",
                "qty": 0.01,
                "price": 50000 + (i * 100),
                "fee": 0.5,
                "fee_currency": "USDT",
                "timestamp": ts.isoformat(),  # STRING timestamp
                "order_id": f"order_{i}",
                "is_paper": True
            })
        
        # Add fills with datetime timestamps (proper data)
        for i in range(5, 10):
            ts = base_time + timedelta(days=i)
            self.data.append({
                "_id": f"fill_dt_{i}",
                "user_id": "test_user",
                "bot_id": "test_bot",
                "exchange": "binance",
                "symbol": "BTC/USDT",
                "side": "buy" if i % 2 == 0 else "sell",
                "qty": 0.01,
                "price": 50000 + (i * 100),
                "fee": 0.5,
                "fee_currency": "USDT",
                "timestamp": ts,  # DATETIME timestamp
                "order_id": f"order_{i}",
                "is_paper": True
            })
    
    def create_index(self, *args, **kwargs):
        self.indexes.append((args, kwargs))
    
    async def insert_one(self, doc):
        doc["_id"] = f"fill_{len(self.data)}"
        self.data.append(doc)
        return Mock(inserted_id=doc["_id"])
    
    def find(self, query=None):
        """Return mock cursor with test data"""
        cursor = Mock()
        cursor.sort = Mock(return_value=cursor)
        cursor.limit = Mock(return_value=cursor)
        
        # Filter data based on query if provided
        filtered_data = self.data.copy()
        
        cursor.to_list = AsyncMock(return_value=filtered_data)
        return cursor
    
    def aggregate(self, pipeline):
        cursor = Mock()
        cursor.to_list = AsyncMock(return_value=[])
        return cursor


class MockEventsCollection:
    """Mock ledger_events collection"""
    def __init__(self):
        self.data = []
        self.indexes = []
    
    def create_index(self, *args, **kwargs):
        self.indexes.append((args, kwargs))
    
    async def insert_one(self, doc):
        doc["_id"] = f"event_{len(self.data)}"
        self.data.append(doc)
        return Mock(inserted_id=doc["_id"])
    
    def find(self, query=None):
        cursor = Mock()
        cursor.sort = Mock(return_value=cursor)
        cursor.limit = Mock(return_value=cursor)
        cursor.to_list = AsyncMock(return_value=[])
        return cursor


@pytest.fixture
def mock_db():
    """Create mock database with fills and events collections"""
    fills_collection = MockFillsCollection()
    events_collection = MockEventsCollection()
    
    # Create a dict-like object
    class MockDB(dict):
        def __init__(self):
            super().__init__()
            self["fills_ledger"] = fills_collection
            self["ledger_events"] = events_collection
    
    return MockDB()


@pytest.fixture
def ledger_service(mock_db):
    """Create ledger service instance with test data"""
    return LedgerService(mock_db)


@pytest.mark.asyncio
async def test_profit_series_with_string_timestamps(ledger_service):
    """Test that profit_series handles string timestamps without crashing"""
    # This should NOT raise "string indices must be integers, not 'str'"
    series = await ledger_service.profit_series(
        user_id="test_user",
        period="daily",
        limit=30
    )
    
    # Should return a list, not crash
    assert isinstance(series, list)
    
    # Should have data points
    assert len(series) > 0
    
    # Each item should have required fields
    for item in series:
        assert "date" in item
        assert "realized_pnl" in item
        assert "fees" in item
        assert "net_profit" in item


@pytest.mark.asyncio
async def test_profit_series_weekly_with_mixed_timestamps(ledger_service):
    """Test weekly profit series with mixed timestamp types"""
    series = await ledger_service.profit_series(
        user_id="test_user",
        period="weekly",
        limit=12
    )
    
    assert isinstance(series, list)
    # Should group by week
    for item in series:
        assert "date" in item
        assert "week" in item["date"] or "W" in item["date"]


@pytest.mark.asyncio
async def test_profit_series_monthly_with_mixed_timestamps(ledger_service):
    """Test monthly profit series with mixed timestamp types"""
    series = await ledger_service.profit_series(
        user_id="test_user",
        period="monthly",
        limit=12
    )
    
    assert isinstance(series, list)


@pytest.mark.asyncio
async def test_compute_equity_with_string_timestamps(ledger_service):
    """Test equity calculation with string timestamps"""
    # Add a funding event
    await ledger_service.append_event(
        user_id="test_user",
        event_type="funding",
        amount=10000,
        currency="USDT",
        timestamp=datetime.utcnow(),
        description="Test funding"
    )
    
    # Should compute equity without crashing
    equity = await ledger_service.compute_equity("test_user")
    
    # Should return a number
    assert isinstance(equity, (int, float))
    assert equity >= 0


@pytest.mark.asyncio
async def test_compute_realized_pnl_with_string_timestamps(ledger_service):
    """Test realized PnL calculation with string timestamps"""
    pnl = await ledger_service.compute_realized_pnl("test_user")
    
    # Should return a number
    assert isinstance(pnl, (int, float))


@pytest.mark.asyncio
async def test_compute_drawdown_with_string_timestamps(ledger_service):
    """Test drawdown calculation with string timestamps"""
    current_dd, max_dd = await ledger_service.compute_drawdown("test_user")
    
    # Should return numbers
    assert isinstance(current_dd, (int, float))
    assert isinstance(max_dd, (int, float))
    assert 0 <= current_dd <= 1
    assert 0 <= max_dd <= 1


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
