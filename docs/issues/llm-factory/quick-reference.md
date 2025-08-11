# LLM Factory 快速參考指南

## 🚀 快速開始

### LLM 調用
```python
from src.services.llm_factory import get_llm_client

# 使用 API 名稱（推薦）
client = get_llm_client(api_name="gap_analysis")
```

### Embedding 調用
```python
from src.services.llm_factory import get_embedding_client

# 預設使用 embedding-3-large
client = get_embedding_client()

# 課程搜尋使用 embedding-3-small
client = get_embedding_client(api_name="course_search")
```

## 📋 模型對照表

| 用途 | 環境變數 | 預設值 | Azure 部署 |
|------|----------|--------|------------|
| 關鍵字提取 | LLM_MODEL_KEYWORDS | gpt-4.1-mini | gpt-4-1-mini-japaneast |
| 差距分析 | LLM_MODEL_GAP_ANALYSIS | gpt-4.1 | gpt-4.1-japan |
| 履歷格式化 | LLM_MODEL_RESUME_FORMAT | gpt-4.1 | gpt-4.1-japan |
| 履歷客製化 | LLM_MODEL_RESUME_TAILOR | gpt-4.1 | gpt-4.1-japan |
| 標準 Embedding | LLM_MODEL_EMBEDDING_DEFAULT | embedding-3-large | embedding-3-large-japan |
| 課程 Embedding | LLM_MODEL_COURSE_EMBEDDING | embedding-3-small | embedding-3-small-japan |

## ⚠️ 重要規則

### ✅ 正確做法
```python
# LLM
from src.services.llm_factory import get_llm_client
client = get_llm_client(api_name="gap_analysis")

# Embedding
from src.services.llm_factory import get_embedding_client
client = get_embedding_client()
```

### ❌ 錯誤做法
```python
# 不要直接使用 OpenAI SDK
from openai import AsyncAzureOpenAI
client = AsyncAzureOpenAI(...)  # ❌

# 不要使用舊的 embedding 函數
from src.services.embedding_client import get_azure_embedding_client
client = get_azure_embedding_client()  # ❌ (deprecated)
```

## 🔄 遷移指南

### 如果你的程式碼使用...

1. **`gpt4o-2`** → 改為 `gpt-4.1`
2. **`gpt41-mini`** → 改為 `gpt-4.1-mini`
3. **`get_azure_embedding_client()`** → 改為 `get_embedding_client()`
4. **`get_course_embedding_client()`** → 改為 `get_embedding_client(api_name="course_search")`

## 📝 環境變數範例

```bash
# .env 檔案
LLM_MODEL_KEYWORDS=gpt-4.1-mini
LLM_MODEL_GAP_ANALYSIS=gpt-4.1
LLM_MODEL_RESUME_FORMAT=gpt-4.1
LLM_MODEL_RESUME_TAILOR=gpt-4.1
LLM_MODEL_EMBEDDING_DEFAULT=embedding-3-large
LLM_MODEL_COURSE_EMBEDDING=embedding-3-small
```

## 🎯 API 使用範例

### 關鍵字提取
```python
client = get_llm_client(api_name="keyword_extraction")
# 自動使用 gpt-4.1-mini (快速)
```

### 差距分析
```python
client = get_llm_client(api_name="gap_analysis")
# 自動使用 gpt-4.1 (高品質)
```

### 履歷向量化
```python
client = get_embedding_client()
# 自動使用 embedding-3-large
```

### 課程搜尋
```python
client = get_embedding_client(api_name="course_search")
# 自動使用 embedding-3-small (成本優化)
```

## 📊 決策樹

```
需要 AI 服務？
├── 文字生成/分析？
│   └── 使用 get_llm_client()
│       ├── 需要快速回應？ → api_name="keyword_extraction"
│       └── 需要高品質？ → api_name="gap_analysis"
└── 向量化/相似度？
    └── 使用 get_embedding_client()
        ├── 一般用途？ → 不帶參數
        └── 課程搜尋？ → api_name="course_search"
```

## 🆘 常見問題

**Q: 出現 "deployment does not exist" 錯誤？**
A: 檢查是否使用 LLM Factory，不要直接調用 OpenAI SDK

**Q: 舊程式碼還能運作嗎？**
A: 可以，但建議盡快遷移到新的調用方式

**Q: 如何選擇適合的模型？**
A: 根據上方決策樹，或查看模型對照表

---
更新日期：2025-08-11