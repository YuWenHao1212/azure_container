# API 監控端點文檔

## 生產監控
- **Application Insights**: 整合完整遙測
- **健康檢查**: `/health` 端點自動監控
- **錯誤追蹤**: 統一錯誤格式與分類

## 開發除錯端點 (非生產環境)

### 基本監控
- `GET /api/v1/monitoring/stats` - 監控統計
- `GET /api/v1/debug/storage-info` - 錯誤儲存資訊  
- `GET /api/v1/debug/errors` - 最近錯誤記錄
- `GET /debug/monitoring` - 監控狀態除錯

### 課程快取監控
- `GET /api/v1/debug/course-cache/stats` - 快取統計
- `GET /api/v1/debug/course-cache/health` - 快取健康狀態
- `POST /api/v1/debug/course-cache/cleanup` - 清理過期項目
- `POST /api/v1/debug/course-cache/clear` - 清空快取（慎用）

## 監控指標

### 關鍵效能指標 (KPIs)
- **回應時間**: P50, P95, P99
- **錯誤率**: 5xx, 4xx 錯誤百分比
- **吞吐量**: 每秒請求數
- **資源使用**: CPU, 記憶體使用率

### 警報閾值
- 回應時間 > 5s
- 錯誤率 > 5%
- CPU 使用率 > 80%
- 記憶體使用率 > 90%

## Azure Monitor 整合
```bash
# 查看即時日誌
az monitor app-insights query \
  --app <app-id> \
  --analytics-query "traces | order by timestamp desc | take 100"

# 查看異常
az monitor app-insights query \
  --app <app-id> \
  --analytics-query "exceptions | order by timestamp desc | take 50"
```