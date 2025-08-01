# Azure Container API

> AI 履歷優化平台 - 針對 Azure Container Apps 最佳化

## 專案簡介

本專案是從生產環境容器鏡像 `airesumeadvisor-api:20250730-100726-3530cfd` 中還原的完整 AI 履歷優化平台，包含以下核心功能：

- 🔍 **關鍵字提取** - 從職缺描述提取技能關鍵字
- 📊 **匹配指數計算** - 評估履歷與職缺的匹配度  
- 📈 **差距分析** - 找出技能缺口並提供改進建議
- 📄 **履歷格式化** - OCR 文字轉結構化 HTML
- ✍️ **履歷客製化** - AI 智能改寫履歷內容
- 🎓 **課程推薦** - 向量搜尋相關學習資源

## 快速開始

### 本地開發

```bash
# 1. 克隆專案
git clone <repository-url>
cd azure_container

# 2. 設定環境變數
# 方法一：使用簡化配置（推薦）
cp .env.simple .env
# 只需要設定 AZURE_OPENAI_API_KEY 即可

# 方法二：完整配置
cp .env.example .env
# 編輯 .env 檔案，填入所有配置

# 3. 安裝依賴
pip install -r requirements.txt

# 4. 啟動應用程式
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

訪問 http://localhost:8000/docs 查看 API 文檔

### Docker 部署

```bash
# 1. 建立 Docker 鏡像
docker build -t azure-container-api .

# 2. 運行容器
docker run -p 8000:8000 --env-file .env azure-container-api
```

### Azure Container Apps 部署

```bash
# 1. 確保已登入 Azure
az login

# 2. 執行部署腳本
./deploy-container-app.sh
```

## API 端點

### 核心功能
- `POST /api/v1/extract-jd-keywords` - 關鍵字提取
- `POST /api/v1/index-calculation` - 匹配指數計算
- `POST /api/v1/index-cal-and-gap-analysis` - 指數計算與差距分析
- `POST /api/v1/format-resume` - 履歷格式化
- `POST /api/v1/tailor-resume` - 履歷客製化
- `POST /api/v1/courses/search` - 課程搜尋

### 系統端點
- `GET /health` - 健康檢查
- `GET /docs` - API 文檔
- `GET /` - 服務資訊

### 認證方式

支援兩種認證方式：
- **HTTP Header** (推薦): `X-API-Key: your-api-key`
- **Query Parameter**: `?code=your-api-key`

## 技術規格

- **框架**: FastAPI 0.104.1
- **Python**: 3.11
- **架構**: FHS (Functional Hierarchy Structure)
- **AI 模型**: GPT-4.1 (主要) + GPT-4.1 mini (關鍵字提取)
- **部署**: Azure Container Apps
- **監控**: Application Insights + 輕量監控

## 效能表現

相比 Azure Functions 架構：
- **回應時間改善**: 53% (6.0s → 2.8s)
- **架構開銷消除**: 100% (3.2s → 0s)
- **冷啟動時間改善**: 80% (2-3s → 0.1-0.5s)
- **並發能力提升**: 40-100x (< 0.5 QPS → 20-50 QPS)

## 開發指南

### 程式碼風格
```bash
# 檢查程式碼風格
ruff check src/ --fix
```

### 測試執行
```bash
# 單元測試
pytest tests/unit/ -v

# 整合測試  
pytest tests/integration/ -v
```

### 環境配置

關鍵環境變數：

**簡化配置 (Japan East 統一部署)**：
- `AZURE_OPENAI_API_KEY` - 共用的 API 金鑰（所有模型都使用此金鑰）
- `CONTAINER_APP_API_KEY` - Container Apps 認證金鑰

所有 Azure OpenAI 服務（GPT-4.1、GPT-4.1 mini、Embeddings）都部署在 Japan East，使用同一個 API Key。詳見 `.env.example` 或使用 `.env.simple` 快速開始。

## 生產環境

### 當前部署
- **生產環境**: https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io
- **開發環境**: https://airesumeadvisor-api-dev.calmisland-ea7fe91e.japaneast.azurecontainerapps.io

### 資源配置
- **CPU**: 1 核心
- **記憶體**: 2GB
- **儲存**: 4GB 暫存空間
- **自動擴展**: 1-10 實例

## 部署與 CI/CD

### GitHub Actions CI/CD
本專案使用 GitHub Actions 實現自動化部署：

- **自動部署**: 推送到 `main` 分支自動觸發測試和部署
- **測試驗證**: 執行 113 個測試確保程式碼品質
- **零停機部署**: 使用 Azure Container Apps 的藍綠部署
- **回滾機制**: 支援快速回滾到任何歷史版本

詳細設定請參考 [DEPLOYMENT.md](./DEPLOYMENT.md)

### 手動部署
```bash
# 建置並推送到 Azure Container Registry
docker build -t airesumeadvisorregistry.azurecr.io/airesumeadvisor-api:latest .
docker push airesumeadvisorregistry.azurecr.io/airesumeadvisor-api:latest

# 使用部署腳本
./deploy-container-app.sh
```

## 監控與除錯

### 健康檢查
- `/health` - 基本健康狀態
- `/debug/monitoring` - 監控狀態詳情

### 開發除錯端點 (非生產環境)
- `/api/v1/monitoring/stats` - 監控統計
- `/api/v1/debug/storage-info` - 錯誤儲存資訊
- `/api/v1/debug/errors` - 最近錯誤記錄

## 支援

詳細的開發指南和協作規範請參考 [CLAUDE.md](./CLAUDE.md)

## 授權

本專案為內部開發專案，僅供 AIResumeAdvisor 團隊使用。