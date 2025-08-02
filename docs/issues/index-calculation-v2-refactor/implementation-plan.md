# Index Calculation V2 詳細實施計劃

## Python 3.11 特性應用

本專案使用 Python 3.11.8，可以利用以下新特性來改進實作：

1. **asyncio.TaskGroup** - 更好的並行任務管理和例外處理
2. **改進的錯誤訊息** - 更精確的錯誤定位和除錯
3. **效能提升** - 比 Python 3.9 快 10-60%，有助於達成效能目標
4. **typing 改進** - 更好的型別提示支援

## Phase 1: 服務架構重構 (Day 1-2)

### 1.1 建立基礎服務類別 (Day 1 上午)

#### 任務清單
- [ ] 建立 `src/services/index_calculation_v2.py`
- [ ] 實作 `IndexCalculationServiceV2` 基礎類別
- [ ] 整合 `BaseService` 繼承
- [ ] 實作依賴注入模式

#### 程式碼範例
```python
# src/services/index_calculation_v2.py
from typing import Optional, Dict, Any, List, Union
import time
import hashlib
from datetime import datetime, timedelta

from src.services.base_service import BaseService
from src.core.monitoring_service import monitoring_service
from src.services.embedding_client import EmbeddingClient

class IndexCalculationServiceV2(BaseService):
    """
    Enhanced index calculation service with caching and parallel processing.
    
    Key improvements (inspired by KeywordExtractionServiceV2):
    - In-memory caching with TTL
    - Parallel processing support
    - Detailed performance metrics
    - Service statistics
    """
    
    def __init__(
        self,
        embedding_client: Optional[EmbeddingClient] = None,
        enable_cache: bool = True,
        cache_ttl_minutes: int = 60,
        enable_parallel_processing: bool = True
    ):
        super().__init__()
        
        # Dependencies
        self.embedding_client = embedding_client or get_embedding_client()
        
        # Configuration
        self.enable_cache = enable_cache
        self.cache_ttl_minutes = cache_ttl_minutes
        self.enable_parallel_processing = enable_parallel_processing
        
        # Cache storage
        self._cache = {}
        self._cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }
        
        # Service statistics
        self.calculation_stats = {
            "total_calculations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "average_processing_time_ms": 0,
            "error_count": 0
        }
```

### 1.2 實作快取管理器 (Day 1 下午)

#### 任務清單
- [ ] 實作 `CacheManager` 類別
- [ ] 實作快取鍵生成邏輯
- [ ] 實作 TTL 管理
- [ ] 實作 LRU 淘汰策略

#### 關鍵方法
```python
def _generate_cache_key(
    self, 
    text: str, 
    cache_type: str = "embedding"
) -> str:
    """Generate cache key using SHA256 hash."""
    normalized = self._normalize_text(text)
    cache_input = f"{cache_type}:{normalized}"
    return hashlib.sha256(cache_input.encode('utf-8')).hexdigest()

def _get_cached_result(self, cache_key: str) -> Optional[Any]:
    """Get cached result if available and not expired."""
    if not self.enable_cache or cache_key not in self._cache:
        return None
    
    cached_entry = self._cache[cache_key]
    if self._is_expired(cached_entry):
        del self._cache[cache_key]
        self._cache_stats["evictions"] += 1
        return None
    
    self._cache_stats["hits"] += 1
    return cached_entry["result"]
```

### 1.3 整合統計收集 (Day 2 上午)

#### 任務清單
- [ ] 實作 `get_service_stats()` 方法
- [ ] 整合時間追蹤
- [ ] 實作詳細的 timing breakdown
- [ ] 加入快取效能指標

#### 統計資料結構
```python
def get_service_stats(self) -> Dict[str, Any]:
    """Get comprehensive service statistics."""
    cache_hit_rate = 0.0
    if self.calculation_stats["total_calculations"] > 0:
        cache_hit_rate = (
            self.calculation_stats["cache_hits"] / 
            self.calculation_stats["total_calculations"]
        )
    
    return {
        "service_name": "IndexCalculationServiceV2",
        "calculation_stats": self.calculation_stats.copy(),
        "cache_performance": {
            "enabled": self.enable_cache,
            "hit_rate": round(cache_hit_rate, 3),
            "total_hits": self._cache_stats["hits"],
            "total_misses": self._cache_stats["misses"],
            "cache_size": len(self._cache),
            "ttl_minutes": self.cache_ttl_minutes
        },
        "performance_optimizations": {
            "parallel_processing_enabled": self.enable_parallel_processing,
            "average_response_time_ms": self.calculation_stats["average_processing_time_ms"]
        }
    }
```

### 1.4 API 端點整合 (Day 2 下午)

#### 任務清單
- [ ] 更新 `src/api/v1/index_calculation.py`
- [ ] 整合新服務類別
- [ ] 加入統計端點
- [ ] 直接替換現有實作（無需保持向後相容）

## Phase 2: 效能優化 (Day 3-4)

### 2.1 Embedding 快取實作 (Day 3 上午)

#### 任務清單
- [ ] 實作 embedding 快取邏輯
- [ ] 整合快取到計算流程
- [ ] 加入快取預熱功能
- [ ] 實作快取清理策略

#### 快取流程
```python
async def _get_or_compute_embedding(
    self, 
    text: str
) -> List[float]:
    """Get embedding from cache or compute."""
    cache_key = self._generate_cache_key(text, "embedding")
    
    # Try cache first
    cached = self._get_cached_result(cache_key)
    if cached is not None:
        return cached
    
    # Compute if not cached
    embedding = await self.embedding_client.create_embedding(text)
    
    # Cache the result
    self._cache_result(cache_key, embedding)
    
    return embedding
```

### 2.2 並行處理優化 (Day 3 下午)

#### 任務清單
- [ ] 實作並行 embedding 生成
- [ ] 並行關鍵字分析
- [ ] 整合 asyncio.gather 和 Python 3.11 的 asyncio.TaskGroup
- [ ] 加入並行控制開關

#### 並行實作 (使用 Python 3.11 特性)
```python
async def _calculate_parallel(
    self,
    resume: str,
    job_description: str,
    keywords: List[str]
) -> Dict[str, Any]:
    """Parallel calculation of embeddings and keyword analysis."""
    if self.enable_parallel_processing:
        # Parallel execution using Python 3.11's TaskGroup
        async with asyncio.TaskGroup() as tg:
            embedding_task = tg.create_task(
                self._compute_embeddings_pair(resume, job_description)
            )
            keyword_task = tg.create_task(
                self._analyze_keyword_coverage(resume, keywords)
            )
        
        # TaskGroup automatically waits for all tasks and handles exceptions
        embeddings = embedding_task.result()
        keyword_coverage = keyword_task.result()
    else:
        # Sequential execution
        embeddings = await self._compute_embeddings_pair(resume, job_description)
        keyword_coverage = await self._analyze_keyword_coverage(resume, keywords)
    
    # Calculate similarity (depends on embeddings)
    similarity = self._calculate_similarity(embeddings)
    
    return {
        "embeddings": embeddings,
        "similarity": similarity,
        "keyword_coverage": keyword_coverage
    }
```

### 2.3 連線池優化 (Day 4 上午)

#### 任務清單
- [ ] 實作 HTTP 連線池
- [ ] 整合到 embedding client
- [ ] 加入連線健康檢查
- [ ] 實作連線復用

### 2.4 效能測試與調優 (Day 4 下午)

#### 任務清單
- [ ] 建立效能基準測試
- [ ] 測試快取效果
- [ ] 測試並行處理效果
- [ ] 調整參數優化

## Phase 3: 監控與配置 (Day 5)

### 3.1 詳細時間追蹤 (Day 5 上午)

#### 任務清單
- [ ] 實作 timing breakdown
- [ ] 整合到回應格式
- [ ] 加入效能事件追蹤
- [ ] 實作效能警報

#### Timing 結構
```python
timing_breakdown = {
    "validation_ms": 0,
    "cache_lookup_ms": 0,
    "embedding_generation_ms": 0,
    "similarity_calculation_ms": 0,
    "keyword_analysis_ms": 0,
    "cache_write_ms": 0,
    "total_ms": 0
}
```

### 3.2 事件追蹤系統 (Day 5 下午 - 上半)

#### 任務清單
- [ ] 定義業務事件
- [ ] 實作事件追蹤
- [ ] 整合監控服務
- [ ] 加入自定義指標

### 3.3 配置外部化 (Day 5 下午 - 下半)

#### 任務清單
- [ ] 移動配置到環境變數
- [ ] 實作配置驗證
- [ ] 加入 feature flags
- [ ] 支援動態配置

## Phase 4: 測試與文檔 (Day 6)

### 4.1 單元測試 (Day 6 上午)

#### 測試覆蓋目標
- [ ] 服務類別測試 (> 90%)
- [ ] 快取邏輯測試 (100%)
- [ ] 並行處理測試
- [ ] 錯誤處理測試

### 4.2 整合測試 (Day 6 下午 - 上半)

#### 測試案例
- [ ] API 端點測試
- [ ] 快取行為測試
- [ ] 並發場景測試
- [ ] 效能回歸測試

### 4.3 文檔更新 (Day 6 下午 - 下半)

#### 文檔任務
- [ ] 更新 API 文檔
- [ ] 更新架構文檔
- [ ] 建立操作手冊
- [ ] 更新 CHANGELOG

## 風險管理

### 技術風險
1. **快取一致性**
   - 緩解: 使用 TTL 和版本控制
   - 監控: 快取命中率和過期率

2. **並行競爭**
   - 緩解: 使用 asyncio 鎖
   - 測試: 壓力測試並發場景

3. **記憶體使用**
   - 緩解: LRU 淘汰和大小限制
   - 監控: 記憶體使用指標

### 時程風險
1. **延期風險**: 中等
2. **緩解措施**: 
   - 每日進度檢查
   - 優先完成核心功能
   - 保留 buffer 時間

## 交付標準

### 必須完成
- [ ] 快取機制實作並測試
- [ ] 服務類別重構完成
- [ ] 完全替換舊實作（追求程式碼簡潔）
- [ ] 基本測試覆蓋

### 應該完成
- [ ] 並行處理優化
- [ ] 完整監控整合
- [ ] 80% 測試覆蓋率

### 可以完成
- [ ] Redis 快取支援
- [ ] 動態配置系統
- [ ] 效能儀表板

## 驗收標準

1. **功能驗收**
   - 所有現有 API 正常運作
   - 新功能按預期工作

2. **效能驗收**
   - P95 < 2秒 (快取未命中)
   - P95 < 100ms (快取命中)
   - 支援 50+ QPS

3. **品質驗收**
   - 測試通過率 100%
   - 無關鍵 bug
   - 文檔完整

---

**計劃版本**: 1.0.0  
**建立日期**: 2025-08-02  
**負責人**: Backend Team