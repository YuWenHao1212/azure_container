# Azure Container Apps Memory Management Guide

**Version**: 1.0.0  
**Target Platform**: Azure Container Apps  
**Application**: AI Resume Advisor API  
**Memory Allocation**: 2GB (1 CPU, 2GB RAM)

## 📋 目錄

1. [Memory Leak 風險分析](#memory-leak-風險分析)
2. [預防措施實作](#預防措施實作)
3. [監控和警報設定](#監控和警報設定)
4. [Azure Container Apps 配置](#azure-container-apps-配置)
5. [測試和驗證](#測試和驗證)
6. [生產環境最佳實踐](#生產環境最佳實踐)
7. [故障排除指南](#故障排除指南)

## Memory Leak 風險分析

### 🚨 主要風險點

#### 1. HTTP 連線池管理
**風險**: httpx.AsyncClient 實例未正確關閉
```python
# 風險代碼
self.client = httpx.AsyncClient()  # 沒有在應用關閉時釋放

# 解決方案
@app.on_event("shutdown")
async def shutdown_event():
    await resource_manager.shutdown()  # 統一清理所有連線
```

#### 2. 並行任務累積
**風險**: Python 3.11 TaskGroup 中的任務未清理
```python
# 風險代碼
async with asyncio.TaskGroup() as tg:
    tasks = [tg.create_task(process(item)) for item in large_list]
    # 任務可能累積在記憶體中

# 解決方案
async with resource_manager.managed_task(process_batch(batch)) as task:
    result = await task  # 自動清理
```

#### 3. Application Insights 緩衝區
**風險**: TelemetryClient 內部緩衝區持續增長
```python
# 解決方案
self.telemetry_client.flush()  # 定期強制發送
atexit.register(lambda: self.telemetry_client.flush())  # 應用關閉時清理
```

#### 4. 快取大小無限制
**風險**: LRU 快取沒有大小限制
```python
# 解決方案
resource_manager.set_cache_object(key, value)  # 自動限制大小
```

### 📊 記憶體使用模式分析

| 元件 | 正常使用 | 峰值使用 | 潛在洩漏風險 |
|------|---------|---------|------------|
| HTTP 連線池 | 10-50MB | 100MB | ⚠️ 高 |
| Azure OpenAI 客戶端 | 20-80MB | 150MB | ⚠️ 中 |
| 快取系統 | 50-200MB | 500MB | ⚠️ 高 |
| 並行處理 | 100-300MB | 800MB | ⚠️ 中 |
| Application Insights | 10-30MB | 100MB | ⚠️ 低 |

## 預防措施實作

### 🛠️ 1. Resource Manager 系統

已實作統一的資源管理系統：

```python
from src.core.resource_manager import resource_manager

# 自動連線管理
async with resource_manager.managed_connection(create_client) as client:
    result = await client.request()  # 自動關閉

# 任務生命週期管理
async with resource_manager.managed_task(heavy_processing()) as task:
    result = await task  # 自動清理

# 快取大小限制
resource_manager.set_cache_object("key", value)  # 自動 LRU 淘汰
```

### 🔍 2. 記憶體監控端點

開發/測試環境提供記憶體監控 API：

```bash
# 取得記憶體統計
GET /api/v1/memory/stats

# 強制垃圾回收
POST /api/v1/memory/gc

# 清理快取
POST /api/v1/memory/clear-cache

# 記憶體健康檢查
GET /api/v1/memory/health
```

### ⚡ 3. 應用程式生命週期管理

```python
@app.on_event("startup")
async def startup_event():
    await resource_manager.start()
    logger.info(f"Startup memory: {get_memory_usage():.1f}MB")

@app.on_event("shutdown") 
async def shutdown_event():
    await resource_manager.shutdown()
    logger.info(f"Shutdown memory: {get_memory_usage():.1f}MB")
```

## 監控和警報設定

### 📈 Azure Container Apps 監控配置

#### 1. 環境變數設定
```bash
# 記憶體閾值設定
MEMORY_WARNING_THRESHOLD=1500     # 1.5GB 警告
MEMORY_CRITICAL_THRESHOLD=1800    # 1.8GB 嚴重
CONTAINER_MEMORY_LIMIT_MB=2048    # 2GB 容器限制

# 監控設定
MONITORING_ENABLED=true
LIGHTWEIGHT_MONITORING=true
ERROR_CAPTURE_ENABLED=true
```

#### 2. Application Insights 查詢

```kusto
// 記憶體使用趨勢
customEvents
| where name == "MemoryUsageCheck"
| extend memory_mb = toreal(customDimensions.memory_mb)
| summarize avg(memory_mb), max(memory_mb) by bin(timestamp, 5m)
| render timechart

// 記憶體洩漏檢測
customEvents  
| where name == "MemoryUsageCheck"
| extend memory_mb = toreal(customDimensions.memory_mb)
| where memory_mb > 1500  // 超過警告閾值
| summarize count() by bin(timestamp, 1h)

// 垃圾回收效果分析
customEvents
| where name contains "GarbageCollection"
| extend freed_mb = toreal(customDimensions.memory_freed_mb)
| summarize total_freed = sum(freed_mb) by bin(timestamp, 1h)
```

#### 3. Azure 警報規則

```json
{
  "name": "HighMemoryUsage",
  "condition": {
    "allOf": [
      {
        "metricName": "WorkingSetBytes",
        "operator": "GreaterThan", 
        "threshold": 1610612736,  // 1.5GB in bytes
        "timeAggregation": "Average",
        "dimensions": [
          {
            "name": "RevisionName",
            "operator": "Include",
            "values": ["*"]
          }
        ]
      }
    ]
  },
  "actions": [
    {
      "actionGroupId": "/subscriptions/.../actionGroups/memory-alerts"
    }
  ]
}
```

## Azure Container Apps 配置

### 🏗️ 1. Container App 資源配置

```yaml
# container-app.yaml
apiVersion: 2022-03-01
location: Japan East
properties:
  configuration:
    ingress:
      external: true
      targetPort: 8000  
  template:
    containers:
    - name: airesumeadvisor-api
      image: airesumeadvisorregistry.azurecr.io/airesumeadvisor-api:latest
      resources:
        cpu: 1.0
        memory: 2Gi  # 2GB 記憶體限制
      env:
      # Memory management settings
      - name: MEMORY_WARNING_THRESHOLD
        value: "1500"
      - name: MEMORY_CRITICAL_THRESHOLD  
        value: "1800"
      - name: CONTAINER_MEMORY_LIMIT_MB
        value: "2048"
      
      # Resource limits for Python
      - name: PYTHONUNBUFFERED
        value: "1"
      - name: PYTHONMALLOC
        value: "malloc"  # Use standard malloc for better memory tracking
        
    scale:
      minReplicas: 2
      maxReplicas: 10
      rules:
      - name: cpu-scaling
        http:
          metadata:
            concurrentRequests: "20"
      - name: memory-scaling  
        custom:
          type: memory
          metadata:
            type: Utilization
            value: "70"  # Scale when memory usage > 70%
```

### 🔧 2. Dockerfile 最佳化

```dockerfile
FROM python:3.11-slim

# Memory optimization
ENV PYTHONUNBUFFERED=1
ENV PYTHONMALLOC=malloc
ENV MALLOC_MMAP_THRESHOLD_=131072
ENV MALLOC_TRIM_THRESHOLD_=131072
ENV MALLOC_TOP_PAD_=131072

# Install system dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ src/
COPY .env.example .env

# Create non-root user for security
RUN adduser --disabled-password --gecos '' --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start application
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 📋 3. 部署腳本更新

```bash
#!/bin/bash
# deploy-with-memory-monitoring.sh

set -e

# Build with memory optimization flags
docker build \
  --build-arg PYTHONMALLOC=malloc \
  --build-arg MALLOC_TRIM_THRESHOLD_=131072 \
  -t airesumeadvisorregistry.azurecr.io/airesumeadvisor-api:latest .

# Deploy with memory monitoring
az containerapp update \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --image airesumeadvisorregistry.azurecr.io/airesumeadvisor-api:latest \
  --set-env-vars \
    MEMORY_WARNING_THRESHOLD=1500 \
    MEMORY_CRITICAL_THRESHOLD=1800 \
    CONTAINER_MEMORY_LIMIT_MB=2048 \
    MONITORING_ENABLED=true \
    LIGHTWEIGHT_MONITORING=true

echo "Deployment completed with memory monitoring enabled"
```

## 測試和驗證

### 🧪 1. 記憶體洩漏測試

```bash
# 運行完整的記憶體洩漏測試
./test/scripts/run_memory_leak_tests.sh

# 只運行壓力測試
./test/scripts/run_memory_leak_tests.sh stress

# 分析現有結果
./test/scripts/run_memory_leak_tests.sh analyze
```

### 📊 2. 效能基準測試

```bash
# 運行包含記憶體監控的效能測試
./test/scripts/run_complete_test_suite.sh --include-performance --stage memory

# 監控記憶體使用模式
pytest test/memory/test_memory_leak_detection.py -v --tb=short
```

### 🔍 3. 生產前驗證清單

- [ ] 所有記憶體洩漏測試通過
- [ ] 啟動記憶體佔用 < 500MB
- [ ] 峰值記憶體使用 < 1.5GB
- [ ] 資源清理正常工作
- [ ] 監控端點正常運作
- [ ] 垃圾回收有效
- [ ] 警報規則已配置

## 生產環境最佳實踐

### 🎯 1. 記憶體管理策略

#### 定期清理任務
```python
# 每5分鐘自動檢查記憶體使用
async def memory_cleanup_task():
    while True:
        stats = resource_manager.get_stats()
        if stats.memory_metrics.rss_mb > MEMORY_WARNING_THRESHOLD:
            await resource_manager.force_garbage_collection()
        await asyncio.sleep(300)  # 5分鐘
```

#### 請求級別的資源管理
```python
@app.middleware("http")
async def memory_management_middleware(request: Request, call_next):
    # 請求開始前檢查記憶體
    initial_memory = get_memory_usage()
    
    response = await call_next(request)
    
    # 請求結束後清理
    final_memory = get_memory_usage()
    memory_growth = final_memory - initial_memory
    
    if memory_growth > 50:  # 50MB
        await resource_manager.force_garbage_collection()
    
    return response
```

### 🔄 2. 自動恢復機制

```python
async def memory_recovery_handler():
    """自動記憶體恢復處理器"""
    stats = resource_manager.get_stats()
    memory_mb = stats.memory_metrics.rss_mb
    
    if memory_mb > MEMORY_CRITICAL_THRESHOLD:
        logger.critical(f"Critical memory usage: {memory_mb}MB")
        
        # 1. 清理快取
        resource_manager.clear_cache()
        
        # 2. 強制垃圾回收
        await resource_manager.force_garbage_collection()
        
        # 3. 等待並重新檢查
        await asyncio.sleep(10)
        new_stats = resource_manager.get_stats()
        
        if new_stats.memory_metrics.rss_mb > MEMORY_CRITICAL_THRESHOLD:
            # 4. 最後手段：重啟容器實例
            logger.error("Memory still critical after cleanup - requesting restart")
            os._exit(1)  # Force container restart
```

### 📈 3. 監控和警報

#### Application Insights Dashboard
```json
{
  "dashboard": {
    "widgets": [
      {
        "type": "chart",
        "title": "Memory Usage Trend",
        "query": "customEvents | where name == 'MemoryUsageCheck'"
      },
      {
        "type": "number", 
        "title": "Current Memory Usage",
        "query": "customEvents | where name == 'MemoryUsageCheck' | top 1 by timestamp"
      },
      {
        "type": "table",
        "title": "Memory Warnings",
        "query": "customEvents | where customDimensions.memory_mb > 1500"
      }
    ]
  }
}
```

## 故障排除指南

### 🚨 常見記憶體問題

#### 1. 記憶體持續增長
```bash
# 診斷步驟
curl -X GET "https://your-app.azurecontainerapps.io/api/v1/memory/stats"
curl -X POST "https://your-app.azurecontainerapps.io/api/v1/memory/gc"
curl -X GET "https://your-app.azurecontainerapps.io/api/v1/memory/health"

# 檢查記憶體洩漏
./test/scripts/run_memory_leak_tests.sh
```

#### 2. 容器重啟頻繁
```bash
# 檢查 Azure Container Apps 日誌
az containerapp logs show \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --follow

# 檢查記憶體使用歷史
az monitor metrics list \
  --resource "/subscriptions/.../containerApps/airesumeadvisor-api-production" \
  --metric "WorkingSetBytes" \
  --start-time "2024-01-01T00:00:00Z"
```

#### 3. 效能下降
```bash
# 檢查垃圾回收頻率
grep "garbage collection" /var/log/app/*.log

# 分析記憶體分配模式
python3 -c "
import tracemalloc
tracemalloc.start()
# ... run your application code ...
current, peak = tracemalloc.get_traced_memory()
print(f'Current: {current / 1024 / 1024:.1f}MB')
print(f'Peak: {peak / 1024 / 1024:.1f}MB')
"
```

### 📞 緊急回應程序

#### Level 1: 記憶體警告 (>1.5GB)
1. 檢查當前記憶體統計
2. 執行手動垃圾回收
3. 清理快取
4. 監控5分鐘

#### Level 2: 記憶體嚴重 (>1.8GB) 
1. 立即清理所有快取
2. 強制垃圾回收
3. 檢查活躍連線數
4. 考慮重啟實例

#### Level 3: 記憶體臨界 (>1.9GB)
1. 自動觸發容器重啟
2. 通知開發團隊
3. 分析根本原因
4. 實施緊急修復

## 📋 檢查清單

### 部署前檢查
- [ ] 記憶體洩漏測試通過
- [ ] 資源管理器正常工作
- [ ] 監控端點可訪問
- [ ] 警報規則已配置
- [ ] 自動清理機制啟用

### 運行時監控
- [ ] 每日檢查記憶體趨勢
- [ ] 每週執行記憶體洩漏測試
- [ ] 監控垃圾回收效果
- [ ] 追蹤容器重啟次數
- [ ] 分析效能指標

---

**文檔版本**: 1.0.0  
**最後更新**: 2025-01-01  
**維護者**: Backend Architecture Team  
**審核者**: DevOps Team