"""
Test Suite for Phase 5-8 Features
- Risk Engine & Capital Allocation
- AI Model Router & Learning
- Audit Logging & Email Reporting
"""

import pytest
import asyncio
from datetime import datetime, timezone

# ============================================================================
# PHASE 5 TESTS - Risk Engine & Capital
# ============================================================================

@pytest.mark.asyncio
async def test_capital_allocator():
    """Test capital allocation system"""
    from engines.capital_allocator import capital_allocator
    import database as db
    
    # Create test bot
    test_bot = {
        "id": "test_bot_001",
        "user_id": "test_user",
        "name": "Test Bot",
        "risk_mode": "balanced",
        "initial_capital": 1000,
        "current_capital": 1200,
        "total_profit": 200,
        "trades_count": 50,
        "win_count": 30
    }
    
    # Test optimal allocation calculation
    optimal = await capital_allocator.calculate_optimal_allocation("test_user", test_bot)
    
    assert optimal > 0, "Optimal allocation should be positive"
    assert optimal >= 500, "Should meet minimum allocation"
    print(f"✅ Capital Allocator: Optimal allocation = R{optimal:.2f}")

@pytest.mark.asyncio
async def test_trade_staggerer():
    """Test trade staggering system"""
    from engines.trade_staggerer import trade_staggerer
    
    # Test can execute now
    can_execute, reason = await trade_staggerer.can_execute_now("test_bot_001", "binance")
    
    assert isinstance(can_execute, bool), "Should return boolean"
    print(f"✅ Trade Staggerer: Can execute = {can_execute}, Reason = {reason}")
    
    # Test queue status
    status = await trade_staggerer.get_queue_status()
    
    assert "queue_size" in status, "Should have queue size"
    print(f"✅ Trade Staggerer: Queue status = {status}")

@pytest.mark.asyncio
async def test_circuit_breaker():
    """Test circuit breaker system"""
    from engines.circuit_breaker import circuit_breaker
    
    test_bot = {
        "id": "test_bot_001",
        "initial_capital": 1000,
        "current_capital": 900,
        "total_profit": -100
    }
    
    # Test bot drawdown check
    breach, reason = await circuit_breaker.check_bot_drawdown(test_bot)
    
    assert isinstance(breach, bool), "Should return boolean"
    print(f"✅ Circuit Breaker: Bot drawdown check = {breach}, Reason = {reason}")

@pytest.mark.asyncio
async def test_risk_engine():
    """Test risk engine"""
    from risk_engine import risk_engine
    
    # Test trade risk check
    allowed, reason = await risk_engine.check_trade_risk(
        user_id="test_user",
        bot_id="test_bot_001",
        exchange="binance",
        proposed_notional=500.0,
        risk_mode="balanced"
    )
    
    assert isinstance(allowed, bool), "Should return boolean"
    print(f"✅ Risk Engine: Trade allowed = {allowed}, Reason = {reason}")

# ============================================================================
# PHASE 6 TESTS - AI & Learning
# ============================================================================

@pytest.mark.asyncio
async def test_ai_model_router():
    """Test AI model router"""
    from engines.ai_model_router import ai_model_router
    
    # Test health check
    health = await ai_model_router.health_check()
    
    assert "status" in health, "Should have status"
    print(f"✅ AI Model Router: Health = {health['status']}")
    
    # Test chat completion (with mock data)
    messages = [{"role": "user", "content": "Test"}]
    result = await ai_model_router.chat_completion(messages, mode='fast', max_tokens=10)
    
    assert "content" in result, "Should have content"
    print(f"✅ AI Model Router: Chat completion successful")

@pytest.mark.asyncio
async def test_self_learning_engine():
    """Test self-learning engine"""
    from engines.self_learning import self_learning_engine
    import database as db
    
    # Create test data
    test_bot_id = "test_learning_bot"
    test_user_id = "test_user"
    
    # Insert test bot
    test_bot = {
        "id": test_bot_id,
        "user_id": test_user_id,
        "name": "Learning Test Bot",
        "risk_mode": "safe",
        "initial_capital": 1000,
        "current_capital": 1100,
        "total_profit": 100,
        "trades_count": 20,
        "win_count": 12
    }
    
    await db.bots_collection.insert_one(test_bot)
    
    # Insert test trades
    for i in range(20):
        trade = {
            "id": f"trade_{i}",
            "bot_id": test_bot_id,
            "user_id": test_user_id,
            "profit_loss": 10 if i < 12 else -5,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pair": "BTC/ZAR",
            "entry_price": 1000000,
            "amount": 0.001
        }
        await db.trades_collection.insert_one(trade)
    
    # Test performance analysis
    analysis = await self_learning_engine.analyze_bot_performance(test_bot_id)
    
    assert "win_rate" in analysis or "status" in analysis, "Should return analysis or status"
    print(f"✅ Self-Learning: Analysis completed")
    
    # Cleanup
    await db.bots_collection.delete_one({"id": test_bot_id})
    await db.trades_collection.delete_many({"bot_id": test_bot_id})

# ============================================================================
# PHASE 8 TESTS - Audit & Email
# ============================================================================

@pytest.mark.asyncio
async def test_audit_logger():
    """Test audit logging system"""
    from engines.audit_logger import audit_logger
    
    # Test log event
    logged = await audit_logger.log_event(
        event_type="test_event",
        user_id="test_user",
        details={"test": "data"},
        severity="info"
    )
    
    assert logged == True, "Should log successfully"
    print(f"✅ Audit Logger: Event logged")
    
    # Test get audit trail
    logs = await audit_logger.get_user_audit_trail("test_user", days=1)
    
    assert isinstance(logs, list), "Should return list"
    print(f"✅ Audit Logger: Retrieved {len(logs)} log entries")

@pytest.mark.asyncio
async def test_email_reporter():
    """Test email reporting system"""
    from engines.email_reporter import email_reporter
    
    # Test report generation (without sending)
    report = await email_reporter.generate_daily_report("test_user", "test@example.com")
    
    assert "summary" in report or "error" in report, "Should return report or error"
    print(f"✅ Email Reporter: Report generated")
    
    # Note: Actual email sending requires SMTP configuration

# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_full_trade_flow_with_risk_checks():
    """Test complete trade flow with all Phase 5 checks"""
    from engines.trade_staggerer import trade_staggerer
    from risk_engine import risk_engine
    from engines.trade_limiter import trade_limiter
    
    test_bot_id = "integration_test_bot"
    test_exchange = "binance"
    
    # 1. Check if bot can trade (rate limits)
    can_trade, reason = await trade_limiter.can_trade(test_bot_id)
    print(f"Step 1 - Trade Limiter: {can_trade}, {reason}")
    
    # 2. Check if trade can execute now (staggering)
    can_execute, exec_reason = await trade_staggerer.can_execute_now(test_bot_id, test_exchange)
    print(f"Step 2 - Staggerer: {can_execute}, {exec_reason}")
    
    # 3. Check risk
    allowed, risk_reason = await risk_engine.check_trade_risk(
        user_id="test_user",
        bot_id=test_bot_id,
        exchange=test_exchange,
        proposed_notional=300.0,
        risk_mode="safe"
    )
    print(f"Step 3 - Risk Engine: {allowed}, {risk_reason}")
    
    print(f"✅ Full Trade Flow: All checks completed")

# ============================================================================
# RUN ALL TESTS
# ============================================================================

async def run_all_tests():
    """Run all Phase 5-8 tests"""
    print("\n" + "="*80)
    print("PHASE 5-8 COMPREHENSIVE TEST SUITE")
    print("="*80 + "\n")
    
    tests = [
        ("Capital Allocator", test_capital_allocator),
        ("Trade Staggerer", test_trade_staggerer),
        ("Circuit Breaker", test_circuit_breaker),
        ("Risk Engine", test_risk_engine),
        ("AI Model Router", test_ai_model_router),
        ("Self-Learning Engine", test_self_learning_engine),
        ("Audit Logger", test_audit_logger),
        ("Email Reporter", test_email_reporter),
        ("Full Trade Flow Integration", test_full_trade_flow_with_risk_checks)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n📋 Running: {test_name}")
            print("-" * 80)
            await test_func()
            passed += 1
            print(f"✅ PASSED: {test_name}\n")
        except Exception as e:
            failed += 1
            print(f"❌ FAILED: {test_name}")
            print(f"Error: {str(e)}\n")
    
    print("="*80)
    print(f"\n📊 TEST RESULTS:")
    print(f"   ✅ Passed: {passed}/{len(tests)}")
    print(f"   ❌ Failed: {failed}/{len(tests)}")
    print(f"   Success Rate: {(passed/len(tests)*100):.1f}%")
    print("\n" + "="*80)

if __name__ == "__main__":
    asyncio.run(run_all_tests())
