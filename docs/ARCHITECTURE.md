# 架構設計

## 概述

本專案採用 FHS (Functional Hierarchy Structure) 架構模式，將功能邏輯組織成清晰的層次結構。

**🔄 架構升級進行中**: 正在從 Azure Functions 遷移到 Azure Container Apps，部分 API 已完成遷移。

## 架構演進

### 舊架構 (Azure Functions) - 已淘汰
```
HTTP Request → Azure Functions Runtime → ASGI Adapter → FastAPI → Business Logic
```
**問題**: 每個請求有 3+ 秒的固定開銷，冷啟動嚴重

### 目標架構 (Container Apps) 🚀
```
HTTP Request → Container Apps Ingress → FastAPI (Native) → Business Logic  
```
**成果**: 
- ⚡ 40-91% 響應時間提升
- 🚀 平均響應時間從 6秒降至 2.8秒
- 🔥 無冷啟動問題
- 📈 並發處理能力提升 40-100倍

## 架構原則

### 1. 功能分層
```
src/
├── api/          # API 端點定義
├── services/     # 業務邏輯層
├── core/         # 核心功能（配置、錯誤處理）
├── models/       # 資料模型
├── prompts/      # LLM prompts
└── utils/        # 工具函數
```

### 2. 關注點分離
- **API 層**：處理 HTTP 請求/回應
- **Service 層**：實作業務邏輯
- **Core 層**：提供基礎設施支援

### 3. 相依性方向
- API → Services → Core/Utils
- 避免循環相依

## 技術選型

### 核心框架
- **FastAPI**：現代化、高效能的 Python web framework
- **Pydantic**：資料驗證與序列化
- **Azure Container Apps**：容器化部署平台（原生支援）
- **Docker**：容器化封裝

### AI/ML 整合
- **Azure OpenAI**：GPT-4 模型存取
- **Embedding API**：語義相似度計算
- **LangChain**：LLM 應用開發框架

### 資料存儲
- **PostgreSQL + pgvector**：課程資料庫與向量搜尋
- **Azure Blob Storage**：大型檔案儲存（未來擴展）

## 設計決策

### 1. Prompt 版本管理

#### 目錄結構
```yaml
prompts/
└── [task]/                    # 任務名稱（如 keyword_extraction）
    ├── v1.0.0.yaml           # 基礎版本
    ├── v1.0.0-zh-TW.yaml    # 語言特定版本
    ├── v1.1.0.yaml           # 更新版本
    └── v2.0.0.yaml           # 主要版本更新
```

#### Prompt Manager 架構
- **SimplePromptManager**：處理 prompt 載入與版本選擇
- **BilingualPromptManager**：處理多語言 prompt 選擇
- **版本解析**：自動選擇最新版本或指定版本
- **快取機制**：避免重複載入

#### 優勢
- 支援多版本並存，便於 A/B 測試
- 語言特定優化（如 `v1.1.0-zh-TW.yaml`）
- 版本回滾機制
- 統一的 YAML 格式配置

### 2. 錯誤處理策略
- 統一的錯誤回應格式（符合 Bubble.io 需求）
- 分層錯誤處理（中間件 → API → 服務層）
- 詳細的錯誤分類和追蹤
- 使用者友善的錯誤訊息

### 3. 效能優化
- 非同步處理（async/await 全面支援）
- 連線池管理（資料庫、HTTP 客戶端）
- 內建記憶體快取（關鍵字提取結果）
- 並行處理（2輪提取策略）

### 4. 監控架構
```
應用程式
├── 輕量級監控中間件（預設啟用）
│   ├── 請求/響應追蹤
│   ├── 效能指標收集
│   └── 錯誤統計
├── 錯誤捕獲中間件
│   └── 結構化錯誤記錄
└── Application Insights（可選）
    └── 完整遙測數據
```

## 安全考量

### API 安全
- **X-API-Key** 認證（Container Apps 原生支援）
- Pydantic 模型驗證（自動輸入清理）
- Rate limiting（Container Apps Ingress 層）
- CORS 配置（支援 Bubble.io 域名）

### 資料保護
- 敏感資料不記錄
- 環境變數管理 secrets
- HTTPS only

## 監控與可觀測性

### 三層監控策略
1. **輕量級監控**（預設）
   - 請求/響應時間追蹤
   - 錯誤率統計
   - API 使用模式分析

2. **Application Insights**（可選）
   - 完整請求追蹤
   - 自訂效能指標
   - 分散式追蹤

3. **健康檢查**
   - `/health` - 統一健康檢查端點
   - 自動健康探測（Container Apps）
   - 版本和配置資訊

### 監控端點（非生產環境）
- `/api/v1/monitoring/stats` - 即時統計
- `/api/v1/debug/errors` - 錯誤記錄
- `/debug/monitoring` - 監控狀態

## 擴展性設計

### 水平擴展（Container Apps）
- **自動擴展**: 2-10 個實例
- **觸發條件**: CPU/記憶體使用率
- **Stateless 設計**: 無狀態服務
- **負載均衡**: 內建支援

### 資源配置
- **CPU**: 1 vCPU（可調整）
- **記憶體**: 2GB RAM
- **暫存空間**: 4GB
- **並發處理**: 20-50 QPS

## 部署架構

```
GitHub (main branch)
    ↓ (push trigger)
Docker Build
    ↓ (build image)
Azure Container Registry
    ↓ (push image)
Azure Container Apps
    ↓ (pull & deploy)
Container Instances (2-10)
    ↓ (serve requests)
Bubble.io Frontend
```

### 部署環境
- **生產環境**: airesumeadvisor-api-production
- **開發環境**: airesumeadvisor-api-dev
- **區域**: Japan East（低延遲）

## 服務層架構

### 核心服務模組
```
services/
├── keyword_extraction_v2.py    # 關鍵字提取 V2（支援快取、並行）
├── unified_prompt_service.py   # 統一 Prompt 管理
├── course_search.py           # 向量相似度課程搜尋
├── index_calculation.py       # 匹配指數計算
├── gap_analysis.py           # 差距分析服務
├── resume_tailoring.py       # 履歷客製化
├── resume_format.py          # 履歷格式化
└── language_detection/       # 多語言檢測模組
    ├── detector.py          # 語言檢測主服務
    ├── validator.py         # 語言驗證
    └── bilingual_prompt_manager.py  # 雙語 Prompt 管理
```

### 服務特性
1. **依賴注入**: 使用單例模式管理服務實例
2. **錯誤處理**: 每個服務都有專屬的異常類型
3. **效能追蹤**: 內建 TokenTrackingMixin
4. **非同步支援**: 完整 async/await 實作

## 未來演進

### Phase 5 優化重點
1. **快取層**：Redis 整合
2. **批次處理**：大量請求優化
3. **監控增強**：自訂 dashboard
4. **多區域部署**：降低延遲

### 長期規劃
- GraphQL API 支援
- WebSocket 即時通訊
- 微服務拆分（如需要）