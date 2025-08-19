# 測試快速參考卡

**版本**: 1.0.0 | **日期**: 2025-08-19 | **用途**: 快速查詢測試規則和命令

---

## ✅ 必做事項清單

### 🔥 最高優先級
```bash
□ 使用 get_llm_client() 調用所有 LLM（絕不直接用 OpenAI SDK）
□ 確保所有測試 JD/Resume ≥ 200 字元
□ 非同步操作使用 AsyncMock，同步操作使用 Mock
□ 在 fixture 中管理環境變數，測試後恢復
□ 檢測 CI 環境並調整延遲時間
```

### 📝 開發時必做
```bash
□ 每個測試方法加 Test ID 註釋（如：API-GAP-001-UT）
□ 使用 fixture 管理測試資料，不要硬編碼
□ Patch 在 import 位置，不是定義位置
□ 單元測試完全 Mock 外部依賴
□ 條件式初始化資源（if not self._pool: init()）
```

### 🔍 提交前必做
```bash
□ 執行 ruff check src/ test/ --line-length=120
□ 執行 python test/scripts/pre_commit_check_advanced.py
□ 確認所有 217 個測試通過
□ 檢查無直接 OpenAI SDK import
□ 驗證測試可獨立執行（不依賴順序）
```

---

## ❌ 禁止事項清單

### 🚫 絕對禁止
```python
# ❌ 直接使用 OpenAI SDK
from openai import AsyncAzureOpenAI
from src.services.openai_client import get_azure_openai_client

# ❌ 修改 sys.path
sys.path.insert(0, '/some/path')

# ❌ 混用 Mock 類型
async_func = Mock()  # 應該用 AsyncMock

# ❌ 無條件初始化
await self.initialize()  # 應該先檢查

# ❌ 硬編碼測試資料
jd = "Python Developer"  # 太短，< 200 字元
```

### ⚠️ 應該避免
```python
# 不要忽略測試隔離
# 不要假設測試執行順序
# 不要在測試外修改全局狀態
# 不要過度 Mock（有些測試需要真實行為）
# 不要忽略 CI/本地環境差異
```

---

## 🛠️ 常用測試命令

### 基本測試執行
```bash
# Ruff 程式碼檢查
ruff check src/ test/ --line-length=120
ruff check src/ test/ --fix  # 自動修復

# 單元測試
pytest test/unit/ -v
pytest test/unit/services/test_gap_analysis_v2.py -v

# 整合測試
pytest test/integration/ -v
pytest test/integration/test_gap_analysis_v2_integration_complete.py -v

# 效能測試（需要真實 API keys）
pytest test/performance/ -v -s
```

### 模組專用測試
```bash
# Health & Keyword
./test/scripts/run_health_keyword_unit_integration.sh

# Index Calculation
./test/scripts/run_index_calculation_unit_integration.sh

# Gap Analysis
./test/scripts/run_index_cal_gap_analysis_unit_integration.sh

# Course Batch Query
pytest test/unit/test_course_batch_unit.py test/integration/test_course_batch_integration.py -v

# Resume Tailoring
pytest test/unit/services/test_resume_tailoring_metrics.py test/integration/test_resume_tailoring_api.py -v
```

### 進階測試
```bash
# 完整 pre-commit 檢查（217 個測試）
python test/scripts/pre_commit_check_advanced.py

# CI 環境模擬
CI=true GITHUB_ACTIONS=true pytest

# 單一測試除錯
pytest path/to/test.py::TestClass::test_method -xvs

# 顯示測試覆蓋率
pytest --cov=src --cov-report=html

# 平行執行測試
pytest -n auto
```

---

## 🎯 Mock 快速模式

### AsyncMock 模式
```python
# ✅ 正確的 Async Context Manager
class AsyncContextManager:
    def __init__(self, value):
        self.value = value
    async def __aenter__(self):
        return self.value
    async def __aexit__(self, *args):
        return None

mock_pool.get_client = lambda: AsyncContextManager(mock_client)
```

### LLM Client Mock
```python
# ✅ 標準 LLM Mock
@pytest.fixture
def mock_llm():
    with patch('src.services.llm_factory.get_llm_client') as mock:
        client = Mock()
        client.chat.completions.create = AsyncMock(
            return_value=Mock(
                choices=[Mock(message=Mock(content='{"result": "ok"}'))]
            )
        )
        mock.return_value = client
        yield mock
```

### Patch 位置
```python
# 檔案: src/services/gap_analysis_v2.py
from src.services.llm_factory import get_llm_client

# 測試檔案: 
@patch('src.services.gap_analysis_v2.get_llm_client')  # ✅ Patch import 位置
```

---

## 📊 測試資料快速參考

### 有效資料範例
```python
# 英文 JD (450+ 字元) ✅
VALID_EN_JD = """
We are looking for a Senior Python Developer with 5+ years of experience 
in building scalable web applications using FastAPI and Django frameworks. 
Strong knowledge of Docker, Kubernetes, and AWS cloud services is required. 
The ideal candidate must have excellent problem-solving skills and ability 
to work independently in a fast-paced agile environment. Experience with 
microservices architecture, RESTful APIs, GraphQL, PostgreSQL, MongoDB, 
Redis, and distributed systems is highly valued.
""".strip()

# 繁中 JD (350+ 字元) ✅  
VALID_ZH_JD = """
我們正在尋找一位資深的Python開發工程師，需要具備FastAPI框架經驗，
熟悉Docker容器技術和Azure雲端服務。理想的候選人應該對微服務架構有深入理解，
並且有RESTful API開發經驗。具備CI/CD流程和測試驅動開發經驗者優先。
同時需要熟悉分散式系統設計，具備系統架構規劃能力和團隊合作精神。
需要至少五年以上的後端開發經驗。
""".strip()
```

### 邊界測試
```python
BOUNDARY_199 = "x" * 199  # ❌ 失敗
BOUNDARY_200 = "x" * 200  # ✅ 通過
BOUNDARY_201 = "x" * 201  # ✅ 通過
```

---

## 🔍 問題診斷速查

| 症狀 | 可能原因 | 快速修復 |
|------|---------|---------|
| `deployment does not exist` | 直接用 OpenAI SDK | 改用 `get_llm_client()` |
| `Database configuration not found` | CI 無配置檔案 | 加條件判斷 `if not self._pool` |
| `coroutine raised StopIteration` | 用錯 Mock 類型 | 改用 AsyncMock |
| 本地過 CI 掛 | 環境差異 | 檢查配置檔案依賴 |
| JSON 解析失敗 | Token 限制截斷 | 增加 max_tokens |

---

## 📈 測試統計基準

### 正常執行時間
- **單元測試**: 10-15 秒
- **整合測試**: 15-20 秒  
- **全部測試**: 30-40 秒
- **單一測試**: < 0.5 秒

### 測試數量（2025-08-19）
- **總測試數**: 217
- **單元測試**: ~110
- **整合測試**: ~107
- **模組分布**: 9 個主要模組

---

## 🚀 緊急修復流程

```bash
# 1. 快速定位問題
pytest --lf  # 只跑上次失敗的測試

# 2. 詳細除錯
pytest test/failing_test.py -xvs --pdb

# 3. 檢查 Mock
grep -r "get_azure_openai_client\|AsyncAzureOpenAI" src/ test/

# 4. 驗證修復
python test/scripts/pre_commit_check_advanced.py

# 5. CI 環境驗證
CI=true pytest test/failing_test.py
```

---

## 📝 Test ID 格式

```python
# API-{模組}-{編號}-{類型}
API-GAP-001-UT     # Gap Analysis 單元測試
API-GAP-001-IT     # Gap Analysis 整合測試  
API-GAP-001-PT     # Gap Analysis 效能測試
API-TLR-001-UT     # Resume Tailoring 單元測試
API-ERR-001-UT     # Error Handler 單元測試
```

---

**快速連結**:
- [完整指南](./COMPREHENSIVE_TEST_DESIGN_GUIDE.md)
- [疑難排解](./TEST_TROUBLESHOOTING_GUIDE.md)
- [Mock 策略](../issues/service-module-refactor/MOCK_STRATEGY_GUIDE.md)
- [測試資料](../issues/service-module-refactor/TEST_DATA_REQUIREMENTS.md)