# LLM 動態切換功能

## 概述

LLM 動態切換功能允許系統根據不同的需求和環境，靈活選擇使用不同的語言模型（如 GPT-4o-2 或 GPT-4.1 mini）。這個功能支援多種選擇策略，讓開發者和營運團隊能夠優化成本和效能。

## 功能特點

### 1. 多層級選擇優先級
- **請求參數**（最高優先級）：未來可在 API 請求中指定模型
- **HTTP Header**：透過 `X-LLM-Model` header 選擇模型
- **環境變數**：為每個 API 配置預設模型
- **系統預設**：當無特定配置時使用的模型

### 2. 支援的模型
- **GPT-4o-2**：高準確度，適合複雜任務
- **GPT-4.1 mini**：快速且經濟，成本降低 98%+

### 3. API 級別配置
每個 API 可獨立配置使用的模型：
- 關鍵字提取：`LLM_MODEL_KEYWORDS`
- 差距分析：`LLM_MODEL_GAP_ANALYSIS`
- 履歷格式化：`LLM_MODEL_RESUME_FORMAT`
- 履歷優化：`LLM_MODEL_RESUME_TAILOR`

## 使用方式

### 環境變數配置

```bash
# 設定預設模型
LLM_MODEL_DEFAULT=gpt4o-2

# 為特定 API 設定模型
LLM_MODEL_KEYWORDS=gpt41-mini      # 關鍵字提取使用 GPT-4.1 mini
LLM_MODEL_GAP_ANALYSIS=gpt4o-2     # 差距分析使用 GPT-4o-2

# Feature flags
ENABLE_LLM_MODEL_OVERRIDE=true     # 允許請求覆蓋
ENABLE_LLM_MODEL_HEADER=true       # 允許 Header 覆蓋
```

### HTTP Header 使用

```bash
# 使用 GPT-4.1 mini
curl -X POST https://api.example.com/api/v1/extract-jd-keywords \
  -H "Content-Type: application/json" \
  -H "X-LLM-Model: gpt41-mini" \
  -d '{"job_description": "..."}'
```

### 程式碼整合

```python
from src.services.llm_factory import get_llm_client_smart

# 智能選擇 LLM 客戶端
client = get_llm_client_smart(
    api_name="keywords",
    request_model=None,  # 可從請求中取得
    headers=request.headers  # HTTP headers
)
```

## 成本效益分析

### 模型成本比較（每 1K tokens）
| 模型 | 輸入成本 | 輸出成本 |
|------|----------|----------|
| GPT-4o-2 | $0.01 | $0.03 |
| GPT-4.1 mini | $0.00015 | $0.0006 |

### 實際案例
- 關鍵字提取（平均 1500 輸入 + 500 輸出 tokens）
  - GPT-4o-2：$0.03 per request
  - GPT-4.1 mini：$0.0005 per request
  - **節省：98.2%**

## 監控與分析

系統會自動記錄每個請求使用的模型：

```kusto
// Application Insights 查詢
customEvents
| where name == "LLMModelSelected"
| summarize count() by tostring(customDimensions.model), tostring(customDimensions.api_name)
| render piechart
```

## 最佳實踐

1. **Staging 環境測試**
   - 先在 staging 環境測試新模型
   - 監控準確度和效能指標
   - 確認符合業務需求後再部署到生產環境

2. **漸進式遷移**
   - 從低風險 API 開始（如關鍵字提取）
   - 逐步擴展到其他 API
   - 保持監控和回滾能力

3. **成本優化策略**
   - 簡單任務使用 GPT-4.1 mini
   - 複雜或高價值任務使用 GPT-4o-2
   - 定期檢視使用報告調整配置

## 故障排除

### 常見問題

1. **模型選擇未生效**
   - 檢查環境變數是否正確設置
   - 確認 feature flags 已啟用
   - 查看日誌確認實際使用的模型

2. **GPT-4.1 mini 回退到 GPT-4o-2**
   - 檢查 API Key 是否配置
   - 確認端點 URL 正確
   - 查看錯誤日誌

### 日誌範例
```
INFO: Using model from HTTP header: gpt41-mini
INFO: Using LLM model: gpt41-mini from japaneast
```

## 生產環境使用統計

### 模型使用分布 (2025-08)
- **關鍵字提取 API**: 
  - 使用模型: GPT-4.1 mini
  - 請求量: 100%
  - 平均回應時間: 2.14 秒
  - 成本節省: 98.2% (相比 GPT-4o-2)

### 測試覆蓋
- **LLM Factory 模組**: 8 個單元測試
- **模型切換邏輯**: 100% 覆蓋
- **錯誤處理**: 完整測試

## 未來擴展

1. **自動模型選擇**
   - 根據請求複雜度自動選擇
   - 基於歷史數據的智能推薦

2. **更多模型支援**
   - Claude 3.5
   - 開源模型整合

3. **A/B 測試框架**
   - 自動分流測試
   - 效果追蹤和分析