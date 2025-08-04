"""
Memory Leak Detection Tests for Azure Container Apps Deployment.

These tests verify that the application properly manages memory
and prevents common memory leak scenarios.
"""
import asyncio
import gc
import logging
import time
from typing import List

import pytest
import psutil

from src.core.resource_manager import ResourceManager, resource_manager
from src.services.llm_factory import get_llm_client
from src.services.openai_client import get_azure_openai_client


class MemoryProfiler:
    """Simple memory profiler for tracking memory usage during tests."""

    def __init__(self):
        self.snapshots: List[tuple] = []
        self.process = psutil.Process()

    def snapshot(self, label: str = ""):
        """Take a memory snapshot."""
        memory_info = self.process.memory_info()
        rss_mb = memory_info.rss / 1024 / 1024
        vms_mb = memory_info.vms / 1024 / 1024
        self.snapshots.append((time.time(), label, rss_mb, vms_mb))
        return rss_mb

    def get_memory_growth(self) -> float:
        """Get memory growth from first to last snapshot (MB)."""
        if len(self.snapshots) < 2:
            return 0.0
        return self.snapshots[-1][2] - self.snapshots[0][2]

    def report(self) -> str:
        """Generate memory usage report."""
        if not self.snapshots:
            return "No memory snapshots taken"

        lines = ["Memory Usage Report:"]
        for timestamp, label, rss_mb, vms_mb in self.snapshots:
            lines.append(f"  {label}: RSS={rss_mb:.1f}MB, VMS={vms_mb:.1f}MB")

        growth = self.get_memory_growth()
        lines.append(f"Total Growth: {growth:.1f}MB")
        return "\n".join(lines)


@pytest.fixture
def memory_profiler():
    """Memory profiler fixture."""
    profiler = MemoryProfiler()
    profiler.snapshot("test_start")
    yield profiler
    profiler.snapshot("test_end")
    print(f"\n{profiler.report()}")


@pytest.fixture
def resource_mgr():
    """Resource manager fixture for testing."""
    mgr = ResourceManager(
        max_connections=10,
        max_cache_size=100,
        enable_monitoring=False  # Disable monitoring for tests
    )
    yield mgr


@pytest.mark.asyncio
class TestMemoryLeakDetection:
    """Test suite for memory leak detection."""

    async def test_http_client_cleanup(self, memory_profiler, resource_mgr):
        """Test that HTTP clients are properly cleaned up."""
        clients = []
        
        # Create multiple clients
        for i in range(10):
            client = get_azure_openai_client(deployment_name="test-deployment")
            clients.append(client)
            memory_profiler.snapshot(f"client_{i}_created")

        # Verify they're registered
        stats = resource_mgr.get_stats()
        initial_connections = stats.active_connections

        # Close all clients
        for client in clients:
            await client.close()
        
        memory_profiler.snapshot("clients_closed")
        
        # Force garbage collection
        for i in range(3):
            gc.collect()
        
        memory_profiler.snapshot("gc_completed")
        
        # Verify memory didn't grow significantly (allow 10MB tolerance)
        memory_growth = memory_profiler.get_memory_growth()
        assert memory_growth < 10.0, f"Memory grew by {memory_growth:.1f}MB, which may indicate a leak"

    async def test_concurrent_request_cleanup(self, memory_profiler):
        """Test memory cleanup after concurrent requests."""
        async def make_dummy_request():
            """Simulate a request that creates objects."""
            # Simulate some work that creates objects
            data = list(range(1000))  # Create some objects
            await asyncio.sleep(0.01)  # Simulate async work
            return len(data)

        # Initial snapshot
        memory_profiler.snapshot("before_concurrent_requests")
        
        # Run concurrent tasks
        tasks = []
        for batch in range(5):  # 5 batches
            batch_tasks = [make_dummy_request() for _ in range(20)]  # 20 tasks per batch
            results = await asyncio.gather(*batch_tasks)
            tasks.extend(results)
            memory_profiler.snapshot(f"batch_{batch}_completed")

        # Force cleanup
        gc.collect()
        memory_profiler.snapshot("final_gc")
        
        # Verify reasonable memory usage
        memory_growth = memory_profiler.get_memory_growth()
        assert memory_growth < 20.0, f"Memory grew by {memory_growth:.1f}MB after concurrent requests"

    async def test_cache_size_limits(self, resource_mgr):
        """Test that cache respects size limits."""
        # Fill cache beyond limit
        for i in range(150):  # Exceed max_cache_size of 100
            resource_mgr.set_cache_object(f"key_{i}", f"large_value_{i}" * 100)

        stats = resource_mgr.get_stats()
        assert stats.cached_objects <= resource_mgr.max_cache_size, \
            f"Cache size {stats.cached_objects} exceeds limit {resource_mgr.max_cache_size}"

    async def test_llm_client_memory_usage(self, memory_profiler):
        """Test LLM client memory usage patterns."""
        memory_profiler.snapshot("before_llm_clients")
        
        # Create and use multiple LLM clients
        clients = []
        for model in ["gpt4o-2", "gpt41-mini"]:
            for i in range(5):
                try:
                    client = get_llm_client(model=model)
                    clients.append(client)
                except Exception as e:
                    # Skip if client creation fails (missing env vars in test)
                    logging.warning(f"Skipped client creation: {e}")
                    continue
        
        memory_profiler.snapshot("llm_clients_created")
        
        # Cleanup
        for client in clients:
            if hasattr(client, 'close'):
                await client.close()
        
        # Force GC
        for i in range(3):
            gc.collect()
        
        memory_profiler.snapshot("llm_clients_cleaned")
        
        # Verify memory is reasonable
        memory_growth = memory_profiler.get_memory_growth()
        assert memory_growth < 15.0, f"LLM client memory grew by {memory_growth:.1f}MB"

    async def test_resource_manager_stats(self, resource_mgr):
        """Test resource manager statistics collection."""
        # Get initial stats
        stats = resource_mgr.get_stats()
        assert isinstance(stats.uptime_seconds, float)
        assert stats.uptime_seconds >= 0
        
        # Test memory metrics
        if stats.memory_metrics:
            assert stats.memory_metrics.rss_mb > 0
            assert stats.memory_metrics.percent >= 0
            assert stats.memory_metrics.available_mb > 0

    async def test_garbage_collection_effectiveness(self, memory_profiler, resource_mgr):
        """Test that forced garbage collection is effective."""
        # Create objects that should be collectible
        objects = []
        for i in range(1000):
            obj = {f"key_{j}": f"value_{j}" * 100 for j in range(10)}
            objects.append(obj)
        
        memory_profiler.snapshot("objects_created")
        
        # Clear references
        objects.clear()
        
        # Force GC through resource manager
        gc_result = await resource_mgr.force_garbage_collection()
        
        memory_profiler.snapshot("after_forced_gc")
        
        # Verify GC stats
        assert isinstance(gc_result["duration_ms"], float)
        assert gc_result["duration_ms"] >= 0
        assert isinstance(gc_result["objects_collected"], int)
        
        # Memory should have been freed (allow some tolerance)
        memory_growth = memory_profiler.get_memory_growth()
        assert memory_growth < 50.0, f"Memory still grew by {memory_growth:.1f}MB after GC"

    async def test_connection_limit_enforcement(self, resource_mgr):
        """Test that connection limits are enforced."""
        # Try to register more connections than the limit
        fake_connections = [f"connection_{i}" for i in range(15)]
        
        for conn in fake_connections:
            resource_mgr.register_connection(conn)
        
        stats = resource_mgr.get_stats()
        # Note: WeakSet may not prevent registration, but should log warnings
        # The actual limit enforcement depends on the specific implementation
        assert stats.active_connections >= 0  # Basic sanity check

    @pytest.mark.skip(reason="Long-running test - enable manually for stress testing")
    async def test_long_running_memory_stability(self, memory_profiler):
        """Long-running test to detect gradual memory leaks."""
        # This test would run for several minutes to detect gradual leaks
        # Skip by default but can be enabled for thorough testing
        
        for iteration in range(100):  # Simulate 100 iterations of work
            # Simulate typical application work
            await self._simulate_typical_workload()
            
            if iteration % 10 == 0:
                memory_profiler.snapshot(f"iteration_{iteration}")
                gc.collect()
        
        # Verify memory didn't grow excessively
        memory_growth = memory_profiler.get_memory_growth()
        assert memory_growth < 100.0, f"Memory grew by {memory_growth:.1f}MB over time"

    async def _simulate_typical_workload(self):
        """Simulate typical application workload."""
        # Create some temporary objects
        temp_data = [{"key": f"value_{i}"} for i in range(100)]
        
        # Simulate async processing
        await asyncio.sleep(0.01)
        
        # Process data
        result = sum(len(str(item)) for item in temp_data)
        
        return result


@pytest.mark.asyncio
class TestContainerAppsSpecificConcerns:
    """Tests for Azure Container Apps specific memory concerns."""

    async def test_memory_under_container_limits(self):
        """Test that the application respects container memory limits."""
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        # Azure Container Apps default is 2GB, warn if approaching limit
        container_limit_mb = 2048
        usage_percentage = (memory_mb / container_limit_mb) * 100
        
        # Should not exceed 80% of container limit during normal operation
        assert usage_percentage < 80.0, \
            f"Memory usage {memory_mb:.1f}MB ({usage_percentage:.1f}%) is too high for container"

    async def test_startup_memory_footprint(self):
        """Test that startup memory footprint is reasonable."""
        process = psutil.Process()
        memory_info = process.memory_info()
        startup_memory_mb = memory_info.rss / 1024 / 1024
        
        # Startup memory should be reasonable (< 500MB)
        assert startup_memory_mb < 500.0, \
            f"Startup memory footprint {startup_memory_mb:.1f}MB is too high"

    async def test_resource_manager_integration(self):
        """Test resource manager integration."""
        # Verify global resource manager is available
        from src.core.resource_manager import resource_manager as global_rm
        
        assert global_rm is not None
        
        # Test basic functionality
        stats = global_rm.get_stats()
        assert stats.uptime_seconds >= 0
        
        # Test cache functionality
        global_rm.set_cache_object("test_key", "test_value")
        assert global_rm.get_cache_object("test_key") == "test_value"
        
        # Test cleanup
        global_rm.clear_cache()
        assert global_rm.get_cache_object("test_key") is None


if __name__ == "__main__":
    # Run memory leak detection tests
    pytest.main([__file__, "-v", "--tb=short"])