# LLM Factory 重構：移除 gpt4o-2 Legacy 命名並整合 Embedding 服務

**日期**: 2025-08-11  
**作者**: Claude Code + WenHao  
**版本**: v1.0.0  
**PR**: [#4](https://github.com/YuWenHao1212/azure_container/pull/4)

## 📋 目錄
1. [重構背景](#重構背景)
2. [重構目標](#重構目標)
3. [技術分析](#技術分析)
4. [實作方案](#實作方案)
5. [變更詳情](#變更詳情)
6. [測試驗證](#測試驗證)
7. [使用指南](#使用指南)
8. [遷移指南](#遷移指南)
9. [影響評估](#影響評估)
10. [總結](#總結)

## 重構背景

### 問題發現
在檢視 Resume Tailoring v2.1.0 實作時，發現系統中存在兩個問題：

1. **Legacy 命名混淆**
   - 程式碼中混用 `gpt4o-2` 和 `gpt-4.1` 兩種命名
   - `gpt4o-2` 是舊的命名慣例，實際會映射到 `gpt-4.1-japan`
   - 造成開發者困惑，不清楚應該使用哪個名稱

2. **服務管理分散**
   - LLM 服務透過 `llm_factory.py` 管理
   - Embedding 服務透過 `embedding_client.py` 獨立管理
   - 缺乏統一的 AI 服務管理介面

### 現況分析
```
原本架構：
┌─────────────┐     ┌──────────────────┐
│   API 層    │────▶│  LLM Factory     │────▶ Azure OpenAI (LLM)
└─────────────┘     └──────────────────┘
       │
       │            ┌──────────────────┐
       └───────────▶│ Embedding Client │────▶ Azure OpenAI (Embedding)
                    └──────────────────┘
```

問題：
- 兩套獨立的管理機制
- 重複的配置邏輯
- 不一致的錯誤處理

## 重構目標

### 主要目標
1. **消除 Legacy 命名**：完全移除 `gpt4o-2`，統一使用 `gpt-4.1`
2. **統一服務管理**：將 Embedding 服務整合到 LLM Factory
3. **簡化配置**：集中管理所有 AI 模型配置
4. **保持相容性**：確保現有 API 繼續正常運作

### 預期效果
```
新架構：
┌─────────────┐     ┌──────────────────┐
│   API 層    │────▶│   LLM Factory    │────▶ Azure OpenAI (LLM)
└─────────────┘     │  (統一管理中心)   │
                    │                  │────▶ Azure OpenAI (Embedding)
                    └──────────────────┘
```

## 技術分析

### 影響範圍評估
透過程式碼搜尋和分析，識別出需要修改的檔案：

| 類別 | 檔案數量 | 主要檔案 |
|------|---------|----------|
| 核心服務 | 3 | llm_factory.py, config.py, embedding_client.py |
| 環境配置 | 2 | .env.example, deploy-container-app.sh |
| CI/CD | 1 | .github/workflows/ci-cd-main.yml |
| 測試腳本 | 3 | run_index_cal_gap_analysis_*.sh |
| 文檔 | 1 | CLAUDE.md |

### 模型映射關係
| 邏輯名稱 | Azure 部署名稱 | 用途 |
|----------|---------------|------|
| gpt-4.1 | gpt-4.1-japan | 主要 LLM（高品質） |
| gpt-4.1-mini | gpt-4-1-mini-japaneast | 輔助 LLM（高效能） |
| embedding-3-large | embedding-3-large-japan | 標準 Embedding |
| embedding-3-small | embedding-3-small-japan | 課程搜尋 Embedding |

## 實作方案

### 階段一：LLM Factory 擴充
**檔案**: `src/services/llm_factory.py`

#### 1. 新增類型定義
```python
# 新增 Embedding 模型類型
EmbeddingModel = Literal["embedding-3-large", "embedding-3-small"]

# 更新 LLM 模型類型（移除 gpt4o-2）
LLMModel = Literal["gpt-4.1", "gpt-4.1-mini"]
```

#### 2. 新增 Embedding 部署映射
```python
EMBEDDING_DEPLOYMENT_MAP = {
    "embedding-3-large": "embedding-3-large-japan",
    "embedding-3-small": "embedding-3-small-japan",
}
```

#### 3. 實作 get_embedding_client 函數
```python
def get_embedding_client(
    model: EmbeddingModel | None = None,
    api_name: str | None = None
):
    """
    統一的 Embedding 客戶端獲取函數
    
    優先順序：
    1. 直接指定的 model 參數
    2. 基於 api_name 的環境變數配置
    3. 預設使用 embedding-3-large
    """
    # 實作邏輯...
```

### 階段二：Config 更新
**檔案**: `src/core/config.py`

新增 Embedding 配置欄位：
```python
class Settings(BaseSettings):
    # 新增 Embedding 模型配置
    llm_model_embedding_default: str = Field(
        default="embedding-3-large",
        description="預設 Embedding 模型"
    )
    
    llm_model_course_embedding: str = Field(
        default="embedding-3-small",
        description="課程搜尋專用 Embedding 模型"
    )
    
    # 更新預設 LLM 模型
    llm_model_default: str = Field(
        default="gpt-4.1",  # 從 gpt4o-2 改為 gpt-4.1
        description="預設 LLM 模型"
    )
```

### 階段三：Embedding Client 簡化
**檔案**: `src/services/embedding_client.py`

保留向後相容，但標記為 deprecated：
```python
def get_azure_embedding_client():
    """
    DEPRECATED: 請使用 llm_factory.get_embedding_client()
    此函數保留以維持向後相容性
    """
    from src.services.llm_factory import get_embedding_client
    return get_embedding_client(model="embedding-3-large")
```

### 階段四：環境配置更新
更新所有配置檔案中的模型名稱：
- `.env.example`
- `.github/workflows/ci-cd-main.yml`
- `deploy-container-app.sh`
- 測試腳本

## 變更詳情

### 程式碼變更統計
```
11 files changed, 152 insertions(+), 76 deletions(-)
```

### 主要檔案變更
1. **llm_factory.py** (+92 行)
   - 新增 EmbeddingModel 類型
   - 新增 get_embedding_client 函數
   - 新增 EMBEDDING_DEPLOYMENT_MAP
   - 更新所有預設值

2. **config.py** (+24 行)
   - 新增 embedding 配置欄位
   - 更新預設模型名稱

3. **embedding_client.py** (-46 行)
   - 簡化為使用 LLM Factory
   - 保留 deprecated 函數

## 測試驗證

### 測試結果
```
╔════════════════════════════════════════════════════╗
║              Pre-commit 完整測試報告                 ║
╚════════════════════════════════════════════════════╝

測試分類                    通過   失敗   總計    狀態
─────────────────────────────────────────────────────
🔍 Ruff 檢查                 ✅     -     -      ✅
🏗️ 服務模組測試              47     0     47     ✅
🩺 Health & Keyword         19     0     19     ✅
🧮 Index Calculation        24     0     24     ✅
📈 Gap Analysis             47     0     47     ✅
─────────────────────────────────────────────────────
🎯 總計                     137    0    137     ✅
```

### Azure 環境驗證
```bash
# 已更新的環境變數
LLM_MODEL_GAP_ANALYSIS=gpt-4.1      ✅
LLM_MODEL_RESUME_FORMAT=gpt-4.1     ✅
LLM_MODEL_RESUME_TAILOR=gpt-4.1     ✅
LLM_MODEL_KEYWORDS=gpt-4.1-mini     ✅
```

## 使用指南

### LLM 服務調用
```python
from src.services.llm_factory import get_llm_client

# 方式一：使用 API 名稱（推薦）
client = get_llm_client(api_name="gap_analysis")

# 方式二：直接指定模型
client = get_llm_client(model="gpt-4.1")

# 方式三：使用預設模型
client = get_llm_client()
```

### Embedding 服務調用
```python
from src.services.llm_factory import get_embedding_client

# 方式一：使用預設 embedding-3-large
client = get_embedding_client()

# 方式二：用於課程搜尋（使用 embedding-3-small）
client = get_embedding_client(api_name="course_search")

# 方式三：直接指定模型
client = get_embedding_client(model="embedding-3-small")
```

### 環境變數配置
```bash
# LLM 模型配置
LLM_MODEL_KEYWORDS=gpt-4.1-mini      # 關鍵字提取
LLM_MODEL_GAP_ANALYSIS=gpt-4.1       # 差距分析
LLM_MODEL_RESUME_FORMAT=gpt-4.1      # 履歷格式化
LLM_MODEL_RESUME_TAILOR=gpt-4.1      # 履歷客製化

# Embedding 模型配置（新增）
LLM_MODEL_EMBEDDING_DEFAULT=embedding-3-large  # 預設 embedding
LLM_MODEL_COURSE_EMBEDDING=embedding-3-small   # 課程搜尋
```

## 遷移指南

### 對現有程式碼的影響

#### 1. LLM 調用（無需修改）
現有的 LLM 調用程式碼**不需要修改**，因為：
- LLM Factory 介面保持不變
- 模型映射自動處理

#### 2. Embedding 調用（建議更新）
```python
# 舊方式（仍可運作，但已 deprecated）
from src.services.embedding_client import get_azure_embedding_client
client = get_azure_embedding_client()

# 新方式（推薦）
from src.services.llm_factory import get_embedding_client
client = get_embedding_client()
```

### 部署注意事項

1. **環境變數更新**
   - 執行提供的 `update_azure_env_vars.sh` 腳本
   - 或手動在 Azure Portal 更新環境變數

2. **CI/CD 配置**
   - GitHub Actions 配置已自動更新
   - 無需手動修改 Secrets（只包含 API keys）

3. **測試驗證**
   - 部署前執行完整測試套件
   - 確認所有 137 個測試通過

## 影響評估

### 正面影響
1. **程式碼一致性**：消除命名混淆，提升可維護性
2. **架構簡化**：統一的 AI 服務管理介面
3. **擴展性提升**：更容易添加新的 AI 模型
4. **錯誤減少**：集中的錯誤處理和配置驗證

### 風險評估
| 風險項目 | 可能性 | 影響 | 緩解措施 |
|---------|--------|------|----------|
| API 相容性問題 | 低 | 高 | 保留 deprecated 函數 |
| 部署失敗 | 低 | 中 | 完整測試 + 回滾計畫 |
| 效能影響 | 極低 | 低 | 無額外開銷 |

## 總結

### 成果摘要
- ✅ 成功移除所有 `gpt4o-2` legacy 命名
- ✅ 統一 AI 服務管理架構
- ✅ 保持 100% 向後相容性
- ✅ 所有測試通過（137/137）
- ✅ Azure 環境已更新並驗證

### 後續建議
1. **短期**（1-2 週）
   - 監控生產環境效能指標
   - 收集開發團隊反饋
   - 更新內部開發文檔

2. **中期**（1-3 月）
   - 逐步移除 deprecated 函數的使用
   - 評估新模型整合需求
   - 優化模型選擇策略

3. **長期**（3-6 月）
   - 完全移除 deprecated 函數
   - 實作動態模型載入機制
   - 整合更多 AI 服務（如 Vision、Speech）

### 相關資源
- [Pull Request #4](https://github.com/YuWenHao1212/azure_container/pull/4)
- [LLM Factory 原始碼](../../src/services/llm_factory.py)
- [測試報告](../../test/reports/)
- [Azure Container Apps Dashboard](https://portal.azure.com/)

---

**文檔版本歷史**
- v1.0.0 (2025-08-11): 初始版本，記錄完整重構過程

**聯絡資訊**
- 技術負責人：WenHao
- AI 助理：Claude Code
- 專案儲存庫：[azure_container](https://github.com/YuWenHao1212/azure_container)