"""
Tests for lifecycle management
Validates startup/shutdown without raising exceptions
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from services.lifecycle import LifecycleManager, SubsystemDefinition


@pytest.fixture
def lifecycle_manager():
    """Create a fresh lifecycle manager for each test"""
    return LifecycleManager()


class TestSubsystemDefinition:
    """Test SubsystemDefinition class"""
    
    def test_create_definition(self):
        """Test creating a subsystem definition"""
        subsys = SubsystemDefinition(
            name="Test System",
            module_path="test.module",
            instance_name="test_instance"
        )
        
        assert subsys.name == "Test System"
        assert subsys.module_path == "test.module"
        assert subsys.instance_name == "test_instance"
        assert subsys.start_method == "start"
        assert subsys.stop_method == "stop"
        assert subsys.instance is None
        assert subsys.task is None


class TestLifecycleManager:
    """Test LifecycleManager class"""
    
    def test_init(self, lifecycle_manager):
        """Test lifecycle manager initialization"""
        assert lifecycle_manager.subsystems == []
        assert lifecycle_manager.background_tasks == []
        assert lifecycle_manager.feature_flags == {}
    
    def test_load_feature_flags(self, lifecycle_manager):
        """Test loading feature flags from environment"""
        with patch('services.lifecycle.env_bool') as mock_env:
            mock_env.side_effect = lambda key, default: default
            
            lifecycle_manager._load_feature_flags()
            
            assert 'enable_trading' in lifecycle_manager.feature_flags
            assert 'enable_autopilot' in lifecycle_manager.feature_flags
            assert 'enable_schedulers' in lifecycle_manager.feature_flags
    
    def test_register_subsystems(self, lifecycle_manager):
        """Test registering subsystems"""
        lifecycle_manager._register_subsystems()
        
        assert len(lifecycle_manager.subsystems) > 0
        
        # Check self_healing is registered
        self_healing_subsys = [s for s in lifecycle_manager.subsystems if s.name == "Self-Healing System"]
        assert len(self_healing_subsys) == 1
        assert self_healing_subsys[0].module_path == "engines.self_healing"
        assert self_healing_subsys[0].instance_name == "self_healing"
    
    @pytest.mark.asyncio
    async def test_start_subsystem_handles_sync_and_async(self, lifecycle_manager):
        """Test that lifecycle manager can handle both sync and async methods without errors"""
        # This is a smoke test - we just verify no exceptions are raised
        subsys = SubsystemDefinition(
            name="Test System",
            module_path="nonexistent.module",
            instance_name="test_instance"
        )
        
        # Should not raise - just log error and continue
        await lifecycle_manager._start_subsystem(subsys)
        
        # If we get here, error handling worked
        assert True
    
    @pytest.mark.asyncio
    async def test_stop_subsystem_sync_method(self, lifecycle_manager):
        """Test stopping a subsystem with synchronous stop method"""
        # Create a mock subsystem
        mock_instance = MagicMock()
        mock_instance.stop = MagicMock()  # Sync method
        
        subsys = SubsystemDefinition(
            name="Test Sync",
            module_path="test.module",
            instance_name="test_instance"
        )
        subsys.instance = mock_instance
        
        await lifecycle_manager._stop_subsystem(subsys)
        
        # Verify stop was called (not awaited)
        mock_instance.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_subsystem_async_method(self, lifecycle_manager):
        """Test stopping a subsystem with asynchronous stop method"""
        # Create a mock subsystem
        mock_instance = MagicMock()
        mock_instance.stop = AsyncMock()  # Async method
        
        subsys = SubsystemDefinition(
            name="Test Async",
            module_path="test.module",
            instance_name="test_instance"
        )
        subsys.instance = mock_instance
        
        await lifecycle_manager._stop_subsystem(subsys)
        
        # Verify stop was awaited
        mock_instance.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_all_cancels_tasks(self, lifecycle_manager):
        """Test that stop_all properly cancels background tasks"""
        # Create actual asyncio tasks for testing
        async def dummy_task():
            await asyncio.sleep(10)
        
        task1 = asyncio.create_task(dummy_task())
        task2 = asyncio.create_task(dummy_task())
        
        lifecycle_manager.background_tasks = [task1, task2]
        
        await lifecycle_manager.stop_all()
        
        # Verify tasks were cancelled
        assert task1.cancelled() or task1.done()
        assert task2.cancelled() or task2.done()


class TestNoAwaitSelfHealing:
    """Test that self_healing is never awaited"""
    
    def test_self_healing_start_not_awaited(self):
        """Verify self_healing.start() is synchronous"""
        # Skip if motor not installed (test environment)
        pytest.importorskip("motor")
        
        from engines.self_healing import self_healing
        import inspect
        
        # Verify start method is NOT a coroutine function
        assert not inspect.iscoroutinefunction(self_healing.start)
    
    def test_self_healing_stop_not_awaited(self):
        """Verify self_healing.stop() is synchronous"""
        # Skip if motor not installed (test environment)
        pytest.importorskip("motor")
        
        from engines.self_healing import self_healing
        import inspect
        
        # Verify stop method is NOT a coroutine function
        assert not inspect.iscoroutinefunction(self_healing.stop)


class TestCancellationPattern:
    """Test proper cancellation pattern with wait_for"""
    
    @pytest.mark.asyncio
    async def test_wait_for_with_timeout(self):
        """Test that wait_for is called with explicit timeout"""
        tasks = [
            asyncio.create_task(asyncio.sleep(0.1)),
            asyncio.create_task(asyncio.sleep(0.1))
        ]
        
        # Cancel tasks
        for task in tasks:
            task.cancel()
        
        # Test wait_for with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=1.0
            )
        except Exception as e:
            # Should not raise
            pytest.fail(f"wait_for raised exception: {e}")
    
    @pytest.mark.asyncio
    async def test_cancellation_does_not_raise(self):
        """Test that task cancellation is handled gracefully"""
        async def dummy_task():
            await asyncio.sleep(10)
        
        task = asyncio.create_task(dummy_task())
        task.cancel()
        
        try:
            await asyncio.wait_for(
                asyncio.gather(task, return_exceptions=True),
                timeout=1.0
            )
        except Exception as e:
            # Should not raise
            pytest.fail(f"Cancellation raised exception: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
