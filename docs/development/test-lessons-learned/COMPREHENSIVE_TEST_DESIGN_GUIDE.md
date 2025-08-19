# 綜合測試設計指南

**文檔版本**: 1.0.0  
**建立日期**: 2025-08-19  
**維護者**: 測試團隊  
**目的**: 整合所有測試相關的經驗教訓，提供單一真實來源

---

## 📚 目錄

1. [核心原則](#核心原則)
2. [架構設計](#架構設計)
3. [環境管理](#環境管理)
4. [Mock 策略](#mock-策略)
5. [資料要求](#資料要求)
6. [效能優化](#效能優化)
7. [常見陷阱與解決方案](#常見陷阱與解決方案)
8. [測試執行指南](#測試執行指南)

---

## 🎯 核心原則

### 五大黃金規則

#### 1. LLM Factory 規則 ⚠️ **最重要**
```python
# ❌ 絕對禁止 - 直接使用 OpenAI SDK
from openai import AsyncAzureOpenAI
from src.services.openai_client import get_azure_openai_client

# ✅ 唯一正確方式 - 使用 LLM Factory
from src.services.llm_factory import get_llm_client
client = get_llm_client(api_name="gap_analysis")
```

**原因**: 專案有統一的 LLM 管理機制，包含部署映射（如 gpt-4.1 → gpt-4.1-japan）

#### 2. 資料長度規則
- **所有 JD 和 Resume 必須 ≥ 200 字元**
- API 會返回 HTTP 422 錯誤如果不符合
- 使用 fixtures 管理測試資料

#### 3. 環境隔離規則
- 單元測試**絕不**依賴外部資源
- 使用 Mock 隔離所有外部依賴
- CI 環境不應需要配置檔案

#### 4. AsyncMock 規則
```python
# ✅ 正確 - 非同步操作使用 AsyncMock
mock_service.process = AsyncMock(return_value=result)

# ❌ 錯誤 - 會導致 "coroutine raised StopIteration"
mock_service.process = Mock(return_value=result)
```

#### 5. CI 環境適應規則
```python
# 測試必須偵測並適應 CI 環境
is_ci = os.environ.get('CI') == 'true' or os.environ.get('GITHUB_ACTIONS') == 'true'
delay = 0.1 if is_ci else 3.0  # CI 使用更短延遲
```

---

## 🏗️ 架構設計

### 測試分層策略

| 層級 | 目的 | Mock 策略 | 執行時間目標 |
|------|------|-----------|-------------|
| **單元測試 (UT)** | 測試單一組件邏輯 | 完全 Mock 所有外部依賴 | < 0.1s/test |
| **整合測試 (IT)** | 測試組件間互動 | Mock 外部 API，保留內部服務 | < 1s/test |
| **效能測試 (PT)** | 測量實際效能 | 使用真實 API | < 30s/test |
| **E2E 測試** | 端到端驗證 | 無 Mock，完全真實環境 | < 60s/test |

### 測試檔案結構
```
test/
├── unit/                      # 單元測試
│   └── services/              # 服務層單元測試
├── integration/               # 整合測試
├── performance/              # 效能測試
├── e2e_standalone/          # 獨立 E2E 測試（無全局 Mock）
├── fixtures/                # 共享測試資料
├── helpers/                 # 測試輔助函數
└── config/                  # 測試配置
    └── test_config.py       # CI/本地環境配置
```

### Test ID 命名規範
```python
# Test ID: API-{模組}-{編號}-{類型}
# 範例：API-GAP-001-UT（Gap Analysis 單元測試 001）

def test_gap_analysis_basic():
    """
    Test ID: API-GAP-001-UT
    測試基本差距分析功能
    """
    pass
```

---

## 🌍 環境管理

### CI vs 本地環境差異

| 項目 | 本地環境 | CI 環境 (GitHub Actions) |
|------|----------|------------------------|
| **配置檔案** | 存在 (.env, config/) | 不存在 |
| **資料庫** | 可能有本地 DB | 無資料庫連線 |
| **延遲時間** | 正常延遲 (3-20s) | 快速延遲 (0.05-0.5s) |
| **環境變數** | 開發者設定 | CI 預設值 |

### 環境隔離最佳實踐

#### 1. Fixture 環境管理
```python
@pytest.fixture(autouse=True)
def setup_test_environment():
    """完全隔離的測試環境設置"""
    original_env = os.environ.copy()
    
    # 清理可能干擾的環境變數
    for key in list(os.environ.keys()):
        if key.startswith(('AZURE_', 'OPENAI_', 'EMBEDDING_')):
            del os.environ[key]
    
    # 設置測試專用配置
    os.environ.update({
        'USE_V2_IMPLEMENTATION': 'true',
        'ENVIRONMENT': 'test',
        'TESTING': 'true'
    })
    
    yield
    
    # 恢復原始環境
    os.environ.clear()
    os.environ.update(original_env)
```

#### 2. 條件式初始化
```python
# ✅ 正確 - 檢查資源是否已存在
if not self._connection_pool:
    await self.initialize()

# ❌ 錯誤 - 無條件初始化
await self.initialize()  # 即使已經 mock 也會嘗試連線
```

---

## 🎭 Mock 策略

### 標準 Mock Fixtures

#### 1. LLM Client Mock
```python
@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing"""
    client = Mock()
    client.chat = Mock()
    client.chat.completions = Mock()
    
    # 模擬成功回應
    client.chat.completions.create = AsyncMock(
        return_value=Mock(
            choices=[Mock(
                message=Mock(content='{"result": "success"}')
            )]
        )
    )
    
    return client
```

#### 2. Async Context Manager Mock
```python
# ✅ 正確實作
class AsyncContextManager:
    def __init__(self, value):
        self.value = value
    async def __aenter__(self):
        return self.value
    async def __aexit__(self, *args):
        return None

mock_pool.get_client = lambda: AsyncContextManager(mock_client)
```

### Mock 位置規則

**Patch 在 import 位置，而非定義位置**

```python
# 如果 services.py 有：
from src.services.llm_factory import get_llm_client

# 則 patch：
@patch('src.services.gap_analysis_v2.get_llm_client')
```

### Mock 驗證
```python
# 驗證調用次數
assert mock_client.call_count == 2

# 驗證調用參數
mock_client.assert_called_with(
    api_name="gap_analysis",
    temperature=0.3
)

# 驗證未被調用
mock_client.assert_not_called()
```

---

## 📊 資料要求

### 最小長度要求

| 資料類型 | 最小長度 | 錯誤代碼 | HTTP 狀態碼 |
|---------|---------|----------|------------|
| Job Description | 200 字元 | VALIDATION_ERROR | 422 |
| Resume | 200 字元 | VALIDATION_ERROR | 422 |
| Keywords | 無限制 | - | - |

### 標準測試資料

```python
# 有效英文 JD (450 字元)
VALID_ENGLISH_JD = """
We are looking for a Senior Python Developer with 5+ years of experience 
in building scalable web applications using FastAPI and Django frameworks. 
Strong knowledge of Docker, Kubernetes, and AWS cloud services is required. 
The ideal candidate must have excellent problem-solving skills and ability 
to work independently in a fast-paced agile environment. Experience with 
microservices architecture, RESTful APIs, GraphQL, PostgreSQL, MongoDB, 
Redis, and distributed systems is highly valued.
""".strip()

# 有效繁中 JD (350 字元)
VALID_CHINESE_JD = """
我們正在尋找一位資深的Python開發工程師，需要具備FastAPI框架經驗，
熟悉Docker容器技術和Azure雲端服務。理想的候選人應該對微服務架構有深入理解，
並且有RESTful API開發經驗。具備CI/CD流程和測試驅動開發經驗者優先。
同時需要熟悉分散式系統設計，具備系統架構規劃能力和團隊合作精神。
需要至少五年以上的後端開發經驗。
""".strip()

# 邊界測試
BOUNDARY_199_CHARS = "x" * 199  # 應該失敗
BOUNDARY_200_CHARS = "x" * 200  # 應該通過
BOUNDARY_201_CHARS = "x" * 201  # 應該通過
```

### 不支援語言
```python
# 簡體中文 - 應被拒絕
UNSUPPORTED_SIMPLIFIED_CHINESE = "使用简体字的测试文本..."

# 日文 - 應被拒絕  
UNSUPPORTED_JAPANESE = "日本語のテストテキスト..."
```

---

## ⚡ 效能優化

### CI 環境優化

#### TestConfig 配置
```python
# test/config/test_config.py
class TestConfig:
    @staticmethod
    def is_ci_environment():
        return os.environ.get('CI') == 'true' or \
               os.environ.get('GITHUB_ACTIONS') == 'true'
    
    @staticmethod
    def get_retry_delays():
        if TestConfig.is_ci_environment():
            return {
                'rate_limit': {
                    'initial_delay': 0.1,
                    'max_delay': 1.0,
                    'multiplier': 1.5
                },
                'timeout': {
                    'initial_delay': 0.05,
                    'max_delay': 0.5,
                    'multiplier': 1.5
                }
            }
        else:
            # 本地環境使用正常延遲
            return {
                'rate_limit': {
                    'initial_delay': 3.0,
                    'max_delay': 20.0,
                    'multiplier': 2.0
                }
            }
```

### 效能基準

| 測試類型 | 本地目標 | CI 目標 |
|---------|---------|---------|
| 單元測試套件 | < 10s | < 5s |
| 整合測試套件 | < 30s | < 20s |
| 全部測試 | < 60s | < 40s |

---

## ⚠️ 常見陷阱與解決方案

### 問題 1: LLM Factory 違規
**症狀**: `500 Error: deployment does not exist`

**根本原因**: 直接使用 OpenAI SDK 而非 LLM Factory

**解決方案**:
```python
# 搜尋並替換所有直接調用
# 搜尋: get_azure_openai_client
# 搜尋: AsyncAzureOpenAI
# 替換為: get_llm_client
```

### 問題 2: 測試在本地通過但 CI 失敗
**症狀**: `Database configuration not found`

**根本原因**: CI 環境沒有配置檔案

**解決方案**:
```python
# 條件式初始化
if not self._connection_pool:  # 只在需要時初始化
    await self.initialize()
```

### 問題 3: AsyncMock 錯誤
**症狀**: `coroutine raised StopIteration`

**根本原因**: 對非同步函數使用 Mock 而非 AsyncMock

**解決方案**:
```python
# 使用正確的 Mock 類型
mock_async_func = AsyncMock()  # 非同步函數
mock_sync_func = Mock()        # 同步函數
```

### 問題 4: Import 系統污染
**症狀**: 測試互相影響，執行順序影響結果

**根本原因**: 在測試中修改 sys.path

**解決方案**:
```python
# ❌ 不要這樣做
sys.path.insert(0, some_path)

# ✅ 使用 fixture 和 patch
@patch('module.function')
def test_something(mock_func):
    pass
```

### 問題 5: JSON 解析失敗
**症狀**: `JSONDecodeError: Expecting property name`

**根本原因**: LLM 輸出被截斷（token 限制）

**解決方案**:
```python
# 動態計算所需 tokens
def calculate_required_tokens(text):
    chars_per_token = 3
    estimated_tokens = len(text) // chars_per_token
    buffer = 500  # 額外緩衝
    return estimated_tokens + buffer
```

---

## 🚀 測試執行指南

### 快速測試命令

```bash
# Ruff 檢查
ruff check src/ test/ --line-length=120

# 單元測試
pytest test/unit/ -v

# 整合測試
pytest test/integration/ -v

# 特定模組測試
./test/scripts/run_health_keyword_unit_integration.sh
./test/scripts/run_index_calculation_unit_integration.sh
./test/scripts/run_index_cal_gap_analysis_unit_integration.sh

# 完整 pre-commit 檢查
python test/scripts/pre_commit_check_advanced.py

# CI 環境模擬
CI=true GITHUB_ACTIONS=true pytest
```

### Pipeline 失敗處理

```bash
# CI/CD workflow 中正確捕獲退出碼
python test/scripts/pre_commit_check_advanced.py | tee test_output.log
TEST_EXIT_CODE=${PIPESTATUS[0]}
if [ $TEST_EXIT_CODE -ne 0 ]; then
    echo "❌ Tests failed"
    exit $TEST_EXIT_CODE
fi
```

### 診斷工具

```bash
# CI 環境診斷
python test/scripts/diagnose_ci_env.py

# 單一測試除錯
pytest test/unit/test_specific.py::TestClass::test_method -xvs

# 顯示所有 fixture
pytest --fixtures test/
```

---

## 📋 檢查清單

### 開發時檢查
- [ ] 所有 LLM 調用使用 `get_llm_client()`
- [ ] 測試資料 > 200 字元
- [ ] 非同步操作使用 AsyncMock
- [ ] 環境變數在 fixture 中管理
- [ ] 沒有修改 sys.path

### Code Review 檢查
- [ ] 無直接 OpenAI SDK 使用
- [ ] 有條件式初始化邏輯
- [ ] Mock 在正確位置
- [ ] 測試可獨立執行
- [ ] CI 環境適應邏輯

### 部署前檢查
- [ ] 通過 ruff 檢查
- [ ] 所有測試通過
- [ ] CI pipeline 成功
- [ ] 效能符合基準
- [ ] 文檔已更新

---

## 📚 相關文檔

- [Mock 策略指南](../issues/service-module-refactor/MOCK_STRATEGY_GUIDE.md)
- [測試資料要求](../issues/service-module-refactor/TEST_DATA_REQUIREMENTS.md)
- [CI/CD 配置](.github/workflows/ci-cd-main.yml)
- [測試配置](test/config/test_config.py)

---

**維護說明**: 
- 每次遇到新的測試問題，更新此文檔
- 定期審查並更新最佳實踐
- 保持與實際程式碼同步

**最後更新**: 2025-08-19