# 生產環境錯誤告警指南

## 概述

本指南描述了 Azure Container Apps 生產環境的錯誤監控和告警系統配置。系統設計目標是確保快速檢測和響應關鍵問題，維持服務的高可用性。

## 錯誤告警架構

### 監控層級

1. **應用程式層級錯誤**
   - 使用統一錯誤處理系統記錄
   - 輕量監控系統追蹤錯誤模式
   - 自動分類和計數

2. **基礎設施層級監控**
   - Container Apps 指標 (CPU, 記憶體, 重啟)
   - Azure Monitor 整合
   - Log Analytics 查詢

3. **外部服務監控**
   - Azure OpenAI 服務可用性
   - 認證服務狀態
   - 第三方 API 響應

## 告警規則配置

### 關鍵告警 (Critical - 立即響應)

| 告警名稱 | 條件 | 閾值 | 響應時間 |
|---------|------|------|----------|
| 高內部錯誤率 | SYSTEM_INTERNAL_ERROR | 5次/5分鐘 | < 5分鐘 |
| Azure OpenAI 不可用 | EXTERNAL_SERVICE_UNAVAILABLE | 3次/5分鐘 | < 5分鐘 |
| 容器頻繁重啟 | Container 重啟 | 3次/10分鐘 | < 10分鐘 |

### 高優先級告警 (High - 30分鐘內響應)

| 告警名稱 | 條件 | 閾值 | 響應時間 |
|---------|------|------|----------|
| 認證失敗激增 | AUTH_TOKEN_INVALID | 10次/10分鐘 | < 30分鐘 |
| 服務超時 | EXTERNAL_SERVICE_TIMEOUT | 10次/10分鐘 | < 30分鐘 |
| 處理失敗率高 | PROCESSING_ERROR | 15次/15分鐘 | < 30分鐘 |
| 速率限制頻繁 | EXTERNAL_RATE_LIMIT_EXCEEDED | 20次/15分鐘 | < 30分鐘 |

### 中等優先級告警 (Medium - 2小時內響應)

| 告警名稱 | 條件 | 閾值 | 響應時間 |
|---------|------|------|----------|
| 驗證錯誤率高 | VALIDATION_ERROR | 50次/30分鐘 | < 2小時 |
| CPU 使用率高 | CPU 使用率 | > 80% 持續5分鐘 | < 2小時 |
| 記憶體使用率高 | 記憶體使用率 | > 85% 持續5分鐘 | < 2小時 |

## 部署指南

### 1. 前置需求

```bash
# 確保已登入 Azure CLI
az login

# 設定正確的訂閱
az account set --subscription "5396d388-8261-464e-8ee4-112770674fba"

# 確認有適當的權限
az role assignment list --assignee $(az account show --query user.name --output tsv)
```

### 2. 執行部署腳本

```bash
# 執行告警部署腳本
./scripts/deploy_production_alerts.sh
```

### 3. 驗證配置

```bash
# 檢查 Action Group
az monitor action-group list --resource-group airesumeadvisorfastapi

# 檢查告警規則
az monitor metrics alert list --resource-group airesumeadvisorfastapi

# 檢查 Log Analytics 告警
az monitor scheduled-query list --resource-group airesumeadvisorfastapi
```

## 通知設定

### 電子郵件通知

- **DevOps 團隊**: devops@airesumeadvisor.com
- **緊急聯絡**: emergency@airesumeadvisor.com

### 通知級別

- **Critical**: 電子郵件 + SMS + Teams
- **High**: 電子郵件 + Teams  
- **Medium**: 電子郵件

### 通知冷卻期

- 預設冷卻期: 30分鐘
- 關鍵告警: 15分鐘
- 每小時最大告警數: 10個

## 健康檢查配置

### Container Apps 探針

```yaml
# Liveness Probe - 檢測應用程式是否存活
liveness_probe:
  path: /health
  port: 8000
  initial_delay_seconds: 10
  period_seconds: 30
  timeout_seconds: 5
  failure_threshold: 3

# Readiness Probe - 檢測應用程式是否準備接收流量
readiness_probe:
  path: /health
  port: 8000
  initial_delay_seconds: 5
  period_seconds: 10
  timeout_seconds: 3
  failure_threshold: 3

# Startup Probe - 檢測應用程式是否成功啟動
startup_probe:
  path: /health
  port: 8000
  initial_delay_seconds: 10
  period_seconds: 10
  timeout_seconds: 5
  failure_threshold: 30
```

## 監控查詢

### Azure Monitor Kusto 查詢

#### 1. 錯誤率趨勢

```kusto
ContainerAppConsoleLogs_CL
| where TimeGenerated > ago(1h)
| where Log_s contains "ERROR"
| summarize ErrorCount = count() by bin(TimeGenerated, 5m)
| render timechart
```

#### 2. 錯誤類型分布

```kusto
ContainerAppConsoleLogs_CL  
| where TimeGenerated > ago(1h)
| where Log_s contains "error_code"
| extend ErrorCode = extract('"error_code":"([^"]+)"', 1, Log_s)
| summarize Count = count() by ErrorCode
| render piechart
```

#### 3. API 端點錯誤統計

```kusto
ContainerAppConsoleLogs_CL
| where TimeGenerated > ago(1h) 
| where Log_s contains "api_name"
| extend ApiName = extract('"api_name":"([^"]+)"', 1, Log_s)
| where Log_s contains "ERROR"
| summarize ErrorCount = count() by ApiName
| order by ErrorCount desc
```

#### 4. 外部服務錯誤

```kusto
ContainerAppConsoleLogs_CL
| where TimeGenerated > ago(1h)
| where Log_s contains "EXTERNAL_SERVICE"
| extend ErrorType = extract('"error_code":"([^"]+)"', 1, Log_s)
| summarize Count = count() by ErrorType, bin(TimeGenerated, 10m)
| render timechart
```

## 故障排除流程

### 告警響應檢查清單

#### 關鍵告警 (Critical)

1. **立即確認**
   - [ ] 檢查服務是否可訪問
   - [ ] 驗證健康檢查端點
   - [ ] 查看容器狀態

2. **診斷步驟**
   - [ ] 檢查 Azure Monitor 儀表板
   - [ ] 查看容器日誌
   - [ ] 分析錯誤模式

3. **緩解措施**
   - [ ] 重啟容器 (如需要)
   - [ ] 檢查外部服務狀態
   - [ ] 聯絡相關團隊

#### 高優先級告警 (High)

1. **分析階段**
   - [ ] 收集詳細日誌
   - [ ] 識別錯誤根因
   - [ ] 評估影響範圍

2. **解決階段**
   - [ ] 實施修復措施
   - [ ] 監控修復效果
   - [ ] 更新文檔

### 常見問題解決

#### Azure OpenAI 服務不可用

```bash
# 檢查 Azure OpenAI 服務狀態
az cognitiveservices account show \
  --name airesumeadvisor \
  --resource-group airesumeadvisorfastapi

# 檢查 API 金鑰和配額
az cognitiveservices account keys list \
  --name airesumeadvisor \
  --resource-group airesumeadvisorfastapi
```

#### 高錯誤率分析

```bash
# 取得最近的錯誤日誌
az containerapp logs show \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --follow

# 查看特定時間範圍的日誌
az monitor log-analytics query \
  --workspace <workspace-id> \
  --analytics-query "ContainerAppConsoleLogs_CL | where TimeGenerated > ago(1h) | where Log_s contains 'ERROR'"
```

## 維護和優化

### 定期檢查項目

- **每週**
  - 檢查告警有效性
  - 分析錯誤趨勢
  - 更新閾值設定

- **每月**  
  - 檢閱告警回應時間
  - 優化通知設定
  - 更新流程文檔

- **每季**
  - 全面檢閱告警策略
  - 評估新的監控需求
  - 培訓團隊成員

### 效能調優

1. **閾值優化**
   - 基於歷史數據調整閾值
   - 減少誤報
   - 確保真實問題被檢測

2. **通知優化**
   - 避免告警疲勞
   - 優化通知內容
   - 改進響應流程

## 相關資源

- [Azure Monitor 文檔](https://docs.microsoft.com/azure/azure-monitor/)
- [Container Apps 監控](https://docs.microsoft.com/azure/container-apps/monitoring)
- [Log Analytics 查詢](https://docs.microsoft.com/azure/azure-monitor/logs/get-started-queries)
- [Azure CLI 參考](https://docs.microsoft.com/cli/azure/)

## 聯絡資訊

- **DevOps 團隊**: devops@airesumeadvisor.com
- **緊急聯絡**: emergency@airesumeadvisor.com  
- **技術支援**: support@airesumeadvisor.com