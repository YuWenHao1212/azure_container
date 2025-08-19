# 測試疑難排解指南

**文檔版本**: 1.0.0  
**建立日期**: 2025-08-19  
**維護者**: 測試團隊  
**目的**: 快速診斷和解決測試問題

---

## 📚 目錄

1. [常見問題速查表](#常見問題速查表)
2. [按症狀分類的解決方案](#按症狀分類的解決方案)
3. [診斷工具和技巧](#診斷工具和技巧)
4. [歷史案例分析](#歷史案例分析)
5. [預防措施](#預防措施)

---

## 🔍 常見問題速查表

| 問題類型 | 出現頻率 | 嚴重程度 | 典型症狀 | 快速解法 |
|---------|----------|----------|---------|----------|
| **LLM Factory 違規** | ⭐⭐⭐⭐⭐ | 🔴 高 | `deployment does not exist` | 使用 `get_llm_client()` |
| **CI 環境失敗** | ⭐⭐⭐⭐ | 🔴 高 | 本地過 CI 掛 | 條件初始化 |
| **Mock 類型錯誤** | ⭐⭐⭐ | 🟡 中 | `coroutine raised StopIteration` | 使用 AsyncMock |
| **資料長度不足** | ⭐⭐⭐ | 🟡 中 | HTTP 422 錯誤 | 確保 ≥200 字元 |
| **JSON 解析失敗** | ⭐⭐ | 🟡 中 | `JSONDecodeError` | 增加 max_tokens |
| **測試互相影響** | ⭐⭐ | 🟢 低 | 執行順序敏感 | fixture 隔離 |

---

## 🔧 按症狀分類的解決方案

### 症狀 1: "deployment does not exist" (500 錯誤)

#### 錯誤訊息
```
Error: The deployment 'gpt-4o-2' does not exist
Status Code: 500 Internal Server Error
```

#### 根本原因
直接使用 OpenAI SDK 而非 LLM Factory，導致部署名稱映射失敗

#### 診斷步驟
```bash
# 1. 搜尋違規代碼
grep -r "get_azure_openai_client\|AsyncAzureOpenAI" src/ test/

# 2. 檢查 import
grep -r "from openai import\|from src.services.openai_client" src/

# 3. 查看錯誤堆疊
pytest test/failing_test.py -xvs --tb=long
```

#### 解決方案
```python
# ❌ 錯誤代碼
from openai import AsyncAzureOpenAI
client = AsyncAzureOpenAI(...)

from src.services.openai_client import get_azure_openai_client
client = get_azure_openai_client()

# ✅ 正確代碼
from src.services.llm_factory import get_llm_client
client = get_llm_client(api_name="gap_analysis")
```

#### 預防措施
- Code review 時搜尋 OpenAI 直接調用
- 在 CLAUDE.local.md 明確標註此規則
- 使用 pre-commit hook 檢查

---

### 症狀 2: "測試在本地通過但在 CI 失敗"

#### 錯誤訊息
```
Database configuration not found. Please set POSTGRES_* environment variables
FileNotFoundError: config/postgres_connection.json
```

#### 根本原因
CI 環境沒有本地配置檔案或環境變數

#### 診斷步驟
```bash
# 1. 模擬 CI 環境
CI=true GITHUB_ACTIONS=true pytest test/failing_test.py -xvs

# 2. 檢查配置依賴
find . -name "*.json" -o -name "*.env" | grep -E "(config|env)"

# 3. 運行診斷腳本
python test/scripts/diagnose_ci_env.py
```

#### 解決方案
```python
# ❌ 錯誤：無條件初始化
async def get_data(self):
    await self.initialize()  # 總是嘗試連線
    return await self._fetch()

# ✅ 正確：條件初始化
async def get_data(self):
    if not self._connection_pool:  # 只在需要時初始化
        await self.initialize()
    return await self._fetch()
```

#### CI 環境配置
```python
# test/conftest.py
@pytest.fixture(autouse=True)
def mock_external_dependencies():
    """CI 環境自動 mock 外部依賴"""
    if os.environ.get('CI') == 'true':
        with patch('src.services.database.connect'):
            yield
    else:
        yield
```

---

### 症狀 3: "coroutine raised StopIteration"

#### 錯誤訊息
```
RuntimeError: coroutine raised StopIteration
TypeError: object Mock can't be used in 'await' expression
```

#### 根本原因
對非同步函數使用 Mock 而非 AsyncMock

#### 診斷步驟
```python
# 檢查函數是否為非同步
import asyncio
print(asyncio.iscoroutinefunction(target_function))

# 檢查 Mock 類型
print(type(mock_object))
print(callable(mock_object))
```

#### 解決方案
```python
# ❌ 錯誤：同步 Mock 用於非同步
mock_service.process = Mock(return_value=result)

# ✅ 正確：AsyncMock 用於非同步
mock_service.process = AsyncMock(return_value=result)

# ✅ 正確：Async Context Manager
class AsyncContextManager:
    def __init__(self, value):
        self.value = value
    async def __aenter__(self):
        return self.value
    async def __aexit__(self, *args):
        return None

mock_pool.acquire = lambda: AsyncContextManager(mock_conn)
```

---

### 症狀 4: "Job description must be at least 200 characters"

#### 錯誤訊息
```
HTTP 422 Unprocessable Entity
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Job description must be at least 200 characters"
    }
}
```

#### 根本原因
測試資料不符合 API 最小長度要求

#### 診斷步驟
```python
# 檢查資料長度
print(f"JD length: {len(job_description)}")
print(f"Resume length: {len(resume)}")

# 驗證所有測試資料
for name, data in test_data.items():
    if len(data) < 200:
        print(f"❌ {name}: {len(data)} chars")
```

#### 解決方案
```python
# ❌ 錯誤：太短的測試資料
test_jd = "Python Developer with FastAPI"  # 30 字元

# ✅ 正確：使用 fixture 提供充足資料
@pytest.fixture
def valid_jd():
    return """
    Senior Python Developer with 5+ years experience in FastAPI, 
    Django, Docker, Kubernetes, AWS. Strong background in 
    microservices, RESTful APIs, PostgreSQL, MongoDB, Redis. 
    Excellent problem-solving skills, team collaboration, and 
    ability to work in fast-paced agile environment.
    """.strip()  # 300+ 字元
```

---

### 症狀 5: "JSONDecodeError: Expecting property name"

#### 錯誤訊息
```
json.decoder.JSONDecodeError: Expecting property name enclosed in double quotes
Response preview: '{"CoreStrengths": ["Python", "FastAPI"'  # 明顯截斷
```

#### 根本原因
LLM 輸出被 token 限制截斷

#### 診斷步驟
```python
# 1. 檢查回應完整性
print(f"Response length: {len(response)}")
print(f"Last 50 chars: {response[-50:]}")

# 2. 驗證 JSON 結構
def check_json_complete(s):
    return s.count('{') == s.count('}') and \
           s.count('[') == s.count(']')
```

#### 解決方案
```python
# ✅ 動態計算 tokens
def calculate_tokens(resume, jd):
    chars_per_token = 3
    input_tokens = (len(resume) + len(jd)) // chars_per_token
    output_buffer = 2500  # 基本輸出需求
    
    if input_tokens > 2000:
        output_buffer += 1000  # 大輸入需要更多輸出空間
    
    return input_tokens + output_buffer

# ✅ JSON 修復機制
def repair_truncated_json(json_str):
    # 補充缺失括號
    open_braces = json_str.count('{')
    close_braces = json_str.count('}')
    json_str += '}' * (open_braces - close_braces)
    
    # 移除尾隨逗號
    json_str = re.sub(r',\s*}', '}', json_str)
    return json_str
```

---

### 症狀 6: "測試執行順序影響結果"

#### 錯誤訊息
```
PASSED when run alone
FAILED when run with other tests
Import errors after certain test runs
```

#### 根本原因
- 全局狀態污染
- sys.path 修改
- 單例未重置

#### 診斷步驟
```bash
# 1. 單獨執行測試
pytest test/test_file.py::test_function -xvs

# 2. 隨機順序執行
pytest --random-order

# 3. 反向執行
pytest --reverse
```

#### 解決方案
```python
# ✅ 使用 fixture 隔離
@pytest.fixture(autouse=True)
def reset_singleton():
    """重置單例狀態"""
    MyService._instance = None
    yield
    MyService._instance = None

# ✅ 環境變數隔離
@pytest.fixture
def isolated_env():
    original = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original)

# ❌ 避免修改 sys.path
# sys.path.insert(0, path)  # 不要這樣做
```

---

## 🛠️ 診斷工具和技巧

### 基本診斷命令

```bash
# 顯示失敗測試詳情
pytest --lf -xvs  # 只跑上次失敗的

# 進入除錯模式
pytest test.py --pdb  # 失敗時進入 pdb

# 顯示所有 print 輸出
pytest -s

# 顯示詳細堆疊
pytest --tb=long

# 測試執行時間分析
pytest --durations=10  # 顯示最慢的 10 個測試
```

### 進階診斷技巧

#### 1. Mock 調用追蹤
```python
# 查看所有 mock 調用
print(mock_object.mock_calls)
print(mock_object.call_args_list)

# 驗證特定調用
mock_object.assert_called_with(expected_args)
mock_object.assert_called_once()
```

#### 2. 環境變數檢查
```python
# 診斷 fixture
@pytest.fixture(autouse=True)
def log_environment():
    print("\n=== Test Environment ===")
    print(f"CI: {os.environ.get('CI')}")
    print(f"GITHUB_ACTIONS: {os.environ.get('GITHUB_ACTIONS')}")
    print(f"USE_V2: {os.environ.get('USE_V2_IMPLEMENTATION')}")
    yield
```

#### 3. 測試隔離驗證
```bash
# 執行單一測試多次
pytest test.py::test_func -count=5

# 不同順序執行
pytest --random-order-seed=1234
pytest --random-order-seed=5678
```

---

## 📖 歷史案例分析

### 案例 1: Course Batch Query CI 失敗（2025-08-19）

**時間線**:
- Commit 386ff72: ✅ 測試通過
- Commit 13f6bba: ❌ 新增 HTML 功能後失敗
- 診斷時間: 2 小時
- 根本原因: 無條件 `await self.initialize()`

**教訓**: 重構時保留防禦性檢查

### 案例 2: LLM Factory 違規（2025-08-05）

**問題**: 9 個服務直接使用 OpenAI SDK
**影響**: 所有效能測試失敗
**修復時間**: 8 小時（其中 2 小時在此問題）

**教訓**: Claude Code 需要明確告知專案規範

### 案例 3: Pre-commit Hook 失敗（2025-08-09）

**問題**: AsyncMock 實作不完整
**症狀**: `coroutine raised StopIteration`
**解決**: 實作完整 async context manager

**教訓**: 測試 async 協議需要完整實作

---

## 🛡️ 預防措施

### 開發階段預防

1. **使用模板和 Snippets**
```python
# VS Code snippet for test
"pytest-async": {
    "prefix": "pytest-async",
    "body": [
        "@pytest.mark.asyncio",
        "async def test_${1:name}():",
        "    \"\"\"",
        "    Test ID: API-${2:MODULE}-${3:001}-UT",
        "    ${4:description}",
        "    \"\"\"",
        "    ${0:pass}"
    ]
}
```

2. **Pre-commit Hooks**
```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: check-llm-factory
      name: Check LLM Factory Usage
      entry: ./scripts/check_llm_factory.sh
      language: script
      files: \.(py)$
```

3. **自動化檢查腳本**
```bash
#!/bin/bash
# scripts/check_llm_factory.sh
if grep -r "AsyncAzureOpenAI\|get_azure_openai_client" src/ test/; then
    echo "❌ Found direct OpenAI SDK usage!"
    exit 1
fi
```

### Code Review 檢查點

- [ ] 無直接 OpenAI SDK import
- [ ] 測試資料使用 fixtures
- [ ] Mock 類型正確（Async/Sync）
- [ ] 環境變數在 fixture 管理
- [ ] 資源初始化有條件判斷
- [ ] 測試有 Test ID 標記

### CI/CD 配置建議

```yaml
# .github/workflows/ci-cd-main.yml
- name: Run Tests with Diagnostics
  run: |
    # 啟用診斷模式
    export TEST_DIAGNOSTICS=true
    export PYTEST_VERBOSE=true
    
    # 執行測試並保存輸出
    python test/scripts/pre_commit_check_advanced.py | tee test_output.log
    TEST_EXIT_CODE=${PIPESTATUS[0]}
    
    # 失敗時上傳診斷資訊
    if [ $TEST_EXIT_CODE -ne 0 ]; then
        echo "::error::Tests failed"
        python test/scripts/diagnose_ci_env.py
        exit $TEST_EXIT_CODE
    fi
```

---

## 📊 問題統計和趨勢

### 2025 Q3 問題分布
```
LLM Factory 違規:     ████████████ 35%
CI 環境問題:         ████████ 25%
Mock 類型錯誤:       ██████ 20%
資料長度問題:        ████ 15%
其他:               ██ 5%
```

### 改善趨勢
- LLM Factory 違規：從每週 5 次降至 1 次
- CI 失敗率：從 30% 降至 5%
- 平均修復時間：從 4 小時降至 30 分鐘

---

## 🚑 緊急聯絡和資源

### 快速修復資源
- [綜合測試指南](./COMPREHENSIVE_TEST_DESIGN_GUIDE.md)
- [快速參考卡](./TEST_QUICK_REFERENCE.md)
- [Mock 策略指南](../issues/service-module-refactor/MOCK_STRATEGY_GUIDE.md)

### 診斷腳本位置
- `/test/scripts/diagnose_ci_env.py`
- `/test/scripts/check_mock_usage.py`
- `/test/scripts/validate_test_data.py`

### 關鍵配置檔案
- `/test/config/test_config.py`
- `/test/conftest.py`
- `/.github/workflows/ci-cd-main.yml`

---

**維護說明**: 每次遇到新問題，更新此文檔的案例分析章節

**最後更新**: 2025-08-19