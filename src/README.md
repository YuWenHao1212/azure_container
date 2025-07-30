# FHS Architecture Development Structure

## 目錄結構說明

此專案遵循 FHS (Functional Hierarchy Structure) 架構原則，將程式碼按功能層級組織。

### 目錄說明

```
src/
├── api/              # API 端點定義層
│   └── v1/          # API 版本 1
│       ├── __init__.py           # 路由聚合
│       ├── keyword_extraction.py # 關鍵字提取端點
│       ├── resume_format.py      # 履歷格式化端點
│       ├── similarity.py         # 相似度計算端點
│       ├── gap_analysis.py       # 差距分析端點
│       ├── resume_tailoring.py   # 履歷客製化端點
│       └── course_matching.py    # 課程匹配端點
├── core/             # 核心配置與共用元件
│   ├── __init__.py
│   ├── config.py               # 應用程式配置
│   ├── dependencies.py         # 依賴注入
│   ├── exceptions.py          # 自定義例外
│   └── security.py            # 安全相關功能
├── models/           # 資料模型定義
│   ├── __init__.py
│   ├── response.py            # 統一回應模型
│   ├── keyword_extraction.py  # 關鍵字提取模型
│   ├── resume.py             # 履歷相關模型
│   └── job.py                # 職位相關模型
├── services/         # 業務邏輯層
│   ├── __init__.py
│   ├── base.py                    # 基礎服務類別
│   ├── keyword_extraction.py      # 關鍵字提取服務
│   ├── openai_client.py          # OpenAI 客戶端服務
│   ├── standardization.py        # 標準化服務
│   └── llm_parser.py             # LLM 回應解析服務
├── repositories/     # 資料存取層 (未來擴充用)
│   ├── __init__.py
│   └── base.py               # 基礎儲存庫類別
├── utils/            # 工具函數
│   ├── __init__.py
│   ├── validators.py         # 驗證工具
│   ├── formatters.py        # 格式化工具
│   └── constants.py         # 常數定義
└── main.py          # FastAPI 應用程式進入點
```

### 開發指南

1. **新增端點**：在 `api/v1/` 建立新的端點模組
2. **新增服務**：在 `services/` 建立新的服務類別，繼承自 `BaseService`
3. **新增模型**：在 `models/` 定義 Pydantic 模型，確保符合 Bubble.io 相容性要求
4. **測試**：在 `tests/` 對應目錄建立測試案例

### 重要原則

1. **統一回應格式**：所有 API 都必須使用 `UnifiedResponse` 模型
2. **無 Optional 類型**：為確保 Bubble.io 相容性，避免使用 `Optional[Type]`
3. **錯誤處理**：使用統一的錯誤處理機制，返回相同的 JSON Schema
4. **服務分離**：業務邏輯放在 services 層，API 層只處理 HTTP 相關邏輯

### 開發順序

根據 CLAUDE.md 的規劃，開發順序如下：
1. keyword_extraction (關鍵字提取) - 進行中
2. resume_format (履歷格式化)
3. similarity (相似度計算)
4. gap_analysis (差距分析)
5. resume_tailoring (履歷客製化)
6. course_matching (課程匹配)
