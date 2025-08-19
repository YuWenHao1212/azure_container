# 部署環境變數設定指南

## 新增的環境變數

### ENABLE_COURSE_CACHE
- **用途**: 控制動態課程快取的啟用/停用
- **預設值**: `true`
- **可選值**: `true` / `false`
- **說明**: 
  - 設為 `true` 時啟用動態快取（LRU + TTL，30分鐘過期）
  - 設為 `false` 時停用快取，直接查詢資料庫
  - 用於除錯或效能比較

## 需要更新的地方

### 1. GitHub Actions (.github/workflows/)
需要在以下 workflow 檔案中添加：
- `ci.yml` - CI/CD pipeline
- `smoke-test.yml` - Smoke tests
- 任何其他需要執行測試的 workflow

```yaml
env:
  ENABLE_COURSE_CACHE: 'true'
```

### 2. Azure Container Apps
需要在 Azure Portal 或透過 Azure CLI 設定：

#### 透過 Azure Portal:
1. 前往 Container Apps > airesumeadvisor-api-production
2. Settings > Environment variables
3. 新增環境變數：
   - Name: `ENABLE_COURSE_CACHE`
   - Value: `true`

#### 透過 Azure CLI:
```bash
az containerapp update \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --set-env-vars ENABLE_COURSE_CACHE=true
```

### 3. 開發環境 (airesumeadvisor-api-dev)
同樣需要設定（如果啟用開發環境）：
```bash
az containerapp update \
  --name airesumeadvisor-api-dev \
  --resource-group airesumeadvisorfastapi \
  --set-env-vars ENABLE_COURSE_CACHE=true
```

## 驗證設定

### 1. 驗證 Azure Container Apps 設定
```bash
# 查看生產環境變數
az containerapp show \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --query "properties.template.containers[0].env[?name=='ENABLE_COURSE_CACHE'].{name:name, value:value}" \
  -o table
```

### 2. 驗證快取狀態
訪問監控 API 端點：
```bash
curl https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io/api/v1/debug/course-cache/stats \
  -H "X-API-Key: $CONTAINER_APP_API_KEY"
```

回應中會顯示快取是否啟用。

## 快取控制操作

### 停用快取（用於除錯）
```bash
az containerapp update \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --set-env-vars ENABLE_COURSE_CACHE=false
```

### 重新啟用快取
```bash
az containerapp update \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --set-env-vars ENABLE_COURSE_CACHE=true
```

## 注意事項

1. **預設行為**: 如果未設定此環境變數，預設為 `true`（啟用快取）
2. **效能影響**: 停用快取會增加資料庫負載，建議只在除錯時短暫停用
3. **監控**: 使用 `/api/v1/debug/course-cache/stats` 監控快取效能
4. **清理**: 可透過 `/api/v1/debug/course-cache/clear` 手動清除快取

## 部署檢查清單

- [ ] 更新 .env.example ✅
- [ ] 更新 .env ✅
- [ ] 更新 .env.test ✅
- [x] 更新 GitHub Actions workflows ✅ (ci-cd-main.yml 已更新)
- [ ] 更新 Azure Container Apps - Production (需手動執行)
- [ ] 更新 Azure Container Apps - Dev (如果使用)
- [ ] 驗證設定生效
- [ ] 測試快取開關功能

---

**文件版本**: 1.0.0  
**建立日期**: 2025-08-19  
**最後更新**: 2025-08-19