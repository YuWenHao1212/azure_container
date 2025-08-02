# Index Calculation V2 架構設計文檔

## 0. Python 3.11 架構考量

### 0.1 效能優勢
- **整體效能提升**: 比 Python 3.9 快 10-60%
- **更快的函數調用**: 對高頻調用的快取查詢有顯著改善
- **更好的記憶體管理**: 減少記憶體使用，有助於快取更多資料

### 0.2 新特性應用
- **asyncio.TaskGroup**: 更優雅的並行任務管理
- **ExceptionGroup**: 更好的並行錯誤處理
- **改進的型別提示**: 更精確的靜態分析

## 1. 系統架構概覽

### 1.0 部署架構
採用 **Azure Container Apps** 架構（非 Azure Functions）：
```
HTTP Request 
  → Container Apps Ingress (內建負載平衡) 
  → FastAPI (Native，無 ASGI 適配層) 
  → Business Logic
```

**優勢**：
- 原生 FastAPI 執行，無冷啟動問題
- 持久連線池，減少 overhead
- 自動擴展 2-10 實例
- 原生支援並發請求 


### 1.1 整體架構圖

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway                               │
│                 POST /api/v1/index-calculation                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                    API Endpoint Layer                            │
│               IndexCalculationRouter                             │
│  - Request validation                                            │
│  - Response formatting                                           │
│  - Error handling                                                │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                    Service Layer                                 │
│             IndexCalculationServiceV2                            │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐        │
│  │Cache Manager │  │ Parallel     │  │ Stats          │        │
│  │              │  │ Processor    │  │ Collector      │        │
│  └──────┬───────┘  └──────┬───────┘  └────────┬───────┘        │
│         │                  │                    │                │
│  ┌──────▼───────────────────▼──────────────────▼────────┐      │
│  │              Core Processing Engine                   │      │
│  │  - Embedding generation                               │      │
│  │  - Similarity calculation                             │      │
│  │  - Keyword coverage analysis                          │      │
│  └───────────────────────┬──────────────────────────────┘      │
└─────────────────────────┬┴──────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                    External Services                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Azure OpenAI    │  │ Cache Storage   │  │ Monitoring      │ │
│  │ Embedding API   │  │ (Memory/Redis)  │  │ Service         │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 資料流程圖

```
請求 → 驗證 → 快取檢查 ┬→ [快取命中] → 返回快取結果
                    │
                    └→ [快取未命中] → 並行處理 ┬→ Embedding 生成
                                             │
                                             └→ 關鍵字分析
                                             │
                                             ↓
                                          相似度計算
                                             │
                                             ↓
                                          結果聚合
                                             │
                                             ↓
                                          寫入快取
                                             │
                                             ↓
                                          返回結果
```

## 2. 核心元件設計

### 2.1 IndexCalculationServiceV2

```python
class IndexCalculationServiceV2(BaseService):
    """
    主要服務類別，參考 KeywordExtractionServiceV2 設計
    """
    def __init__(
        self,
        embedding_client: Optional[EmbeddingClient] = None,
        enable_cache: bool = True,
        cache_ttl_minutes: int = 60,
        enable_parallel_processing: bool = True,
        connection_pool_size: int = 20
    ):
        # 依賴注入
        self.embedding_client = embedding_client or get_embedding_client()
        self.cache_manager = CacheManager(enable_cache, cache_ttl_minutes)
        self.stats_collector = StatsCollector()
        
        # 配置
        self.enable_parallel_processing = enable_parallel_processing
        self.connection_pool = ConnectionPool(connection_pool_size)
```

### 2.2 CacheManager

```python
class CacheManager:
    """
    統一的快取管理器
    """
    def __init__(self, enabled: bool, ttl_minutes: int):
        self._cache: Dict[str, CacheEntry] = {}
        self._enabled = enabled
        self._ttl_minutes = ttl_minutes
        self._stats = CacheStats()
    
    async def get_or_compute(
        self,
        key: str,
        compute_func: Callable,
        cache_type: str
    ) -> Any:
        """智能快取獲取或計算"""
        if self._enabled:
            cached = self._get_cached(key)
            if cached:
                self._stats.record_hit(cache_type)
                return cached
        
        self._stats.record_miss(cache_type)
        result = await compute_func()
        
        if self._enabled:
            self._set_cache(key, result)
        
        return result
```

### 2.3 ParallelProcessor

```python
class ParallelProcessor:
    """
    並行處理協調器
    """
    async def process_parallel(
        self,
        resume: str,
        job_description: str,
        keywords: List[str]
    ) -> Dict[str, Any]:
        """並行執行多個處理任務"""
        tasks = [
            self._generate_embeddings(resume, job_description),
            self._analyze_keywords(resume, keywords)
        ]
        
        if self.enable_parallel:
            # Python 3.11: 使用 TaskGroup 取代 gather 獲得更好的錯誤處理
            async with asyncio.TaskGroup() as tg:
                for task in tasks:
                    tg.create_task(task)
        else:
            results = []
            for task in tasks:
                results.append(await task)
        
        return self._merge_results(results)
```

## 3. 快取設計

### 3.1 快取層級

```
L1 Cache (Memory)
├── Embedding Cache
│   ├── Key: SHA256(text)
│   ├── Value: embedding vector
│   └── TTL: 60 minutes
│
├── Similarity Cache  
│   ├── Key: SHA256(resume + job_desc)
│   ├── Value: similarity scores
│   └── TTL: 60 minutes
│
└── Coverage Cache
    ├── Key: SHA256(resume + keywords)
    ├── Value: coverage analysis
    └── TTL: 60 minutes

L2 Cache (Redis) - Future
├── Persistent cache
├── Shared across instances
└── Longer TTL
```

### 3.2 快取策略

1. **Write-Through**: 計算後立即寫入快取
2. **LRU Eviction**: 達到大小限制時淘汰最少使用
3. **TTL Expiration**: 基於時間的自動過期
4. **Lazy Cleanup**: 每 100 次寫入觸發清理

## 4. 並行處理設計

### 4.1 並行任務分解

```python
async def calculate_index_parallel(self, request):
    """並行處理主流程"""
    # Phase 1: 並行驗證和預處理
    validation_task = self.validate_input(request)
    preprocess_task = self.preprocess_texts(request)
    
    # Python 3.11: 使用 TaskGroup 進行並行驗證
    async with asyncio.TaskGroup() as tg:
        validation_future = tg.create_task(validation_task)
        preprocess_future = tg.create_task(preprocess_task)
    
    validation = validation_future.result()
    processed = preprocess_future.result()
    
    # Phase 2: 並行計算
    embedding_task = self.compute_embeddings(processed)
    keyword_task = self.analyze_keywords(processed)
    
    # Python 3.11: TaskGroup 自動處理例外
    async with asyncio.TaskGroup() as tg:
        embedding_future = tg.create_task(embedding_task)
        keyword_future = tg.create_task(keyword_task)
    
    embeddings = embedding_future.result()
    keyword_analysis = keyword_future.result()
    
    # Phase 3: 串行計算相似度（依賴 embeddings）
    similarity = await self.calculate_similarity(embeddings)
    
    return self.merge_results(similarity, keyword_analysis)
```

### 4.2 連線池管理

```python
class ConnectionPoolManager:
    """HTTP 連線池管理"""
    def __init__(self, pool_size: int = 20):
        self._pools: Dict[str, aiohttp.TCPConnector] = {}
        self._pool_size = pool_size
    
    async def get_session(self, endpoint: str) -> aiohttp.ClientSession:
        if endpoint not in self._pools:
            connector = aiohttp.TCPConnector(
                limit=self._pool_size,
                limit_per_host=self._pool_size,
                ttl_dns_cache=300
            )
            self._pools[endpoint] = connector
        
        return aiohttp.ClientSession(connector=self._pools[endpoint])
```

## 5. 監控設計

### 5.1 輕量級監控架構

採用與 Keyword Extraction V2 相同的輕量級監控策略：

```
生產環境配置：
LIGHTWEIGHT_MONITORING=true
MONITORING_ENABLED=false

監控資料儲存：
├── 服務記憶體統計 (Service Stats)
│   ├── 總請求數
│   ├── 快取命中率
│   ├── 平均處理時間
│   └── 錯誤計數
│
├── 快取效能指標 (Cache Performance)
│   ├── 命中/未命中次數
│   ├── 快取大小
│   └── 淘汰次數
│
└── 簡化效能追蹤 (僅開發模式)
    ├── Embedding 生成時間
    ├── 相似度計算時間
    └── 關鍵字分析時間
```

### 5.2 輕量級事件追蹤

```python
class LightweightEventTracker:
    """輕量級事件追蹤（生產環境）"""
    async def track_calculation(self, event_data: Dict[str, Any]):
        # 生產環境僅追蹤關鍵指標
        if settings.LIGHTWEIGHT_MONITORING:
            self._update_stats({
                "total_calculations": 1,
                "cache_hit": event_data.get("cache_hit", False),
                "processing_time_ms": event_data["processing_time"],
                "similarity_score": event_data["similarity"]
            })
        
        # 開發環境可追蹤詳細資訊
        if settings.ENVIRONMENT == "development":
            await monitoring_service.track_event(
                "IndexCalculated",
                {
                    **event_data,
                    "timing_breakdown": event_data.get("timing_breakdown")
                }
            )
```

## 6. 錯誤處理架構

### 6.1 錯誤處理層級

```
API Layer
├── Validation Errors → 400 Bad Request
├── Authentication Errors → 401 Unauthorized
└── Not Found Errors → 404 Not Found

Service Layer  
├── Embedding Errors → Retry with backoff
├── Cache Errors → Degrade gracefully
└── Timeout Errors → Return partial results

Infrastructure Layer
├── Network Errors → Circuit breaker
├── Service Unavailable → 503 response
└── Unknown Errors → 500 with logging
```

### 6.2 Python 3.11 並行錯誤處理

```python
class ParallelErrorHandler:
    """利用 Python 3.11 ExceptionGroup 處理並行錯誤"""
    
    async def handle_parallel_tasks(self, tasks: List[Callable]) -> Dict[str, Any]:
        results = {}
        errors = []
        
        try:
            async with asyncio.TaskGroup() as tg:
                futures = {
                    task_name: tg.create_task(task())
                    for task_name, task in tasks.items()
                }
        except* EmbeddingError as eg:
            # 處理 embedding 相關錯誤
            for e in eg.exceptions:
                errors.append(("embedding", e))
        except* CacheError as eg:
            # 快取錯誤不應中斷流程
            for e in eg.exceptions:
                logger.warning(f"Cache error: {e}")
        
        # 收集成功的結果
        for name, future in futures.items():
            if not future.cancelled() and future.done():
                try:
                    results[name] = future.result()
                except Exception:
                    pass
        
        return results, errors
```

### 6.3 重試策略

```python
class RetryStrategy:
    """智能重試策略"""
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    async def execute_with_retry(self, func: Callable) -> Any:
        for attempt in range(self.max_retries):
            try:
                return await func()
            except RetryableError as e:
                if attempt == self.max_retries - 1:
                    raise
                
                delay = min(
                    self.base_delay * (2 ** attempt),
                    self.max_delay
                )
                await asyncio.sleep(delay)
```

## 7. 配置管理

### 7.1 配置層級

```
Environment Variables
│
├── Feature Flags
│   ├── ENABLE_CACHE
│   ├── ENABLE_PARALLEL_PROCESSING
│   └── ENABLE_DETAILED_MONITORING
│
├── Performance Tuning
│   ├── CACHE_TTL_MINUTES
│   ├── CONNECTION_POOL_SIZE
│   └── REQUEST_TIMEOUT_SECONDS
│
└── Business Logic
    ├── SIGMOID_X0
    ├── SIGMOID_K
    └── KEYWORD_MATCH_SETTINGS
```

### 7.2 動態配置

```python
class DynamicConfig:
    """支援熱更新的配置管理"""
    def __init__(self):
        self._config = self._load_initial_config()
        self._watchers = []
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)
    
    def watch(self, key: str, callback: Callable):
        """監聽配置變更"""
        self._watchers.append((key, callback))
    
    async def reload(self):
        """熱更新配置"""
        new_config = await self._fetch_latest_config()
        changes = self._diff_config(self._config, new_config)
        
        for key, value in changes.items():
            for watched_key, callback in self._watchers:
                if key == watched_key:
                    await callback(value)
```

## 8. 安全設計

### 8.1 輸入驗證層

```python
class InputValidator:
    """統一的輸入驗證"""
    async def validate_and_sanitize(self, request: Dict) -> Dict:
        # 1. 結構驗證
        validated = self._validate_structure(request)
        
        # 2. 內容清理
        sanitized = self._sanitize_content(validated)
        
        # 3. 安全檢查
        self._security_check(sanitized)
        
        return sanitized
    
    def _sanitize_content(self, data: Dict) -> Dict:
        """清理潛在的惡意內容"""
        # Remove script tags
        # Escape special characters
        # Validate URLs if any
        return cleaned_data
```

### 8.2 資料保護

- 快取使用 hash key，不存原始文本
- 日誌脫敏處理
- 錯誤訊息不洩露內部細節

## 9. 擴展性設計

### 9.1 插件架構

```python
class PluginManager:
    """支援功能擴展的插件管理"""
    def register_preprocessor(self, preprocessor: Preprocessor):
        """註冊文本預處理器"""
        
    def register_similarity_algorithm(self, algorithm: SimilarityAlgorithm):
        """註冊相似度算法"""
        
    def register_cache_backend(self, backend: CacheBackend):
        """註冊快取後端"""
```

### 9.2 版本管理

```python
class VersionedAPI:
    """API 版本管理"""
    def __init__(self):
        self.versions = {
            "v1": IndexCalculationV1(),
            "v2": IndexCalculationServiceV2()
        }
    
    async def process(self, version: str, request: Dict) -> Dict:
        handler = self.versions.get(version, self.versions["v2"])
        return await handler.process(request)
```

---

**文檔版本**: 1.0.0  
**建立日期**: 2025-08-02  
**架構師**: Claude Code + WenHao