# 🧪 測試設計核心規則

## 五大黃金測試規則（必須嚴格遵守）

### 1. LLM Factory 規則 ⚠️ **最重要**
```python
# ❌ 絕對禁止 - 直接使用 OpenAI SDK
from openai import AsyncAzureOpenAI
from src.services.openai_client import get_azure_openai_client

# ✅ 唯一正確方式 - 使用 LLM Factory
from src.services.llm_factory import get_llm_client
client = get_llm_client(api_name="gap_analysis")
```
**違規後果**: 500 錯誤 "deployment does not exist"

### 2. 測試資料長度規則
- 所有測試 JD 和 Resume **必須 ≥ 200 字元**
- 使用 fixtures 管理測試資料，不要硬編碼
- 違規會導致 HTTP 422 驗證錯誤

### 3. AsyncMock 規則
```python
# ✅ 正確 - 非同步用 AsyncMock
mock_service.process = AsyncMock(return_value=result)

# ❌ 錯誤 - 會導致 "coroutine raised StopIteration"
mock_service.process = Mock(return_value=result)
```

### 4. 環境隔離規則
- 單元測試**絕不**依賴外部資源（DB、檔案、網路）
- 資源初始化必須有條件判斷：`if not self._pool: await self.initialize()`
- CI 環境自動偵測：`os.environ.get('CI') == 'true'`

### 5. Mock 位置規則
```python
# Patch 在 import 位置，不是定義位置
# 如果 gap_analysis_v2.py 有：from src.services.llm_factory import get_llm_client
@patch('src.services.gap_analysis_v2.get_llm_client')  # ✅ 正確
```

## 測試相關文檔
- [綜合測試設計指南](../docs/development/COMPREHENSIVE_TEST_DESIGN_GUIDE.md)
- [測試快速參考卡](../docs/development/TEST_QUICK_REFERENCE.md)
- [測試疑難排解指南](../docs/development/TEST_TROUBLESHOOTING_GUIDE.md)

## 程式碼修改分級測試
- **Level 0**: Prompt 修改 - YAML 格式驗證
- **Level 1**: 程式碼風格 - Ruff 檢查
- **Level 2**: 功能修改 - 單元測試
- **Level 3**: API 修改 - 整合測試

## 測試執行指令
```bash
# 程式碼風格檢查
ruff check src/ --fix

# 單元測試
pytest tests/unit/ -v

# 整合測試  
pytest tests/integration/ -v
```