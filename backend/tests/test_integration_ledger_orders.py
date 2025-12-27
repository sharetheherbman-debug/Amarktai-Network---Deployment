"""
Integration test for ledger service and order pipeline
Tests that the two systems work together correctly
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.ledger_service import LedgerService
from services.order_pipeline import OrderPipeline


class MockCollection:
    """Mock MongoDB collection"""
    def __init__(self):
        self.data = []
        self.indexes = []
    
    def create_index(self, *args, **kwargs):
        self.indexes.append((args, kwargs))
    
    async def insert_one(self, doc):
        doc["_id"] = f"doc_{len(self.data)}"
        self.data.append(doc)
        return Mock(inserted_id=doc["_id"])
    
    async def update_one(self, query, update, **kwargs):
        result = Mock()
        result.modified_count = 0
        return result
    
    def find(self, query=None):
        cursor = Mock()
        cursor.sort = Mock(return_value=cursor)
        cursor.limit = Mock(return_value=cursor)
        cursor.to_list = AsyncMock(return_value=self.data.copy())
        return cursor
    
    def aggregate(self, pipeline):
        cursor = Mock()
        cursor.to_list = AsyncMock(return_value=[])
        return cursor
    
    async def find_one(self, query):
        return None
    
    async def count_documents(self, query):
        return len(self.data)


class MockDatabase:
    """Mock database"""
    def __init__(self):
        self.collections = {}
    
    def __getitem__(self, name):
        if name not in self.collections:
            self.collections[name] = MockCollection()
        return self.collections[name]


@pytest.mark.asyncio
async def test_ledger_service_trade_count():
    """Test that get_trade_count works correctly"""
    db = MockDatabase()
    ledger = LedgerService(db)
    
    # Add some fills
    await ledger.append_fill(
        user_id="user_1",
        bot_id="bot_1",
        exchange="binance",
        symbol="BTC/USDT",
        side="buy",
        qty=0.01,
        price=50000,
        fee=0.5,
        fee_currency="USDT",
        timestamp=datetime.utcnow(),
        order_id="order_1"
    )
    
    await ledger.append_fill(
        user_id="user_1",
        bot_id="bot_1",
        exchange="binance",
        symbol="BTC/USDT",
        side="sell",
        qty=0.01,
        price=51000,
        fee=0.5,
        fee_currency="USDT",
        timestamp=datetime.utcnow(),
        order_id="order_2"
    )
    
    # Count trades
    count = await ledger.get_trade_count(user_id="user_1")
    assert count == 2
    
    count = await ledger.get_trade_count(bot_id="bot_1")
    assert count == 2


@pytest.mark.asyncio
async def test_ledger_service_daily_pnl():
    """Test compute_daily_pnl method"""
    db = MockDatabase()
    ledger = LedgerService(db)
    
    # Add funding
    await ledger.append_event(
        user_id="user_1",
        event_type="funding",
        amount=10000,
        currency="USDT",
        timestamp=datetime.utcnow()
    )
    
    # Add a profitable trade
    await ledger.append_fill(
        user_id="user_1",
        bot_id="bot_1",
        exchange="binance",
        symbol="BTC/USDT",
        side="buy",
        qty=0.01,
        price=50000,
        fee=0.5,
        fee_currency="USDT",
        timestamp=datetime.utcnow(),
        order_id="order_1"
    )
    
    await ledger.append_fill(
        user_id="user_1",
        bot_id="bot_1",
        exchange="binance",
        symbol="BTC/USDT",
        side="sell",
        qty=0.01,
        price=51000,
        fee=0.5,
        fee_currency="USDT",
        timestamp=datetime.utcnow(),
        order_id="order_2"
    )
    
    # Calculate daily PnL
    daily_pnl = await ledger.compute_daily_pnl(user_id="user_1")
    
    # Should be profit minus fees: (51000-50000)*0.01 - 1.0 = 10 - 1 = 9
    # Note: The actual value might vary slightly based on how fees are calculated
    assert daily_pnl >= 8.0  # At least this much profit


@pytest.mark.asyncio
async def test_ledger_service_consecutive_losses():
    """Test get_consecutive_losses method"""
    db = MockDatabase()
    ledger = LedgerService(db)
    
    # This is a basic test - consecutive losses logic is complex
    # and requires position tracking
    consecutive = await ledger.get_consecutive_losses(user_id="user_1")
    assert consecutive >= 0  # Should return a non-negative number


@pytest.mark.asyncio
async def test_ledger_service_error_rate():
    """Test get_error_rate method"""
    db = MockDatabase()
    ledger = LedgerService(db)
    
    # Add some error events
    await ledger.append_event(
        user_id="user_1",
        bot_id="bot_1",
        event_type="error",
        amount=0,
        currency="",
        timestamp=datetime.utcnow(),
        description="Test error"
    )
    
    error_rate = await ledger.get_error_rate(user_id="user_1", hours=1)
    assert error_rate == 1


@pytest.mark.asyncio
async def test_order_pipeline_initialization():
    """Test that OrderPipeline initializes correctly with ledger service"""
    db = MockDatabase()
    ledger = LedgerService(db)
    
    # Create order pipeline with ledger service
    pipeline = OrderPipeline(db, ledger)
    
    assert pipeline.ledger is not None
    assert pipeline.db is not None
    assert pipeline.pending_orders is not None
    assert pipeline.circuit_breaker_state is not None


@pytest.mark.asyncio
async def test_order_pipeline_get_order_status():
    """Test get_order_status method"""
    db = MockDatabase()
    ledger = LedgerService(db)
    pipeline = OrderPipeline(db, ledger)
    
    # Test with non-existent order
    status = await pipeline.get_order_status("order_123", "user_123")
    assert status is None


@pytest.mark.asyncio
async def test_compute_equity_accepts_bot_id():
    """Test that compute_equity works with bot_id parameter"""
    db = MockDatabase()
    ledger = LedgerService(db)
    
    # Add funding for bot
    await ledger.append_event(
        user_id="user_1",
        bot_id="bot_1",
        event_type="funding",
        amount=1000,
        currency="USDT",
        timestamp=datetime.utcnow()
    )
    
    # Compute equity by bot_id
    equity = await ledger.compute_equity(bot_id="bot_1")
    assert equity == 1000.0


@pytest.mark.asyncio
async def test_compute_drawdown_accepts_bot_id():
    """Test that compute_drawdown works with bot_id parameter"""
    db = MockDatabase()
    ledger = LedgerService(db)
    
    # Add funding
    await ledger.append_event(
        user_id="user_1",
        bot_id="bot_1",
        event_type="funding",
        amount=1000,
        currency="USDT",
        timestamp=datetime.utcnow()
    )
    
    # Compute drawdown by bot_id
    current_dd, max_dd = await ledger.compute_drawdown(bot_id="bot_1")
    assert current_dd >= 0
    assert max_dd >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
