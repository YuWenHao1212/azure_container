"""
E2E 測試配置 - 無 mock，使用真實 API

這個 conftest.py 專門為獨立的 E2E 測試設計，
不包含任何 mock，允許測試使用真實的 Azure OpenAI API。
"""
import os
import sys
import pytest
from dotenv import load_dotenv

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

# 載入真實環境變數
load_dotenv(override=True)

@pytest.fixture(autouse=True)
def setup_e2e_environment():
    """設置 E2E 測試環境"""
    # 確保使用 V2 實作
    os.environ['USE_V2_IMPLEMENTATION'] = 'true'
    os.environ['ENABLE_PARTIAL_RESULTS'] = 'true'
    os.environ['LIGHTWEIGHT_MONITORING'] = 'true'
    os.environ['MONITORING_ENABLED'] = 'true'
    os.environ['ERROR_CAPTURE_ENABLED'] = 'true'
    
    # 禁用資源池以簡化測試
    os.environ['RESOURCE_POOL_ENABLED'] = 'false'
    
    # 標記為真實 E2E 測試
    os.environ['REAL_E2E_TEST'] = 'true'
    
    # 設置測試 API key（如果需要）
    if 'CONTAINER_APP_API_KEY' not in os.environ:
        os.environ['CONTAINER_APP_API_KEY'] = 'test-api-key'
    
    yield
    
    # 清理環境變數
    if 'REAL_E2E_TEST' in os.environ:
        del os.environ['REAL_E2E_TEST']

@pytest.fixture
def skip_if_no_api_keys():
    """檢查必要的 API 密鑰"""
    required_keys = [
        'AZURE_OPENAI_API_KEY',
        'AZURE_OPENAI_ENDPOINT',
        'EMBEDDING_API_KEY'
    ]
    
    missing_keys = [key for key in required_keys if not os.environ.get(key)]
    if missing_keys:
        pytest.skip(f"E2E tests require real API keys. Missing: {', '.join(missing_keys)}")

@pytest.fixture
def test_data():
    """載入測試數據"""
    import json
    fixture_path = os.path.join(
        os.path.dirname(__file__),
        '../fixtures/gap_analysis_v2/test_data_v2.json'
    )
    with open(fixture_path, encoding='utf-8') as f:
        return json.load(f)

# 註冊 E2E 標記
def pytest_configure(config):
    """註冊自定義標記"""
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )