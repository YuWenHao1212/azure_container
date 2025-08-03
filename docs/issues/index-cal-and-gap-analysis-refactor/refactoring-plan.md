# Index Calculation and Gap Analysis API 重構計劃

**文檔版本**: 1.0.0  
**建立日期**: 2025-08-03  
**狀態**: 規劃中  
**負責人**: WenHao + Claude Code

## 1. 執行摘要

### 1.1 重構目標
本次重構旨在優化 `/api/v1/index-cal-and-gap-analysis` API 的效能、可維護性和用戶體驗。這是一個組合型 API，同時執行履歷匹配指數計算和差距分析。

### 1.2 關鍵改進目標
- **效能提升**: 目標響應時間從 3-5 秒降至 2 秒以內（P95）
- **快取機制**: 實現智能快取，減少重複計算
- **並行優化**: 改善並行處理策略，最大化資源利用
- **錯誤處理**: 增強錯誤恢復能力，提升用戶體驗
- **可觀測性**: 建立完整的監控和追蹤機制

## 2. 現狀分析

### 2.1 當前架構
```
API Router (/api/v1/index-cal-and-gap-analysis)
    │
    ├─> IndexCalculationService (步驟 1)
    │   ├─> Embedding 生成（序列執行）
    │   └─> 關鍵字覆蓋分析
    │
    └─> GapAnalysisService (步驟 2)
        ├─> LLM 呼叫（GPT-4）
        └─> 重試機制（最多 3 次）
```

### 2.2 效能瓶頸分析

| 組件 | 當前耗時 | 瓶頸原因 | 優化潛力 |
|------|----------|----------|----------|
| **Embedding 生成** | 1-2 秒 | 無快取，每次重新計算 | 高（60-80%） |
| **Gap Analysis LLM** | 2-3 秒 | LLM 呼叫延遲，無快取 | 中（30-50%） |
| **序列執行** | +30% | Index 和 Gap 順序執行 | 中（20-30%） |
| **重試機制** | +2-8 秒 | 空欄位重試 | 低（需保留） |

### 2.3 主要問題

#### 效能問題
1. **無快取機制**：相同的履歷/職缺組合重複計算
2. **序列執行**：兩個服務按順序執行，未充分利用並行
3. **Embedding 重複計算**：沒有 embedding 快取
4. **LLM 呼叫成本高**：每次都呼叫 GPT-4，無結果快取

#### 架構問題
1. **服務耦合**：Gap Analysis 依賴 Index Calculation 的結果
2. **錯誤傳播**：一個服務失敗導致整體失敗
3. **監控不足**：缺乏詳細的效能分解
4. **配置分散**：參數分散在多個地方

#### 用戶體驗問題
1. **響應時間長**：3-5 秒的等待時間
2. **錯誤資訊不清晰**：通用錯誤訊息
3. **無進度回饋**：長時間等待無狀態更新

## 3. 重構設計

### 3.1 目標架構
```
API Router (Enhanced)
    │
    ├─> CacheManager (新增)
    │   └─> 檢查快取（履歷+職缺 hash）
    │
    ├─> ParallelExecutor (新增)
    │   ├─> IndexCalculationServiceV2
    │   │   ├─> Embedding Cache
    │   │   └─> 並行 Embedding 生成
    │   │
    │   └─> GapAnalysisServiceV2
    │       ├─> Prompt Cache
    │       └─> Result Cache
    │
    └─> ResponseAggregator (新增)
        └─> 統一錯誤處理和監控
```

### 3.2 核心改進策略

#### 3.2.1 智能快取系統
```python
class CombinedAnalysisCache:
    """組合分析的智能快取"""
    
    def __init__(self):
        self.index_cache = LRUCache(max_size=1000, ttl_minutes=60)
        self.gap_cache = LRUCache(max_size=500, ttl_minutes=30)
        self.embedding_cache = LRUCache(max_size=2000, ttl_minutes=120)
    
    def get_cache_key(self, resume: str, job_desc: str, keywords: List[str]) -> str:
        """生成穩定的快取鍵"""
        normalized_resume = self._normalize_text(resume)
        normalized_jd = self._normalize_text(job_desc)
        normalized_keywords = sorted([k.lower() for k in keywords])
        
        cache_input = f"{normalized_resume}|{normalized_jd}|{','.join(normalized_keywords)}"
        return hashlib.sha256(cache_input.encode()).hexdigest()
```

#### 3.2.2 並行處理優化
```python
async def parallel_analysis(self, request: AnalysisRequest):
    """並行執行 Index 和 Gap 的預處理部分"""
    
    async with asyncio.TaskGroup() as tg:
        # 並行執行不相依的部分
        embedding_task = tg.create_task(
            self._generate_embeddings_cached(request.resume, request.job_description)
        )
        
        # Gap Analysis 的 prompt 準備可以並行
        prompt_task = tg.create_task(
            self._prepare_gap_prompt(request)
        )
        
        # 關鍵字標準化也可以並行
        keyword_task = tg.create_task(
            self._standardize_keywords(request.keywords)
        )
    
    # 使用並行結果進行後續計算
    embeddings = embedding_task.result()
    gap_prompt = prompt_task.result()
    standardized_keywords = keyword_task.result()
```

#### 3.2.3 分階段執行策略
```python
class PhaseExecutor:
    """分階段執行以支援進度回饋"""
    
    async def execute_with_progress(self, request):
        phases = [
            ("preprocessing", self._preprocess, 10),
            ("embedding_generation", self._generate_embeddings, 30),
            ("index_calculation", self._calculate_index, 20),
            ("gap_analysis", self._analyze_gap, 35),
            ("finalization", self._finalize_results, 5)
        ]
        
        total_progress = 0
        results = {}
        
        for phase_name, phase_func, weight in phases:
            start_time = time.time()
            
            # 執行階段
            result = await phase_func(request, results)
            results[phase_name] = result
            
            # 更新進度
            total_progress += weight
            await self._notify_progress(phase_name, total_progress)
            
            # 記錄階段耗時
            self._track_phase_time(phase_name, time.time() - start_time)
        
        return results
```

### 3.3 服務重構詳細設計

#### 3.3.1 IndexCalculationServiceV2
```python
class IndexCalculationServiceV2:
    """增強版指數計算服務"""
    
    def __init__(self):
        self.embedding_cache = EmbeddingCache()
        self.result_cache = ResultCache()
        self.parallel_executor = ParallelExecutor()
    
    async def calculate_index_optimized(self, request: IndexRequest):
        # 1. 檢查結果快取
        cache_key = self._get_cache_key(request)
        if cached := self.result_cache.get(cache_key):
            return cached
        
        # 2. 並行生成 embeddings（帶快取）
        embeddings = await self._get_embeddings_parallel(
            request.resume,
            request.job_description
        )
        
        # 3. 計算相似度和關鍵字覆蓋（可並行）
        async with asyncio.TaskGroup() as tg:
            similarity_task = tg.create_task(
                self._compute_similarity(embeddings)
            )
            coverage_task = tg.create_task(
                self._analyze_keyword_coverage(request)
            )
        
        # 4. 組合結果並快取
        result = {
            "similarity": similarity_task.result(),
            "coverage": coverage_task.result()
        }
        
        self.result_cache.set(cache_key, result)
        return result
```

#### 3.3.2 GapAnalysisServiceV2
```python
class GapAnalysisServiceV2:
    """增強版差距分析服務"""
    
    def __init__(self):
        self.prompt_cache = PromptCache()
        self.result_cache = ResultCache()
        self.retry_strategy = SmartRetryStrategy()
    
    async def analyze_gap_optimized(self, request: GapRequest):
        # 1. 智能快取檢查
        cache_key = self._get_cache_key(request)
        if cached := self.result_cache.get(cache_key):
            return cached
        
        # 2. 優化的 prompt 準備
        prompt = await self._prepare_optimized_prompt(request)
        
        # 3. 智能重試策略
        result = await self.retry_strategy.execute(
            self._call_llm_with_validation,
            prompt,
            max_attempts=3,
            validation_func=self._validate_gap_response
        )
        
        # 4. 後處理和快取
        processed_result = self._post_process(result)
        self.result_cache.set(cache_key, processed_result)
        
        return processed_result
```

### 3.4 監控與可觀測性增強

#### 3.4.1 詳細的時間追蹤
```python
class PerformanceTracker:
    """效能追蹤器"""
    
    def track_operation(self, operation_name: str):
        return OperationContext(operation_name, self)
    
    class OperationContext:
        def __init__(self, name: str, tracker):
            self.name = name
            self.tracker = tracker
            self.start_time = time.time()
            self.checkpoints = []
        
        def checkpoint(self, name: str):
            elapsed = time.time() - self.start_time
            self.checkpoints.append((name, elapsed))
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            total_time = time.time() - self.start_time
            self.tracker.record_operation(
                self.name,
                total_time,
                self.checkpoints
            )
```

#### 3.4.2 業務指標收集
```python
class BusinessMetrics:
    """業務指標收集器"""
    
    def track_analysis_request(self, request_data: dict):
        metrics = {
            "resume_length": len(request_data["resume"]),
            "jd_length": len(request_data["job_description"]),
            "keywords_count": len(request_data["keywords"]),
            "language": request_data.get("language", "en"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 發送到監控系統
        monitoring_service.track_event("CombinedAnalysisRequest", metrics)
    
    def track_analysis_result(self, result_data: dict, processing_time: float):
        metrics = {
            "similarity_score": result_data["similarity_percentage"],
            "keyword_coverage": result_data["keyword_coverage"]["coverage_percentage"],
            "gaps_identified": len(result_data["gap_analysis"]["KeyGaps"]),
            "processing_time_ms": processing_time * 1000,
            "cache_hit": result_data.get("cache_hit", False)
        }
        
        monitoring_service.track_event("CombinedAnalysisResult", metrics)
```

## 4. 實施計劃

### 4.1 Phase 1: 基礎架構準備（第 1-2 天）
- [ ] 建立快取基礎設施
- [ ] 實作 embedding 快取層
- [ ] 設計監控架構
- [ ] 建立效能基準測試

### 4.2 Phase 2: 服務重構（第 3-5 天）
- [ ] 重構 IndexCalculationService → V2
- [ ] 重構 GapAnalysisService → V2
- [ ] 實作並行執行器
- [ ] 整合快取系統

### 4.3 Phase 3: API 層優化（第 6-7 天）
- [ ] 重構 API router
- [ ] 實作進度回饋機制
- [ ] 增強錯誤處理
- [ ] 優化回應格式

### 4.4 Phase 4: 測試與調優（第 8-10 天）
- [ ] 單元測試（目標覆蓋率 > 90%）
- [ ] 整合測試
- [ ] 效能測試
- [ ] 負載測試

### 4.5 Phase 5: 部署與監控（第 11-12 天）
- [ ] 準備部署文檔
- [ ] 設定監控 dashboard
- [ ] 漸進式部署
- [ ] 效能驗證

## 5. 風險評估與緩解

### 5.1 技術風險
| 風險 | 影響 | 機率 | 緩解策略 |
|------|------|------|----------|
| 快取一致性問題 | 高 | 中 | 實作快取失效機制和版本控制 |
| 並行執行錯誤 | 高 | 低 | 完整的錯誤隔離和 fallback 機制 |
| 記憶體使用增加 | 中 | 高 | 實作快取大小限制和 LRU 策略 |
| API 相容性問題 | 高 | 低 | 保持向後相容，版本化 API |

### 5.2 業務風險
| 風險 | 影響 | 機率 | 緩解策略 |
|------|------|------|----------|
| 暫時性能下降 | 中 | 低 | 金絲雀部署，快速回滾機制 |
| 用戶體驗中斷 | 高 | 低 | A/B 測試，漸進式切換 |
| 成本增加 | 低 | 中 | 監控資源使用，優化配置 |

## 6. 成功指標

### 6.1 效能指標
- **P50 響應時間**: < 1.5 秒（目前 2-3 秒）
- **P95 響應時間**: < 2 秒（目前 3-5 秒）
- **P99 響應時間**: < 3 秒（目前 5-8 秒）
- **快取命中率**: > 40%（新增指標）

### 6.2 品質指標
- **錯誤率**: < 0.1%（維持現有水平）
- **Gap Analysis 完整性**: > 95%（目前 90%）
- **測試覆蓋率**: > 90%（新增要求）

### 6.3 業務指標
- **API 呼叫成本降低**: 30-40%（通過快取）
- **用戶滿意度**: 提升 20%（通過更快響應）
- **並發處理能力**: 提升 50%（通過優化）

## 7. 技術決策記錄

### 7.1 為什麼選擇 LRU 快取？
- **優點**：自動淘汰舊資料，記憶體使用可控
- **缺點**：可能淘汰熱門但暫時未使用的資料
- **決策**：配合 TTL 使用，平衡記憶體和命中率

### 7.2 為什麼保留序列依賴？
- **原因**：Gap Analysis 需要 Index Calculation 的關鍵字覆蓋結果
- **優化**：將可並行的部分提前執行
- **未來**：考慮完全解耦兩個服務

### 7.3 為什麼不使用 Redis？
- **考量**：當前規模下，記憶體快取足夠
- **優點**：減少網路開銷，降低複雜度
- **未來**：規模擴大時可遷移到 Redis

## 8. 相關文檔

### 內部文檔
- [Index Calculation V2 重構經驗](../index-calculation-v2-refactor/README.md)
- [API 架構設計](../../ARCHITECTURE.md)
- [測試規格](../../../test/TEST_SPEC.md)

### 外部參考
- [Azure Container Apps 最佳實踐](https://docs.microsoft.com/azure/container-apps)
- [FastAPI 效能優化指南](https://fastapi.tiangolo.com/deployment/concepts/)
- [Python 3.11 並行處理](https://docs.python.org/3.11/library/asyncio-task.html)

## 9. 附錄

### 附錄 A: 效能測試基準
```python
# 基準測試腳本
async def benchmark_combined_api():
    test_cases = [
        ("small", small_resume, small_jd, 5),
        ("medium", medium_resume, medium_jd, 10),
        ("large", large_resume, large_jd, 20)
    ]
    
    results = {}
    for name, resume, jd, keywords_count in test_cases:
        times = []
        for _ in range(10):
            start = time.time()
            await call_api(resume, jd, generate_keywords(keywords_count))
            times.append(time.time() - start)
        
        results[name] = {
            "p50": np.percentile(times, 50),
            "p95": np.percentile(times, 95),
            "p99": np.percentile(times, 99)
        }
    
    return results
```

### 附錄 B: 快取配置建議
```yaml
cache_config:
  embedding_cache:
    max_size: 2000
    ttl_minutes: 120
    eviction_policy: lru
  
  index_result_cache:
    max_size: 1000
    ttl_minutes: 60
    eviction_policy: lru
  
  gap_analysis_cache:
    max_size: 500
    ttl_minutes: 30
    eviction_policy: lru
  
  combined_result_cache:
    max_size: 300
    ttl_minutes: 15
    eviction_policy: lru
```

---

**文檔結束**