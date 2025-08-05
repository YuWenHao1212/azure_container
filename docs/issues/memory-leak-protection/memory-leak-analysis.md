# Memory Leak Protection Analysis for Azure Container Apps

## Executive Summary

This document provides a comprehensive analysis of memory leak risks and protection strategies for deploying the Index Cal and Gap Analysis V2 API to Azure Container Apps. Based on backend architecture analysis, we've identified critical areas requiring immediate attention before production deployment.

## 1. Current Architecture Memory Risk Assessment

### 1.1 High-Risk Components

#### ResourcePoolManager
- **Risk Level**: 🔴 High
- **Issue**: Maintains long-lived Azure OpenAI client connections
- **Impact**: Each client holds HTTP session and connection pool
- **Potential Leak**: 5-10MB per client × max_pool_size

```python
# Current implementation risk
class ResourcePoolManager:
    def __init__(self, min_size=2, max_size=10):
        self._clients = []  # Risk: Unbounded growth
        self._pool = asyncio.Queue(maxsize=max_size)
```

#### Parallel Processing (TaskGroup)
- **Risk Level**: 🟡 Medium
- **Issue**: Python 3.11 TaskGroup may accumulate unfinished tasks
- **Impact**: Each pending task holds request context
- **Potential Leak**: 1-2MB per pending task

#### HTTP Sessions
- **Risk Level**: 🔴 High
- **Issue**: aiohttp sessions not properly closed
- **Impact**: Connection pool exhaustion
- **Potential Leak**: 100KB-1MB per unclosed session

### 1.2 Memory Growth Patterns

```
Time (hours) | Memory Usage | Risk Level
0            | 200MB       | ✅ Normal
6            | 400MB       | ✅ Normal
12           | 800MB       | 🟡 Warning
24           | 1.6GB       | 🔴 Critical
48           | 2.0GB+      | 💥 Container Restart
```

## 2. Azure Container Apps Constraints

### 2.1 Memory Limits
- **Default Limit**: 2GB (2Gi)
- **Hard Limit**: Container killed when exceeded
- **Recommended Usage**: Stay below 80% (1.6GB)

### 2.2 Scaling Behavior
```yaml
# Current configuration risk
resources:
  memory: 2Gi  # Hard limit
scale:
  maxReplicas: 10  # Each replica can consume 2GB
  # Total potential memory: 20GB across instances
```

### 2.3 Cost Implications
- Memory overuse triggers unnecessary scaling
- Each additional replica costs ~$50/month
- Memory leaks can increase costs by 200-300%

## 3. Python-Specific Considerations

### 3.1 Garbage Collection Challenges
```python
# Issue 1: Circular references
class ServiceA:
    def __init__(self):
        self.service_b = ServiceB(self)  # Circular reference

class ServiceB:
    def __init__(self, service_a):
        self.service_a = service_a  # Won't be garbage collected

# Issue 2: Global state accumulation
_global_cache = {}  # Never cleared
_singleton_instances = {}  # Grows over time
```

### 3.2 Async Context Leaks
```python
# Common leak pattern in FastAPI
active_tasks = set()

@app.post("/process")
async def process():
    task = asyncio.create_task(long_running_operation())
    active_tasks.add(task)  # Never removed
    return {"status": "processing"}
```

## 4. Proposed Solution Architecture

### 4.1 Centralized Resource Manager

```python
# src/core/resource_manager.py
class ResourceManager:
    """Centralized resource lifecycle management"""
    
    def __init__(self):
        self._resources: Dict[str, Any] = {}
        self._cleanup_tasks: List[Callable] = []
        self._memory_threshold_mb = 1500  # 75% of 2GB
        self._last_cleanup = time.time()
        
    async def register_resource(self, name: str, resource: Any, cleanup_fn: Callable):
        """Register a resource with its cleanup function"""
        self._resources[name] = resource
        self._cleanup_tasks.append(cleanup_fn)
        
    async def check_memory_pressure(self):
        """Monitor memory usage and trigger cleanup if needed"""
        current_memory = self._get_process_memory_mb()
        
        if current_memory > self._memory_threshold_mb:
            logger.warning(f"Memory pressure detected: {current_memory}MB")
            await self.cleanup_old_resources()
```

### 4.2 HTTP Session Management

```python
# src/core/http_manager.py
class HTTPSessionManager:
    """Manage all HTTP sessions with automatic cleanup"""
    
    def __init__(self, max_sessions: int = 100):
        self._sessions: Dict[str, aiohttp.ClientSession] = {}
        self._session_last_used: Dict[str, float] = {}
        self._max_sessions = max_sessions
        
    async def get_session(self, key: str) -> aiohttp.ClientSession:
        """Get or create a session with automatic lifecycle management"""
        if key in self._sessions:
            self._session_last_used[key] = time.time()
            return self._sessions[key]
            
        # Cleanup old sessions if at limit
        if len(self._sessions) >= self._max_sessions:
            await self._cleanup_oldest_sessions()
            
        session = aiohttp.ClientSession()
        self._sessions[key] = session
        self._session_last_used[key] = time.time()
        return session
```

### 4.3 Cache Size Limiting

```python
# src/core/cache_manager.py
from functools import lru_cache
from typing import Any, Callable

class BoundedLRUCache:
    """LRU cache with memory-aware size limits"""
    
    def __init__(self, maxsize: int = 1000, max_memory_mb: int = 100):
        self._cache = {}
        self._maxsize = maxsize
        self._max_memory_mb = max_memory_mb
        self._access_order = OrderedDict()
        
    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            # Update access order
            self._access_order.move_to_end(key)
            return self._cache[key]
        return None
        
    def put(self, key: str, value: Any):
        # Check memory limit
        if self._estimate_memory_usage() > self._max_memory_mb:
            self._evict_lru_items()
            
        # Check size limit
        if len(self._cache) >= self._maxsize:
            self._evict_lru_items()
            
        self._cache[key] = value
        self._access_order[key] = time.time()
```

## 5. Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1)
1. Implement ResourceManager
2. Create HTTPSessionManager
3. Add BoundedLRUCache
4. Integrate with application lifecycle

### Phase 2: Monitoring & Metrics (Week 2)
1. Add memory monitoring endpoints
2. Integrate Application Insights
3. Create memory dashboards
4. Set up alerting rules

### Phase 3: Testing & Validation (Week 3)
1. Create memory leak detection tests
2. Run 24-hour stress tests
3. Validate cleanup mechanisms
4. Performance benchmarking

### Phase 4: Production Rollout (Week 4)
1. Deploy to staging environment
2. Monitor for 48 hours
3. Adjust thresholds based on data
4. Production deployment

## 6. Monitoring Strategy

### 6.1 Key Metrics
- Process memory usage (RSS)
- Heap size and growth rate
- Number of active HTTP sessions
- Cache hit/miss ratios
- Garbage collection frequency
- Task queue depth

### 6.2 Application Insights Queries

```kusto
// Memory usage trend
customMetrics
| where name == "process_memory_mb"
| summarize avg(value), max(value), percentile(value, 95) by bin(timestamp, 5m)
| render timechart

// Memory leak detection
customMetrics
| where name == "process_memory_mb"
| summarize memory_mb = avg(value) by bin(timestamp, 1h)
| extend memory_growth = memory_mb - prev(memory_mb)
| where memory_growth > 50  // Alert on 50MB/hour growth
```

### 6.3 Alert Configuration

| Alert Name | Condition | Severity | Action |
|------------|-----------|----------|---------|
| High Memory Usage | > 1.5GB for 5 min | Warning | Trigger cleanup |
| Critical Memory | > 1.8GB for 2 min | Critical | Force GC + cleanup |
| Memory Growth | > 100MB/hour | Warning | Investigate leak |
| Container Restart | Memory OOM | Critical | Page on-call |

## 7. Testing Strategy

### 7.1 Memory Leak Detection Tests

```python
# test/memory/test_memory_leak_detection.py
import asyncio
import psutil
import gc

class TestMemoryLeaks:
    async def test_long_running_simulation(self):
        """Simulate 24 hours of operation"""
        initial_memory = self._get_memory_mb()
        
        # Simulate 1440 minutes (24 hours)
        for minute in range(1440):
            # Make 10 requests per minute
            tasks = [self._make_request() for _ in range(10)]
            await asyncio.gather(*tasks)
            
            # Check memory every hour
            if minute % 60 == 0:
                current_memory = self._get_memory_mb()
                memory_growth = current_memory - initial_memory
                
                # Fail if memory grows > 500MB in 24 hours
                assert memory_growth < 500, f"Memory leak detected: {memory_growth}MB growth"
```

### 7.2 Resource Cleanup Verification

```python
async def test_resource_cleanup():
    """Verify all resources are properly cleaned up"""
    manager = ResourceManager()
    
    # Create resources
    sessions = [aiohttp.ClientSession() for _ in range(100)]
    for i, session in enumerate(sessions):
        await manager.register_resource(f"session_{i}", session, session.close)
    
    # Trigger cleanup
    await manager.cleanup_all_resources()
    
    # Verify all sessions are closed
    for session in sessions:
        assert session.closed, "Session not properly closed"
```

## 8. Emergency Response Procedures

### Level 1: Warning (>1.5GB)
1. Automatic cache clearing
2. Force garbage collection
3. Close idle HTTP sessions
4. Log warning metrics

### Level 2: Critical (>1.8GB)
1. All Level 1 actions
2. Reject new requests (circuit breaker)
3. Force close all idle resources
4. Aggressive garbage collection

### Level 3: Emergency (>1.9GB)
1. All Level 2 actions
2. Graceful shutdown initiation
3. Drain active requests
4. Trigger container restart

## 9. Best Practices Checklist

### For Developers
- [ ] Always use context managers for resources
- [ ] Set explicit cache size limits
- [ ] Clean up global state in shutdown handlers
- [ ] Use weak references where appropriate
- [ ] Profile memory usage during development

### For DevOps
- [ ] Configure appropriate memory limits
- [ ] Set up memory-based autoscaling
- [ ] Monitor memory trends continuously
- [ ] Plan for graceful degradation
- [ ] Document memory tuning parameters

## 10. Conclusion

Memory leak protection is critical for Azure Container Apps deployment success. Without proper measures, our application faces:
- Frequent container restarts
- Degraded user experience  
- Increased operational costs
- Potential data loss

The proposed solution provides comprehensive protection through:
- Proactive resource management
- Continuous monitoring
- Automatic cleanup mechanisms
- Emergency response procedures

This investment in memory management will ensure stable, cost-effective operation of our Index Cal and Gap Analysis V2 API in production.

---

**Document Version**: 1.0  
**Last Updated**: 2025-08-04  
**Author**: Backend Architecture Team  
**Status**: Ready for Implementation