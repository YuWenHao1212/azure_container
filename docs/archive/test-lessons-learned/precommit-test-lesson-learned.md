# Pre-commit Test Isolation - DO's and DON'T's

## Date: 2025-08-09

## ✅ DO's

### Test Fixture Best Practices
- **DO keep fixtures pure** - Don't modify global state in fixtures
- **DO clean up after tests** - Reset singletons and global state in teardown
- **DO use AsyncMock for async code** - Always use AsyncMock for async operations
- **DO implement full protocols** - Async context managers need both `__aenter__` and `__aexit__`

### Mock Configuration
- **DO patch at import location** - Patch where the module imports, not where it's defined
- **DO double-patch when necessary** - If a service is imported in multiple places, patch all locations
- **DO verify mock configuration** - Check callable(), asyncio.iscoroutinefunction(), and protocol methods
- **DO use consistent mock types** - AsyncMock for async, Mock for sync

### Test Strategy
- **DO test with real services when needed** - Don't over-mock, some tests need real behavior
- **DO verify test isolation** - Run tests in different orders to ensure they pass
- **DO create standardized mock helpers** - Reuse common mock patterns

## ❌ DON'T's

### Import System
- **DON'T modify sys.path in tests** - It pollutes the import system for subsequent tests
- **DON'T import modules dynamically in fixtures** - Define mocks inline instead

### Mock Mistakes
- **DON'T mix Mock and AsyncMock** - Use the appropriate type consistently
- **DON'T assume patch location** - Check actual import statements in the code
- **DON'T over-mock** - Some tests need real service behavior (e.g., cache tests)
- **DON'T return Mock from async context managers** - Must return proper async context manager

### Test Isolation
- **DON'T ignore test isolation** - Tests should pass regardless of execution order
- **DON'T leave global state modified** - Always clean up in teardown
- **DON'T assume test execution order** - Each test should be independent

## Quick Reference Examples

### ✅ GOOD - Async Context Manager Mock
```python
class AsyncContextManager:
    def __init__(self, value):
        self.value = value
    async def __aenter__(self):
        return self.value
    async def __aexit__(self, *args):
        return None

mock_pool.get_client = lambda: AsyncContextManager(mock_client)
```

### ❌ BAD - Regular Mock for Async Context Manager
```python
# This will cause "coroutine raised StopIteration" error
mock_pool.get_client = Mock(return_value=mock_client)
```

### ✅ GOOD - Patch at Import Location
```python
# If combined_analysis_v2.py has: from src.services.resource_pool_manager import ResourcePoolManager
patch('src.services.combined_analysis_v2.ResourcePoolManager')
```

### ❌ BAD - Runtime sys.path Modification
```python
# Don't do this in fixtures - pollutes import system
def mock_services(self):
    import sys
    sys.path.insert(0, os.path.dirname(...))
    from integration.helpers.mock_helpers import create_resource_pool_mock
```

---

**Last Updated**: 2025-08-09  
**Status**: All tests passing ✅