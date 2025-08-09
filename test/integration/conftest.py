"""
整合測試的共用 fixtures 和配置
專門用於解決測試隔離和間歇性失敗問題
"""
import asyncio
import contextlib
import gc
import os
import sys
import threading
from unittest.mock import AsyncMock

import pytest


def reset_global_services():
    """重置所有已知的全域服務實例"""
    # 重置 keyword_extraction_v2 的全域實例
    if 'src.services.keyword_extraction_v2' in sys.modules:
        import src.services.keyword_extraction_v2
        src.services.keyword_extraction_v2._keyword_extraction_service_v2 = None

    # 重置 index_calculation_v2 的全域實例
    if 'src.services.index_calculation_v2' in sys.modules:
        import src.services.index_calculation_v2
        src.services.index_calculation_v2._index_calculation_service_v2 = None

    # 確保 asyncio 模組狀態清潔
    # 檢查並清理任何可能殘留的 asyncio 補丁或修改
    if hasattr(asyncio, '_original_sleep'):
        # 如果有備份的原始 sleep, 恢復它
        asyncio.sleep = asyncio._original_sleep
        delattr(asyncio, '_original_sleep')

    # 可以根據需要添加更多服務的重置


@pytest.fixture(autouse=True, scope="class")
def isolate_test_class_environment():
    """
    確保每個測試類別在隔離的環境中執行
    這個 fixture 會自動應用到所有測試類別，在類別之間提供更強的隔離
    """
    # 保存當前環境狀態
    original_env = os.environ.copy()

    # 清除已知的全域狀態
    reset_global_services()

    # 記錄測試開始
    os.environ.get('PYTEST_CURRENT_TEST', 'unknown')
    threading.current_thread().ident  # noqa: B018

    yield

    # 測試後清理
    # 恢復環境變數
    os.environ.clear()
    os.environ.update(original_env)

    # 再次清除全域狀態
    reset_global_services()

    # 強制垃圾回收
    gc.collect()

    # 清理 unittest.mock 的全域狀態
    import unittest.mock
    # 清理所有活躍的 patches
    if hasattr(unittest.mock, '_patch_registry'):
        # 確保所有 patches 都已經停止
        try:
            for patch_obj in list(unittest.mock._patch_registry):
                if patch_obj and hasattr(patch_obj, 'stop'):
                    with contextlib.suppress(Exception):
                        patch_obj.stop()  # 忽略已經停止的 patch
        except Exception:  # noqa: S110
            pass  # 忽略清理過程中的錯誤

    # 清理模組的 import 狀態, 強制重新載入關鍵服務
    modules_to_reload = [
        'src.services.combined_analysis_v2',
        'src.services.index_calculation_v2',
        'src.services.embedding_client',
        'src.services.llm_factory'
    ]

    for module_name in modules_to_reload:
        if module_name in sys.modules:
            # 不實際重載模組, 只重置其中的全域變數
            module = sys.modules[module_name]
            if hasattr(module, '_instance'):
                module._instance = None
            if hasattr(module, '_client'):
                module._client = None


@pytest.fixture(autouse=True)
def isolate_test_function():
    """
    確保每個測試函數在隔離的環境中執行
    """
    # 測試前準備
    yield

    # 測試後快速清理
    gc.collect()


@pytest.fixture
def clean_event_loop():
    """為測試創建乾淨的 event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    yield loop

    # 清理未完成的任務
    try:
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()

        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    except Exception:  # noqa: S110
        pass
    finally:
        loop.close()


def create_configured_async_mock():
    """
    創建完整配置的 AsyncMock
    用於替代簡單的 AsyncMock(), 確保行為一致
    """
    mock = AsyncMock()

    # 配置 chat completion 方法
    mock.chat_completion = AsyncMock(return_value={
        "choices": [{
            "message": {
                "content": '{"keywords": ["Python", "Developer"], "confidence": 0.9}'
            }
        }],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        }
    })

    # 配置 complete_text 方法
    mock.complete_text = AsyncMock(return_value={
        "text": '{"keywords": ["Python"], "confidence": 0.85}'
    })

    # 配置關閉方法
    mock.close = AsyncMock()

    # 配置重試相關屬性 (防止 AttributeError)
    mock.max_retries = 3
    mock.retry_delays = [1, 2, 4]

    # 確保 mock 可以作為 async context manager
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)

    return mock


class ThreadSafeEnvironment:
    """
    線程安全的環境變數管理器
    用於並行測試時避免環境變數競爭
    """
    _local = threading.local()
    _lock = threading.Lock()

    @classmethod
    def set(cls, key: str, value: str):
        """線程安全地設置環境變數"""
        with cls._lock:
            if not hasattr(cls._local, 'env'):
                cls._local.env = {}
            cls._local.env[key] = value
            # 同時更新真實的環境變數
            os.environ[key] = value

    @classmethod
    def get(cls, key: str, default=None):
        """線程安全地獲取環境變數"""
        with cls._lock:
            if not hasattr(cls._local, 'env'):
                cls._local.env = {}
            # 優先從線程本地存儲獲取
            value = cls._local.env.get(key)
            if value is None:
                value = os.environ.get(key, default)
            return value

    @classmethod
    def clear(cls):
        """清除線程本地的環境變數"""
        with cls._lock:
            if hasattr(cls._local, 'env'):
                cls._local.env.clear()


@pytest.fixture
def thread_safe_env():
    """提供線程安全的環境變數管理"""
    ThreadSafeEnvironment.clear()
    yield ThreadSafeEnvironment
    ThreadSafeEnvironment.clear()


@pytest.fixture
def stable_mock_factory():
    """
    提供穩定的 mock 工廠
    確保所有測試使用相同配置的 mock
    """
    def _create_mock(mock_type='azure_openai'):
        if mock_type == 'azure_openai':
            return create_configured_async_mock()
        elif mock_type == 'keyword_service':
            mock = AsyncMock()
            mock.validate_input = AsyncMock(return_value={
                "job_description": "test description",
                "max_keywords": 15
            })
            mock.process = AsyncMock(return_value={
                "keywords": ["Python", "Developer"],
                "keyword_count": 2,
                "confidence_score": 0.9,
                "extraction_method": "test"
            })
            mock.close = AsyncMock()
            return mock
        else:
            return AsyncMock()

    return _create_mock

@pytest.fixture(autouse=True, scope="function")
def prevent_external_calls():
    """
    Prevent all external HTTP/HTTPS calls during integration tests.

    This fixture ensures that no test accidentally makes real network calls
    to external services like Azure OpenAI, even if mocks fail.
    """
    with (
        # Block all HTTP libraries at the lowest level
        patch('httpx.AsyncClient.post', side_effect=RuntimeError("External HTTP calls blocked in tests")),
        patch('httpx.AsyncClient.get', side_effect=RuntimeError("External HTTP calls blocked in tests")),
        patch('aiohttp.ClientSession.post', side_effect=RuntimeError("External HTTP calls blocked in tests")),
        patch('aiohttp.ClientSession.get', side_effect=RuntimeError("External HTTP calls blocked in tests")),
        patch('requests.post', side_effect=RuntimeError("External HTTP calls blocked in tests")),
        patch('requests.get', side_effect=RuntimeError("External HTTP calls blocked in tests")),

        # Block urllib3 and socket level calls
        patch('urllib3.poolmanager.PoolManager.urlopen', side_effect=RuntimeError("External HTTP calls blocked in tests")),
        patch('socket.create_connection', side_effect=RuntimeError("External socket connections blocked in tests")),

        # Block OpenAI SDK direct calls - removed to avoid importing openai module
        # Direct OpenAI SDK usage is prevented by LLM Factory pattern
    ):
        yield


@pytest.fixture
def comprehensive_mock_services():
    """
    Comprehensive mock services that cover all possible service calls.

    This fixture provides fully configured mock services that return
    realistic test data for all Azure OpenAI operations.
    """
    # Mock embedding service - IndexCalculationServiceV2 expects create_embeddings to return list of embeddings
    embedding_mock = AsyncMock()

    # Configure create_embeddings as an AsyncMock that returns proper format
    embedding_mock.create_embeddings = AsyncMock(return_value=[
        [0.1 + i * 0.01] * 1536 for i in range(2)  # Generate 2 embeddings (resume + JD)
    ])
    embedding_mock.close = AsyncMock()
    # Configure as proper async context manager
    embedding_mock.__aenter__ = AsyncMock(return_value=embedding_mock)
    embedding_mock.__aexit__ = AsyncMock(return_value=None)

    # Mock LLM service with realistic gap analysis response
    llm_mock = AsyncMock()
    llm_mock.chat_completion = AsyncMock(return_value={
        "choices": [{
            "message": {
                "content": json.dumps({
                    "CoreStrengths": "<ol><li>Strong Python programming skills</li><li>Experience with web frameworks</li></ol>",
                    "KeyGaps": "<ol><li>Limited cloud experience</li><li>Missing DevOps skills</li></ol>",
                    "QuickImprovements": "<ol><li>Learn Docker basics</li><li>Get AWS certification</li></ol>",
                    "OverallAssessment": "<p>Good technical foundation but needs cloud and DevOps skills</p>",
                    "SkillSearchQueries": ["AWS", "Docker", "Kubernetes", "CI/CD"]
                })
            }
        }],
        "usage": {
            "prompt_tokens": 150,
            "completion_tokens": 75,
            "total_tokens": 225
        }
    })
    llm_mock.close = AsyncMock()

    # Mock keyword extraction service
    keyword_mock = AsyncMock()
    keyword_mock.validate_input = AsyncMock(return_value={
        "job_description": "test job description with sufficient length to pass validation requirements for testing purposes",
        "max_keywords": 15
    })
    keyword_mock.process = AsyncMock(return_value={
        "keywords": ["Python", "FastAPI", "Docker", "AWS", "Git", "REST API", "SQL", "Linux"],
        "keyword_count": 8,
        "confidence_score": 0.87,
        "extraction_method": "llm_based",
        "processing_time_ms": 280
    })
    keyword_mock.close = AsyncMock()

    # Mock resource pool manager with proper async context manager
    pool_mock = Mock()

    # Create a proper async context manager for get_client
    class AsyncContextManagerMock:
        def __init__(self, return_value):
            self.return_value = return_value

        async def __aenter__(self):
            return self.return_value

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

    # Configure get_client to return an async context manager
    pool_mock.get_client = Mock(return_value=AsyncContextManagerMock(llm_mock))
    pool_mock.get_stats = Mock(return_value={
        "clients_created": 2,
        "clients_reused": 8,
        "current_pool_size": 3,
        "pool_hits": 8,
        "pool_misses": 2
    })

    return {
        "embedding": embedding_mock,
        "llm": llm_mock,
        "keyword": keyword_mock,
        "resource_pool": pool_mock
    }


@pytest.fixture(autouse=True)
def mock_all_external_services(comprehensive_mock_services):
    """
    Automatically mock all external services for integration tests.

    This fixture is applied to every test in the integration directory
    and ensures complete isolation from external dependencies.

    We rely on the global mocks from the root conftest.py for the core service patches,
    and add integration-specific mocks here.
    """
    services = comprehensive_mock_services
    # Resource pool mock is already configured in comprehensive_mock_services

    with (
        # Patch ResourcePoolManager at both import locations to ensure complete mocking
        patch('src.services.resource_pool_manager.ResourcePoolManager', return_value=services["resource_pool"]),
        patch('src.services.combined_analysis_v2.ResourcePoolManager', return_value=services["resource_pool"]),

        # Mock the embedding client factory function to return our async mock
        patch('src.services.embedding_client.get_azure_embedding_client') as mock_get_embedding,
        patch('src.services.index_calculation_v2.get_azure_embedding_client') as mock_get_embedding_index,

        # Also mock the class directly in case it's imported directly
        patch('src.services.embedding_client.AzureEmbeddingClient', return_value=services["embedding"]),

        # Low-level client creation prevention - removed to avoid importing openai module
        # Direct OpenAI SDK usage is prevented by LLM Factory pattern
    ):
        # Configure the embedding client mocks to return our AsyncMock
        mock_get_embedding.return_value = services["embedding"]
        mock_get_embedding_index.return_value = services["embedding"]

        yield services


import json  # noqa: E402
from unittest.mock import Mock, patch  # noqa: E402
