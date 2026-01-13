"""
Test Dashboard Real-time Functionality
Tests canonical endpoints, auth hardening, and safe empty states
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


# Mock database and dependencies
@pytest.fixture
def mock_db():
    """Mock database collections"""
    db = MagicMock()
    
    # Mock collections
    db.users_collection = AsyncMock()
    db.bots_collection = AsyncMock()
    db.trades_collection = AsyncMock()
    db.api_keys_collection = AsyncMock()
    
    # Mock find/find_one methods
    db.api_keys_collection.find = MagicMock(return_value=AsyncMock())
    db.api_keys_collection.find().to_list = AsyncMock(return_value=[])
    db.api_keys_collection.find_one = AsyncMock(return_value=None)
    
    db.bots_collection.find = MagicMock(return_value=AsyncMock())
    db.bots_collection.find().to_list = AsyncMock(return_value=[])
    
    db.trades_collection.find = MagicMock(return_value=AsyncMock())
    db.trades_collection.find().to_list = AsyncMock(return_value=[])
    db.trades_collection.count_documents = AsyncMock(return_value=0)
    
    return db


@pytest.mark.asyncio
async def test_email_normalization_register():
    """Test that register normalizes emails to lowercase"""
    from routes.auth import register
    from models import User
    from unittest.mock import MagicMock, AsyncMock
    
    # Mock request with uppercase email
    mock_request = MagicMock()
    mock_request.headers.get = MagicMock(return_value=None)
    
    user = User(
        email="TEST@EXAMPLE.COM",
        password_hash="password123",
        first_name="Test",
        last_name="User"
    )
    
    with patch('routes.auth.db') as mock_db:
        mock_db.users_collection.find_one = AsyncMock(return_value=None)
        mock_db.users_collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id="test_id"))
        
        with patch('routes.auth.get_password_hash', return_value="hashed"):
            with patch('routes.auth.create_access_token', return_value="token"):
                result = await register(mock_request, user)
                
                # Verify email was normalized
                call_args = mock_db.users_collection.find_one.call_args
                assert call_args[0][0]['email'] == 'test@example.com'


@pytest.mark.asyncio
async def test_email_normalization_login():
    """Test that login normalizes emails to lowercase"""
    from routes.auth import login
    from models import UserLogin
    from unittest.mock import MagicMock, AsyncMock
    
    credentials = UserLogin(
        email="TEST@EXAMPLE.COM",
        password="password123"
    )
    
    mock_user = {
        'id': 'test_id',
        'email': 'test@example.com',
        'password_hash': 'hashed'
    }
    
    with patch('routes.auth.db') as mock_db:
        mock_db.users_collection.find_one = AsyncMock(return_value=mock_user)
        
        with patch('routes.auth.verify_password', return_value=True):
            with patch('routes.auth.create_access_token', return_value="token"):
                result = await login(credentials)
                
                # Verify email was normalized in query
                call_args = mock_db.users_collection.find_one.call_args
                assert call_args[0][0]['email'] == 'test@example.com'


@pytest.mark.asyncio
async def test_api_keys_canonical_list(mock_db):
    """Test canonical API keys list endpoint returns masked keys"""
    from routes.api_keys_canonical import list_api_keys
    
    # Mock API keys with encrypted data
    mock_keys = [
        {
            'user_id': 'test_user',
            'provider': 'binance',
            'exchange': 'binance',
            'created_at': datetime.now(timezone.utc).isoformat()
        }
    ]
    
    with patch('routes.api_keys_canonical.db', mock_db):
        mock_db.api_keys_collection.find().to_list = AsyncMock(return_value=mock_keys)
        
        result = await list_api_keys(user_id='test_user')
        
        assert result['success'] is True
        assert result['total'] == 1
        # Ensure no plaintext keys in response
        assert 'api_key_encrypted' not in str(result)
        assert 'api_secret_encrypted' not in str(result)


@pytest.mark.asyncio
async def test_decision_trace_safe_empty_state():
    """Test decision trace returns safe empty state when collection missing"""
    from routes.dashboard_aliases import get_decision_trace_latest
    
    with patch('routes.dashboard_aliases.db') as mock_db:
        # Simulate missing collection
        mock_db.__getitem__ = MagicMock(side_effect=Exception("Collection not found"))
        
        result = await get_decision_trace_latest(limit=50, user_id='test_user')
        
        # Should return empty list, not error
        assert result['success'] is True
        assert result['decisions'] == []
        assert 'note' in result


@pytest.mark.asyncio
async def test_metrics_summary_safe_empty_state(mock_db):
    """Test metrics summary returns safe empty metrics on error"""
    from routes.dashboard_aliases import get_metrics_summary
    
    with patch('routes.dashboard_aliases.db', mock_db):
        # Empty database
        result = await get_metrics_summary(user_id='test_user')
        
        assert result['success'] is True
        assert 'metrics' in result
        assert result['metrics']['bots']['total'] == 0
        assert result['metrics']['trades']['total'] == 0


@pytest.mark.asyncio
async def test_wallet_balances_safe_empty_state():
    """Test wallet balances returns safe state when collection not initialized"""
    from routes.wallet_endpoints import get_wallet_balances
    
    with patch('routes.wallet_endpoints.wallet_balances_collection', None):
        result = await get_wallet_balances(user_id='test_user')
        
        # Should not raise error
        assert 'user_id' in result
        assert result['master_wallet']['total_zar'] == 0
        assert 'note' in result or 'status' in result['master_wallet']


@pytest.mark.asyncio
async def test_exchange_comparison_endpoint(mock_db):
    """Test exchange comparison analytics endpoint"""
    from routes.analytics_api import get_exchange_comparison
    
    # Mock trades from different exchanges
    mock_trades = [
        {'exchange': 'binance', 'profit_loss': 100, 'amount': 1, 'price': 50000},
        {'exchange': 'binance', 'profit_loss': 50, 'amount': 1, 'price': 50000},
        {'exchange': 'luno', 'profit_loss': -20, 'amount': 1, 'price': 50000},
    ]
    
    with patch('routes.analytics_api.db', mock_db):
        mock_db.trades_collection.find().to_list = AsyncMock(return_value=mock_trades)
        
        result = await get_exchange_comparison(period='30d', user_id='test_user')
        
        assert 'exchanges' in result
        assert 'summary' in result
        assert result['summary']['total_trades'] == 3
        
        # Should have both exchanges
        exchanges = {e['exchange'] for e in result['exchanges']}
        assert 'binance' in exchanges
        assert 'luno' in exchanges


@pytest.mark.asyncio
async def test_whale_flow_alias():
    """Test whale flow alias routes to canonical handler"""
    from routes.dashboard_aliases import whale_flow_summary_alias
    from models import User
    
    mock_user = User(id='test', email='test@example.com', password_hash='hash')
    
    with patch('routes.dashboard_aliases.get_whale_summary') as mock_whale:
        mock_whale.return_value = {'summary': 'test'}
        
        result = await whale_flow_summary_alias(current_user=mock_user)
        
        # Should call canonical handler
        mock_whale.assert_called_once()


@pytest.mark.asyncio  
async def test_sse_event_types():
    """Test SSE emits proper event types"""
    from routes.realtime import _event_generator
    
    # Collect first few events
    events = []
    gen = _event_generator('test_user')
    
    for _ in range(3):
        try:
            event = await asyncio.wait_for(gen.__anext__(), timeout=1)
            events.append(event)
        except asyncio.TimeoutError:
            break
    
    # Should have at least heartbeat
    events_str = ''.join(events)
    assert 'event: heartbeat' in events_str
    assert 'timestamp' in events_str


def test_api_key_encryption():
    """Test API key encryption and decryption"""
    from routes.api_key_management import encrypt_api_key, decrypt_api_key
    
    original_key = "test_api_key_12345"
    
    # Encrypt
    encrypted = encrypt_api_key(original_key)
    assert encrypted != original_key
    assert len(encrypted) > 0
    
    # Decrypt
    decrypted = decrypt_api_key(encrypted)
    assert decrypted == original_key


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
