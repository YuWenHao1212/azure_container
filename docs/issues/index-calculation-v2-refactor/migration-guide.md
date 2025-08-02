# Index Calculation V2 遷移指南

## 1. 遷移概述

### 1.1 遷移目標
- 完全替換 V1 實作為 V2
- 簡化程式碼架構
- 無需考慮零停機（API 未對外開放）
- 直接部署，無需回滾機制

### 1.2 主要變更
| 項目 | V1 | V2 |
|------|----|----|
| 服務架構 | 函數式 + 簡單類別 | 完整服務類別 |
| 快取支援 | ❌ 無 | ✅ 內建快取 |
| 並行處理 | ❌ 無 | ✅ 支援 |
| 監控指標 | 基本 | 豐富詳細 |
| 配置管理 | 硬編碼 | 環境變數 |

## 2. 遷移前準備

### 2.1 環境檢查清單
- [ ] Python 3.11.8 已安裝（專案指定版本）
- [ ] 所有依賴套件已更新
- [ ] 環境變數已配置
- [ ] 監控系統已準備
- [ ] 備份計劃已制定

### 2.2 依賴更新
```bash
# 更新 requirements.txt
aiohttp>=3.8.0  # 新增：連線池支援
asyncio>=3.4.3  # 確保版本
pytest-asyncio>=0.21.0  # 測試支援
```

### 2.3 環境變數配置
```bash
# 新增到 .env 或環境配置
INDEX_CALC_CACHE_ENABLED=true
INDEX_CALC_CACHE_TTL_MINUTES=60
INDEX_CALC_CACHE_MAX_SIZE=1000
INDEX_CALC_PARALLEL_PROCESSING=true
INDEX_CALC_CONNECTION_POOL_SIZE=20
INDEX_CALC_REQUEST_TIMEOUT_SECONDS=10

# 保留現有配置
SIGMOID_X0=0.373
SIGMOID_K=15.0
```

## 3. 遷移步驟

### 3.1 Phase 1: 程式碼部署 (不影響服務)

#### Step 1: 部署新程式碼
```bash
# 1. 切換到功能分支
git checkout feature/index-calculation-v2-refactor

# 2. 合併到主分支
git checkout main
git merge feature/index-calculation-v2-refactor

# 3. 部署到生產環境
# 合併到 main 分支後，GitHub Actions 會自動部署到 Azure Container Apps
```

#### Step 2: 驗證部署
```bash
# 檢查健康狀態
curl https://your-api.com/health

# 確認新檔案存在
docker exec -it container_name ls -la src/services/index_calculation_v2.py
```

### 3.2 Phase 2: 直接切換到 V2

由於 API 尚未對外開放，無需考慮線上用戶影響，可直接切換：

```python
# src/api/v1/index_calculation.py
from src.services.index_calculation_v2 import IndexCalculationServiceV2

async def calculate_index(request: IndexCalculationRequest):
    # 直接使用 V2 服務
    service = IndexCalculationServiceV2()
    return await service.calculate_index(request)
```

### 3.3 Phase 3: 完全遷移

#### Step 1: 確認 V2 穩定運行
- 監控錯誤率 < 0.1%
- 效能達到預期目標
- 快取命中率 > 60%

#### Step 2: 移除 V1 程式碼
```bash
# 備份 V1 程式碼
cp src/services/index_calculation.py src/services/index_calculation_v1_backup.py

# 更新 imports
# 將所有 index_calculation 改為 index_calculation_v2
```

## 4. API 遷移

### 4.1 相容性保證
```python
# V1 請求格式（繼續支援）
{
    "resume": "string",
    "job_description": "string",
    "keywords": ["string"] | "string"
}

# V2 新增選項（向後相容） <-  this is good
{
    "resume": "string",
    "job_description": "string",
    "keywords": ["string"] | "string",
    "options": {  # 選填
        "enable_cache": true,
        "include_timing_breakdown": true
    }
}
```

### 4.2 回應格式變更
```python
# V1 回應
{
    "success": true,
    "data": {
        "raw_similarity_percentage": 65,
        "similarity_percentage": 75,
        "keyword_coverage": {...}
    }
}

# V2 新增欄位（僅在開發模式下包含 timing_breakdown） 
{
    "success": true,
    "data": {
        "raw_similarity_percentage": 65,
        "similarity_percentage": 75,
        "keyword_coverage": {...},
        "cache_hit": false,  # 新增
        "processing_time_ms": 1250,  # 新增
        "timing_breakdown": {...}  # 僅開發模式
    }
}
```

## 5. 監控與驗證

### 5.1 關鍵指標監控
```python
# 監控指標對比
metrics_to_monitor = {
    "response_time": {
        "v1_baseline": "3-5 seconds",
        "v2_target": "1-2 seconds",
        "alert_threshold": "3 seconds"
    },
    "error_rate": {
        "v1_baseline": "0.5%",
        "v2_target": "<0.1%",
        "alert_threshold": "1%"
    },
    "cache_hit_rate": {
        "v1_baseline": "N/A",
        "v2_target": ">60%",
        "alert_threshold": "<40%"
    }
}
```

### 5.2 驗證腳本
```python
# scripts/verify_migration.py
import asyncio
import aiohttp
import statistics

async def verify_v2_performance():
    """驗證 V2 效能達到預期"""
    test_requests = 100
    response_times = []
    
    async with aiohttp.ClientSession() as session:
        for i in range(test_requests):
            start = time.time()
            
            async with session.post(
                "https://api.com/api/v1/index-calculation",
                json={
                    "resume": f"Test resume {i % 10}",  # 10 種不同內容
                    "job_description": f"Test job {i % 10}",
                    "keywords": ["Python", "Docker"]
                }
            ) as response:
                data = await response.json()
                
            elapsed = (time.time() - start) * 1000
            response_times.append(elapsed)
            
            # 檢查快取行為
            if i >= 10:  # 第二輪應該有快取
                assert data["data"].get("cache_hit") is True
    
    # 分析結果
    p50 = statistics.median(response_times)
    p95 = statistics.quantiles(response_times, n=20)[18]
    
    print(f"V2 Performance: P50={p50:.0f}ms, P95={p95:.0f}ms")
    assert p50 < 1000  # P50 < 1秒
    assert p95 < 2000  # P95 < 2秒

if __name__ == "__main__":
    asyncio.run(verify_v2_performance())
```

## 6. 部署策略（無需回滾）

由於我們將完全移除舊程式碼，採用簡化的部署策略：

### 6.1 一次性部署
```bash
# 1. 合併功能分支
git checkout main
git merge feature/index-calculation-v2-refactor

# 2. 推送觸發自動部署
git push origin main

# 3. 驗證部署成功
./test/scripts/run_complete_test_suite.sh
```

### 6.2 部署後清理
```bash
# 移除舊的 V1 檔案
rm src/services/index_calculation.py
rm tests/unit/test_index_calculation.py  # 如果存在

# 更新 imports
# 確保所有引用都指向 index_calculation_v2
```

## 7. 常見問題處理

### 7.1 快取相關問題

**問題**: 快取命中率過低
```bash
# 解決方案
# 1. 檢查 TTL 設定
export INDEX_CALC_CACHE_TTL_MINUTES=120  # 增加到 2 小時

# 2. 檢查快取鍵生成
# 確保文本正規化正確
```

**問題**: 記憶體使用過高
```bash
# 解決方案
# 1. 減少快取大小
export INDEX_CALC_CACHE_MAX_SIZE=500

# 2. 減少 TTL
export INDEX_CALC_CACHE_TTL_MINUTES=30
```

### 7.2 效能問題

**問題**: V2 比 V1 慢
```python
# 檢查清單
1. 確認快取已啟用
2. 確認並行處理已啟用
3. 檢查連線池配置
4. 查看 timing_breakdown 找出瓶頸
```

### 7.3 相容性問題

**問題**: 客戶端收到意外回應
```python
# 解決方案
# 使用相容模式
class CompatibilityMiddleware:
    def process_response(self, response):
        # 移除 V2 新增欄位
        if self.client_version < "2.0":
            response.pop("cache_hit", None)
            response.pop("timing_breakdown", None)
        return response
```

## 8. 遷移時間表

### 8.1 建議時程
| 階段 | 時間 | 活動 |
|------|------|------|
| 準備 | Day -7 | 環境準備、依賴更新 |
| 測試 | Day -3 | 預生產環境測試 |
| 部署 | Day 0 | 程式碼部署（不啟用）|
| 灰度 | Day 1-3 | 10% → 50% → 100% |
| 監控 | Day 4-7 | 密切監控、調優 |
| 清理 | Day 14 | 移除舊程式碼 |

### 8.2 檢查點
- [ ] Day 0: 程式碼部署成功
- [ ] Day 1: 10% 流量無異常
- [ ] Day 2: 50% 流量穩定
- [ ] Day 3: 100% 切換完成
- [ ] Day 7: 所有指標達標
- [ ] Day 14: V1 程式碼移除

## 9. 聯絡資訊

### 9.1 緊急聯絡
- **技術負責人**: Backend Team Lead
- **緊急電話**: +886-xxx-xxx-xxx
- **Slack Channel**: #index-calc-migration

### 9.2 支援資源
- [技術規格書](technical-specification.md)
- [架構設計文檔](architecture-design.md)
- [API 文檔](../../API_REFERENCE.md)

---

**文檔版本**: 1.0.0  
**建立日期**: 2025-08-02  
**最後更新**: 2025-08-02  
**維護團隊**: Backend Team