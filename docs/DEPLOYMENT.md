# 部署指南

## 概述

**當前狀態**: 正在進行 Container Apps 遷移
- **生產環境**: Container Apps (Japan East) - 部分運行中
  - ✅ 健康檢查端點 (`/health`)
  - ✅ 關鍵字提取 (`/api/v1/extract-jd-keywords`)
  - 🔄 其他 API 優化中
- **開發環境**: 尚未開始建置
- **部署分支**: `main` 分支（手動部署） <- git action cicd is ready

## 環境需求
S
### 本地開發
- Python 3.11.8
- Azure CLI
- Docker (Container Apps 開發)
- Git

### Azure 資源
- **Subscription ID**: `5396d388-8261-464e-8ee4-112770674fba`
- **Tenant**: `wenhaoairesumeadvisor.onmicrosoft.com`
- **Resource Group**: `airesumeadvisorfastapi`

#### 生產環境資源 (Container Apps) ✅
- **Container App**: `airesumeadvisor-api-production`
- **Container Environment**: `calmisland-ea7fe91e` 
- **Container Registry**: `airesumeadvisorregistry.azurecr.io`
- **區域**: Japan East
- **URL**: https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io

#### 開發環境資源
- **Container App**: `airesumeadvisor-api-dev`
- **URL**: https://airesumeadvisor-api-dev.calmisland-ea7fe91e.japaneast.azurecontainerapps.io

#### 共用資源
- **Application Insights**: `airesumeadvisorfastapi`
- **PostgreSQL Database**: 課程搜尋資料庫（pgvector）

## 自動部署流程

### CI/CD Pipeline (Container Apps)
```yaml
觸發條件：push to main
步驟：
1. 執行測試 (pytest)
2. 建置 Docker 映像
3. 推送到 Azure Container Registry
4. 更新 Container App（滾動部署）
5. 健康檢查驗證
6. 自動回滾（如失敗）
```

### GitHub Actions Workflow
```bash
# .github/workflows/deploy.yml.  <- 這是名字打錯? (ci-cd-main.yml)  
- 建置映像標籤：{date}-{commit_hash}
- 支援手動觸發部署
- 環境變數從 GitHub Secrets 注入
```

### 部署前檢查清單
執行對應的預提交測試（參見 [CLAUDE.md](/CLAUDE.md) 的測試層級定義）：
- Level 2 或 Level 3 測試通過
- 環境變數已正確配置

## 環境變數配置 

### 必要的環境變數
```bash
# Application Insights
APPINSIGHTS_INSTRUMENTATIONKEY="your-app-insights-key"
APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=...;IngestionEndpoint=..."

# Azure OpenAI 服務
AZURE_OPENAI_API_KEY="your-azure-openai-key"
AZURE_OPENAI_ENDPOINT="https://wenha-m7qan2zj-swedencentral.cognitiveservices.azure.com"

# Embedding 服務
AZURE_OPENAI_EMBEDDING_API_KEY="your-embedding-key"
AZURE_OPENAI_EMBEDDING_ENDPOINT="https://wenha-m7qan2zj-swedencentral.cognitiveservices.azure.com/openai/deployments/text-embedding-3-large/embeddings?api-version=2023-05-15"

# 課程 Embedding 服務
AZURE_OPENAI_COURSE_EMBEDDING_API_KEY="your-course-embedding-key"
AZURE_OPENAI_COURSE_EMBEDDING_ENDPOINT="https://ai-azureai700705952086.cognitiveservices.azure.com/openai/deployments/text-embedding-3-small/embeddings?api-version=2023-05-15"

# Azure Storage
AzureWebJobsStorage="your-storage-connection-string"
DEPLOYMENT_STORAGE_CONNECTION_STRING="your-deployment-storage-connection"

# 監控設定
MONITORING_ENABLED="false"              # 生產環境關閉重度監控
LIGHTWEIGHT_MONITORING="true"           # 輕量級監控（預設開啟）
ERROR_CAPTURE_ENABLED="true"           # 錯誤捕獲中間件

# Container Apps 認證
CONTAINER_APP_API_KEY="your-api-key"   # API 認證金鑰

# GPT-4.1 Mini (Japan East)
GPT41_MINI_JAPANEAST_ENDPOINT="https://airesumeadvisor.openai.azure.com/"
GPT41_MINI_JAPANEAST_DEPLOYMENT="gpt-4-1-mini-japaneast"
GPT41_MINI_JAPANEAST_API_KEY="your-gpt41-mini-key"
GPT41_MINI_JAPANEAST_API_VERSION="2025-01-01-preview"

# LLM 模型選擇
LLM_MODEL_KEYWORDS="gpt41-mini"        # 關鍵字提取使用 GPT-4.1 mini
LLM_MODEL_GAP_ANALYSIS="gpt4o-2"      # 差距分析使用 GPT-4o-2
LLM_MODEL_RESUME_TAILORING="gpt4o-2"  # 履歷客製化使用 GPT-4o-2

# CORS 設定
CORS_ORIGINS="https://airesumeadvisor.com,https://airesumeadvisor.bubbleapps.io,https://www.airesumeadvisor.com"

# 環境標識
ENVIRONMENT="production"               # production/development/staging
LOG_LEVEL="INFO"                      # DEBUG/INFO/WARNING/ERROR
```

### 配置方式

#### Azure Portal (Container Apps)
1. 進入 Container App
2. Settings → Environment variables
3. 新增或更新環境變數
4. 儲存（自動觸發新修訂版本）

#### Azure CLI (Container Apps)
```bash
# 更新單一環境變數
az containerapp update \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --set-env-vars KEY=VALUE

# 批量更新環境變數
az containerapp update \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --set-env-vars KEY1=VALUE1 KEY2=VALUE2

# 從 .env 檔案載入
az containerapp update \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --env-vars @.env.production
```

## Container Apps 部署流程

### 自動部署（推薦）
```bash
# 推送到 main 分支自動觸發
git push origin main
```

### 手動部署步驟

#### 1. 建置 Docker 映像
```bash
# 建置映像
docker build -t azure-container-api .

# 測試本地運行
docker run -p 8000:8000 --env-file .env.local azure-container-api

# 驗證健康檢查
curl http://localhost:8000/health
```

#### 2. 推送到 Azure Container Registry
```bash
# 登入 Azure
az login
az account set --subscription "5396d388-8261-464e-8ee4-112770674fba"

# 登入 Container Registry
az acr login --name airesumeadvisorregistry

# 標記映像
docker tag azure-container-api \
  airesumeadvisorregistry.azurecr.io/airesumeadvisor-api:$(date +%Y%m%d-%H%M%S)

# 推送映像
docker push airesumeadvisorregistry.azurecr.io/airesumeadvisor-api:$(date +%Y%m%d-%H%M%S)
```

#### 3. 更新 Container App
```bash
# 使用新映像更新 Container App
az containerapp update \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --image airesumeadvisorregistry.azurecr.io/airesumeadvisor-api:$(date +%Y%m%d-%H%M%S)

# 檢查部署狀態
az containerapp revision list \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --output table
```

#### 4. 驗證部署
```bash
# 檢查健康狀態
curl https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io/health

# 測試 API (使用 Header 認證)
curl -X POST "https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io/api/v1/extract-jd-keywords" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: [YOUR_API_KEY]" \
  -d '{"job_description": "Python developer with FastAPI experience needed"}'
```

## 監控與日誌

### Application Insights
1. 登入 [Azure Portal](https://portal.azure.com)
2. 前往 Application Insights: `airesumeadvisorfastapi`
3. 查看：
   - Live Metrics：即時效能
   - Failures：錯誤追蹤
   - Performance：效能分析
   - Logs：查詢日誌

### 常用查詢
```kusto
// 最近的錯誤
exceptions
| where timestamp > ago(1h)
| order by timestamp desc

// API 效能統計 (Container Apps)
customEvents
| where name == "RequestTracked"
| summarize 
    avg(todouble(customDimensions.duration_ms)), 
    percentile(todouble(customDimensions.duration_ms), 95),
    percentile(todouble(customDimensions.duration_ms), 99)
  by tostring(customDimensions.endpoint)

// 每小時請求量
requests
| where timestamp > ago(24h)
| summarize count() by bin(timestamp, 1h)
| render timechart

// 模型使用統計
customEvents
| where name == "LLMModelSelected"
| summarize count() by tostring(customDimensions.model_selected)
| render piechart

// 關鍵字提取效能
customEvents
| where name == "KeywordExtractionCompleted"
| summarize 
    avg(todouble(customDimensions.processing_time_ms)),
    avg(todouble(customDimensions.keyword_count))
  by bin(timestamp, 1h)
```

### Container Apps 日誌
```bash
# 查看即時日誌
az containerapp logs show \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --follow

# 查看特定修訂版本日誌
az containerapp logs show \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --revision <revision-name>
```

## 故障排除

### 常見問題

#### 1. 部署失敗
**症狀**：Docker 映像建置或推送失敗
**解決**：
- 檢查 Container Registry 認證
- 確認 Dockerfile 語法正確
- 驗證基礎映像可用性
- 檢查 ACR 儲存空間配額

#### 2. API 回應 500 錯誤
**症狀**：API 呼叫返回內部錯誤
**解決**：
- 檢查環境變數配置
- 查看 Application Insights 錯誤日誌
- 確認 LLM API 金鑰有效

#### 3. 效能問題
**症狀**：API 回應緩慢
**解決**：
- 檢查 Container App 擴展設定
- 分析 Application Insights 效能數據
- 調整實例數量（2-10）
- 檢查 LLM API 延遲
- 啟用輕量級監控查看瓶頸

#### 4. Container App 無法啟動
**症狀**：健康檢查失敗，容器無法運行
**解決**：
- 檢查環境變數完整性
- 查看容器啟動日誌
- 驗證 Docker 映像完整性
- 確認資源配置足夠（CPU/記憶體）

### 緊急回滾

Container Apps 支援快速回滾到前一個修訂版本：

```bash
# 列出所有修訂版本
az containerapp revision list \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --output table

# 啟用特定修訂版本（立即回滾）
az containerapp revision activate \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --revision <previous-revision-name>

# 停用有問題的修訂版本
az containerapp revision deactivate \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --revision <problematic-revision-name>

# 調整流量分配（金絲雀部署）
az containerapp ingress traffic set \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --revision-weight <old-revision>=80 <new-revision>=20
```

## 安全最佳實踐

### 金鑰管理
1. 使用 Azure Key Vault（計劃中）
2. 定期輪換 API 金鑰
3. 限制金鑰權限範圍

### 存取控制
1. 使用 X-API-Key 認證保護 API
2. Container Apps 內建 DDoS 保護
3. 設定 CORS 限制來源網域
4. 監控異常存取模式（Application Insights）

### 資料保護
1. 不記錄敏感資料
2. 使用 HTTPS only
3. 遵循 GDPR 規範

## 成本優化

### 監控成本
```bash
# 查看當前成本
az consumption usage list \
  --subscription "5396d388-8261-464e-8ee4-112770674fba" \
  --start-date 2025-07-01 \
  --end-date 2025-07-31
```

### 優化建議 (Container Apps)
1. **按需計費**：僅為實際使用的資源付費
2. **自動擴展**：設定最小實例數為 0（完全無使用時）
3. **資源調整**：
   - 開發環境：0.25 vCPU, 0.5GB RAM
   - 生產環境：1 vCPU, 2GB RAM
4. **快取策略**：
   - 關鍵字提取結果快取（減少 LLM 呼叫）
   - 靜態資源快取
5. **監控成本趨勢**：定期檢視 Cost Analysis

## 維護計畫

### 定期任務
- **每週**：檢查錯誤日誌
- **每月**：審查成本與效能
- **每季**：更新相依套件
- **每年**：災難恢復演練

### 更新流程
1. 在開發環境測試
2. 執行完整測試套件
3. 部署到 staging（如有）
4. 監控 30 分鐘
5. 正式發布