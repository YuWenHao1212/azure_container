"""
整合測試的共用 fixtures 和配置
專門用於解決測試隔離和間歇性失敗問題
"""
import asyncio
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

    # 重置其他可能的全域狀態
    # 可以根據需要添加更多服務的重置


@pytest.fixture(autouse=True)
def isolate_test_environment():
    """
    確保每個測試在隔離的環境中執行
    這個 fixture 會自動應用到所有測試
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
