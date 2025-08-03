# Index Calculation and Gap Analysis V2 技術文檔

**文檔版本**: 1.0.0  
**建立日期**: 2025-08-03  
**狀態**: 規劃中

## 1. 專案概述 

Index Calculation and Gap Analysis V2 是 AI Resume Advisor 平台的組合服務升級版本，負責同時執行履歷匹配度計算和差距分析。本次升級將整合使用已經優化過的 IndexCalculationServiceV2，該服務已實現快取機制、並行處理和效能優化。  

### 1.1 為什麼需要重構？

#### V1 版本的效能問題
1. **響應時間過長**
   - 平均響應時間：5-8 秒
   - P95 響應時間：> 12 秒
   - 主要瓶頸：序列執行兩個服務，無快取機制

2. **重複計算** (已在 IndexCalculationServiceV2 中解決)
   - V2 版本已實現 embedding 快取機制
   - 使用 LRU 快取避免重複生成
   - 大幅減少 Azure OpenAI API 呼叫

3. **重試機制效率低**
   - Gap analysis 重試延遲累積（2-8 秒）
   - 無智能重試策略
   - 空欄位重試浪費資源

#### V1 版本的架構問題
1. **服務耦合**
   - 兩個服務完全獨立執行
   - 無法共享中間結果
   - 缺乏統一的錯誤處理

2. **缺乏並行處理**
   - 嚴格序列執行
   - Index 完成後才開始 gap analysis
   - 浪費等待時間

3. **監控盲點**
   - 無法追蹤個別服務耗時
   - 缺乏整體效能指標
   - 難以定位瓶頸

#### 重構的必要性和目標
1. **業務需求驅動**
   - 用戶期望 < 3 秒的響應時間
   - 需要支援批量處理
   - 降低 API 呼叫成本

2. **技術改進目標**
   - P50 < 2 秒，P95 < 4 秒，P99 < 6 秒
   - 整體快取效益：減少重複 embedding 生成 (實際命中率需根據使用模式評估) 
   - API 呼叫減少 50%+

### 1.2 關鍵改進
- **效能提升**: 預期 P50 1.5秒，P95 3秒（比現有快 60-75%）
- **共享快取**: 實現 embedding 和結果共享
- **並行處理**: 部分並行執行，減少等待時間
- **智能重試**: 基於錯誤類型的自適應重試
- **統一監控**: 完整的效能追蹤和分析

### 1.3 部署資訊
- **生產環境**: https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io
- **API 端點**: POST /api/v1/index-cal-and-gap-analysis-v2
- **容器映像**: 計劃中

## 2. 系統架構

### 2.1 整體架構

```
┌─────────────────────────────────────────────────────────────┐
│                    Container Apps Ingress                    │
│                  (內建負載平衡，自動擴展)                   │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                     FastAPI Application                      │
│                    (原生執行，無冷啟動)                     │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│          Index Calculation and Gap Analysis Router          │
│  POST /api/v1/index-cal-and-gap-analysis-v2                │
│  - 請求驗證 (Pydantic)                                     │
│  - 錯誤處理與回復                                          │
│  - 回應格式化 (Bubble.io 相容)                            │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│              CombinedAnalysisServiceV2                      │
│                                                              │
│  ┌────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Shared Cache   │  │ Orchestrator    │  │ Monitoring   │ │
│  │ Manager        │  │ Engine          │  │ Collector    │ │
│  │                │  │                 │  │              │ │
│  └────────┬───────┘  └────────┬────────┘  └──────┬───────┘ │
│           │                    │                   │         │
│  ┌────────▼────────────────────▼───────────────────▼──────┐ │
│  │                    服務協調層                           │ │
│  │  ┌─────────────────┐  ┌─────────────────┐             │ │
│  │  │ IndexCalculation│  │ GapAnalysis     │             │ │
│  │  │ ServiceV2       │  │ ServiceV2       │             │ │
│  │  │ (現有優化版本) │  │                 │             │ │
│  │  │ - 資源池管理   │  │ - 智能重試     │             │ │
│  │  │ - 並行處理     │  │ - 串流處理     │             │ │
│  │  │ - 效能監控     │  │ - 增量分析     │             │ │
│  │  └─────────────────┘  └─────────────────┘             │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                   外部服務整合                               │
│  ┌──────────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Azure OpenAI     │  │ Application  │  │ Redis Cache  │  │
│  │ (Japan East)     │  │ Insights     │  │ (計劃中)    │  │
│  └──────────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 資料流程

```
用戶請求
    │
    ▼
輸入驗證 ──→ [驗證失敗] ──→ 400 Bad Request
    │
    ▼
資源池檢查 ──→ [可用客戶端] ──→ 直接執行（無初始化延遲）
    │
    └──→ [需要初始化]
            │
            ▼
        並行預處理
        ├─→ 差異化文本處理：
        │   - Embedding (Index Calculation): 使用 clean_html_text 清理 HTML
        │   - LLM (Gap Analysis): 保留原始 HTML 結構以提供更多上下文 
        ├─→ 語言偵測
        └─→ 關鍵字解析
            │
            ▼
        智能執行策略
        ├─→ [共享 Embedding 生成]
        │       │
        │       ▼
        │   Index Calculation (使用共享 embedding)
        │       │
        └───────┤
                │
                ▼
            Gap Analysis
            ├─→ 使用 index 結果作為輸入
            │   - 已匹配關鍵字（分析優勢）
            │   - 缺失關鍵字（識別差距）
            ├─→ 智能 prompt 優化
            └─→ 自適應重試
                │
                ▼
            結果聚合
                │
                ▼
            返還資源池客戶端
                │
                ▼
            返回組合結果
```

### 2.3 服務依賴關係說明

#### Gap Analysis 為何需要 Index Calculation 結果？

1. **關鍵字匹配資訊**
   - `matched_keywords`: 用於識別候選人優勢
   - `missing_keywords`: 用於分析技能差距
   - 確保兩個服務的分析基於相同的關鍵字匹配結果

2. **避免重複計算**
   - Index Calculation 已完成關鍵字分析
   - Gap Analysis 直接使用結果，無需重新計算
   - 保持結果一致性

3. **提供分析上下文**
   - LLM 可基於具體的匹配/缺失關鍵字提供更精確的建議
   - 量化資料（匹配率）輔助質性分析（優勢/差距）

### 2.4 V1 vs V2 架構對比

| 層面 | V1 (原始版本) | V2 (重構版本) | 改進效果 |
|------|--------------|--------------|----------|
| **服務架構** | 兩個獨立服務序列執行 | 統一協調服務 | 減少 40% 執行時間 |
| **快取機制** | ❌ 無快取 | ✅ 資源池管理 | 減少初始化開銷 90% |
| **Embedding** | 重複計算 | 共享計算結果 | 減少 50% API 呼叫 |
| **並行處理** | ❌ 嚴格序列 | ✅ 智能並行 | 節省 30% 時間 |
| **重試策略** | 固定延遲 | 自適應重試 | 減少 60% 重試時間 |
| **錯誤處理** | 各自處理 | 統一錯誤處理 | 更好的錯誤恢復 |
| **監控指標** | 分散日誌 | 統一監控 | 完整可觀測性 |
| **資源使用** | 峰值 3GB | 優化至 2GB | 減少 33% 記憶體 |

### 2.4 效能對比

```
V1 效能基準:
┌─────────────────────────────────────┐
│ Index Calculation: 3-4s             │
│ Gap Analysis: 3-5s                  │
│ 重試延遲: 2-8s                     │
│ 總響應時間: 6-12s                  │
└─────────────────────────────────────┘

V2 效能提升:
┌─────────────────────────────────────┐
│ 共享 Embedding: 1-1.5s              │
│ Index (無初始化延遲): < 500ms      │
│ Gap Analysis: 1.5-2s                │
│ 智能重試: 0.5-2s                   │
│ 總響應時間: 1.5-4s                 │
└─────────────────────────────────────┘
```

## 3. API 規格

### 3.1 請求端點
```
POST /api/v1/index-cal-and-gap-analysis-v2
Content-Type: application/json
```

### 3.2 請求格式
```json
{
  "resume": "string (HTML 或純文字，100-30000 字元)",
  "job_description": "string (HTML 或純文字，50-30000 字元)",
  "keywords": ["string"] 或 "comma,separated,string",
  "language": "auto|en|zh-TW",  // 可選，預設 auto
  "analysis_options": {          // 可選，分析選項
    "include_skill_priorities": true,
    "max_improvements": 5,
    "focus_areas": ["technical", "experience", "soft_skills"]
  }
}
```

### 3.3 回應格式 (Bubble.io 相容)

V2 API 保持向後相容，但將結果結構化以便未來擴展：

```json
{
  "success": true,
  "data": {
    // V2 保持向後相容，但提供更詳細的結構
    "raw_similarity_percentage": 65,  // 保持向後相容
    "similarity_percentage": 75,      // 保持向後相容
    "keyword_coverage": {             // 保持向後相容
      "total_keywords": 20,
      "covered_count": 15,
      "coverage_percentage": 75,
      "covered_keywords": ["Python", "FastAPI"],
      "missed_keywords": ["Kubernetes", "GraphQL"]
    },
    "gap_analysis": {                 // 保持向後相容
      "CoreStrengths": "<ol><li>Strong Python backend expertise with FastAPI framework</li><li>8+ years of software engineering experience exceeding requirements</li><li>Leadership experience managing development teams</li></ol>",
      "KeyGaps": "<ol><li>Missing React frontend development experience</li><li>No demonstrated Kubernetes container orchestration skills</li><li>Lack of AWS cloud platform experience</li></ol>",
      "QuickImprovements": "<ol><li>Add specific React projects or mention any frontend JavaScript experience</li><li>Include Docker experience and mention any container-related work</li></ol>",
      "OverallAssessment": "<p>The candidate shows strong backend development skills with 60% higher experience than required. However, significant gaps exist in frontend (React), DevOps (Kubernetes, CI/CD), and cloud (AWS) technologies.</p>",
      "SkillSearchQueries": [
        {
          "skill_name": "React",
          "skill_category": "TECHNICAL",
          "description": "Frontend framework for building interactive user interfaces required for full-stack role"
        }
      ]
    },
    
    // V2 新增欄位（可選）
    "processing_time_ms": 2500,
    "cache_hit": false,
    "service_timings": {
      "embedding_generation_ms": 1200,
      "index_calculation_ms": 150,
      "gap_analysis_ms": 1100,
      "total_ms": 2500
    }
  },
  "error": {
    "code": "",
    "message": "",
    "details": ""
  },
  "timestamp": "2025-08-03T10:30:00.000Z"
}
```

### 3.4 錯誤回應
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "PARTIAL_FAILURE",
    "message": "Gap analysis failed after retries, returning index calculation only",
    "details": {
      "completed_services": ["index_calculation"],
      "failed_services": ["gap_analysis"],
      "partial_data": {
        "index_calculation": { /* 部分結果 */ }
      }
    }
  },
  "timestamp": "2025-08-03T10:30:00.000Z"
}
```

## 4. 核心實作

### 4.1 統一服務類別

```python
class CombinedAnalysisServiceV2(BaseService):
    """
    統一的分析服務，協調 index calculation 和 gap analysis。
    利用現有的 IndexCalculationServiceV2 及其所有優化特性。
    """
    
    def __init__(
        self,
        index_service: IndexCalculationServiceV2 = None,
        gap_service: GapAnalysisServiceV2 = None,
        enable_cache: bool = True,
        cache_ttl_minutes: int = 60,
        enable_partial_results: bool = True
    ):
        # 服務依賴 - 使用現有優化版本
        self.index_service = index_service or get_index_calculation_service_v2()
        self.gap_service = gap_service or GapAnalysisServiceV2()
        
        # 共享快取
        self.shared_cache = SharedCacheManager(
            ttl_minutes=cache_ttl_minutes,
            max_size=2000
        )
        
        # 配置
        self.enable_partial_results = enable_partial_results
        
        # 統計
        self.analysis_stats = {
            "total_analyses": 0,
            "full_success": 0,
            "partial_success": 0,
            "complete_failures": 0,
            "average_processing_time_ms": 0.0
        }
```

### 4.2 快取策略優化

#### 4.2.1 利用現有 IndexCalculationServiceV2 快取
```python
class CombinedAnalysisServiceV2:
    """
    重點：直接使用 IndexCalculationServiceV2 的內建快取機制。
    主要快取場景：
    1. 同一用戶短時間內多次調整同一份履歷
    2. 批量處理相同職缺的多份履歷
    3. A/B 測試不同版本的履歷
    """
    
    async def execute_analysis(self, request):
        # IndexCalculationServiceV2 會自動處理快取
        # - Embedding 快取 (TTL: 120 分鐘)
        # - 結果快取 (TTL: 60 分鐘)
        index_result = await self.index_service.calculate_index(
            resume=request.resume,
            job_description=request.job_description,
            keywords=request.keywords
        )
```

#### 4.2.2 優化執行流程
```python
async def execute_combined_analysis(
    self,
    resume: str,
    job_description: str,
    keywords: List[str]
) -> Dict[str, Any]:
    """執行組合分析，充分利用 IndexCalculationServiceV2 的優化。"""
    
    # Step 1: 利用 IndexCalculationServiceV2 的快取和優化
    # 服務內部會自動處理：
    # - Embedding 快取檢查
    # - 並行 embedding 生成
    # - 結果快取
    index_result = await self.index_service.calculate_index(
        resume=resume,
        job_description=job_description,
        keywords=keywords,
        include_timing=True  # 獲取詳細時間分解
    )
    
    # Step 2: 基於 index 結果執行 gap analysis
    # 考慮差異化文本處理策略
    gap_result = await self.gap_service.analyze_gap(
        # 可能保留 HTML 給 LLM
        job_description=job_description,  
        resume=resume,
        job_keywords=keywords,
        matched_keywords=index_result["keyword_coverage"]["covered_keywords"],
        missing_keywords=index_result["keyword_coverage"]["missed_keywords"],
        language=request.language
    )
    
    return self._combine_results(index_result, gap_result)
```

### 4.3 智能重試策略

```python
class AdaptiveRetryStrategy:
    """自適應重試策略。"""
    
    def __init__(self):
        self.retry_configs = {
            "empty_fields": {
                "max_attempts": 2,
                "delays": [1.0, 2.0],
                "backoff": "linear"
            },
            "timeout": {
                "max_attempts": 3,
                "delays": [0.5, 1.0, 2.0],
                "backoff": "exponential"
            },
            "rate_limit": {
                "max_attempts": 3,
                "delays": [5.0, 10.0, 20.0],
                "backoff": "exponential"
            }
        }
    
    async def execute_with_retry(
        self,
        func: Callable,
        error_classifier: Callable
    ) -> Any:
        """使用自適應策略執行重試。"""
        
        last_error = None
        total_attempts = 0
        
        while total_attempts < self.get_max_attempts():
            try:
                return await func()
            except Exception as e:
                error_type = error_classifier(e)
                config = self.retry_configs.get(error_type, self.retry_configs["timeout"])
                
                if total_attempts >= config["max_attempts"]:
                    raise
                
                delay = self._calculate_delay(config, total_attempts)
                await asyncio.sleep(delay)
                
                total_attempts += 1
                last_error = e
        
        raise last_error
```

### 4.4 部分結果處理

```python
async def analyze_with_fallback(
    self,
    request: AnalysisRequest
) -> AnalysisResponse:
    """執行分析，支援部分結果返回。"""
    
    results = {
        "index_calculation": None,
        "gap_analysis": None,
        "errors": []
    }
    
    try:
        # 嘗試執行完整分析
        full_result = await self._execute_full_analysis(request)
        return AnalysisResponse(success=True, data=full_result)
        
    except Exception as e:
        # 如果啟用部分結果
        if self.enable_partial_results:
            # 至少嘗試返回 index calculation
            try:
                results["index_calculation"] = await self.index_service.calculate_index(
                    request.resume,
                    request.job_description,
                    request.keywords
                )
                
                return AnalysisResponse(
                    success=False,
                    data=results,
                    error={
                        "code": "PARTIAL_FAILURE",
                        "message": "部分服務失敗，返回可用結果",
                        "details": str(e)
                    }
                )
            except Exception as index_error:
                results["errors"].append(str(index_error))
        
        # 完全失敗
        raise
```

### 4.5 效能監控整合

```python
class PerformanceMonitor:
    """統一效能監控。"""
    
    def __init__(self):
        self.metrics = defaultdict(lambda: {
            "count": 0,
            "total_time": 0.0,
            "min_time": float('inf'),
            "max_time": 0.0,
            "errors": 0
        })
    
    @contextmanager
    def track_operation(self, operation_name: str):
        """追蹤操作效能。"""
        start_time = time.time()
        
        try:
            yield
            success = True
        except Exception:
            success = False
            self.metrics[operation_name]["errors"] += 1
            raise
        finally:
            elapsed = (time.time() - start_time) * 1000
            
            metric = self.metrics[operation_name]
            metric["count"] += 1
            metric["total_time"] += elapsed
            metric["min_time"] = min(metric["min_time"], elapsed)
            metric["max_time"] = max(metric["max_time"], elapsed)
            
            # 發送到 Application Insights
            if success:
                self._send_telemetry(operation_name, elapsed)
```

### 4.6 HTML 處理策略分析

#### 差異化處理的理由

1. **Embedding 計算需要純文本**
   - Embedding 模型在純文本上表現最佳
   - HTML 標籤會增加噪音，降低語義相似度計算的準確性
   - 清理後的文本更能準確反映內容的語義

2. **LLM 可能受益於 HTML 結構**
   - HTML 標籤提供文檔結構資訊（如標題層級、列表、強調等）
   - GPT-4 能理解並利用 HTML 結構進行更好的分析
   - 結構化資訊有助於識別重要內容和層次關係

#### 建議的實作方式

```python
class CombinedAnalysisServiceV2:
    async def process_texts(self, resume: str, job_description: str):
        # For Index Calculation (Embeddings)
        clean_resume = clean_html_text(resume)
        clean_jd = clean_html_text(job_description)
        
        # For Gap Analysis (LLM)
        # 保留原始 HTML，但可能需要基本清理（如移除 script/style 標籤）
        llm_resume = self.sanitize_html_for_llm(resume)
        llm_jd = self.sanitize_html_for_llm(job_description)
        
        return {
            "embedding_texts": (clean_resume, clean_jd),
            "llm_texts": (llm_resume, llm_jd)
        }
```

### 4.7 Gap Analysis V2 技術細節

```python
class GapAnalysisServiceV2(GapAnalysisService):
    """
    升級版 Gap Analysis 服務。
    
    主要改進：
    1. 使用 gpt-4.1-japan 模型（部署在 Japan East）
    2. 利用 index 結果作為上下文
    3. 智能 prompt 優化
    4. 支援技能優先級分析
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.llm_model = "gpt-4.1-japan"  # 使用 Japan East 部署
        self.enable_context_enhancement = True
        self.enable_skill_priorities = True
```

#### 關鍵技術特點

1. **LLM 模型配置**
   - 模型：`gpt-4.1-japan`
   - 部署區域：Japan East
   - API 版本：`2025-01-01-preview`
   - 溫度設定：0.3（降低以提高一致性）

2. **輸入處理**
   - HTML 清理：使用 `clean_html_text` 函數
   - 文本長度限制：履歷 30KB、職缺 30KB
   - 語言支援：en、zh-TW

3. **上下文增強**
   - 利用 index 計算結果提供額外上下文
   - 包括匹配分數、關鍵字覆蓋率等
   - 提升分析的精確度和相關性

## 5. 效能指標與監控

### 5.0 輕量級監控策略

遵循 Keyword Extraction 和 Index Calculation V2 的成功模式，採用輕量級監控：

```python
# 環境變數配置
LIGHTWEIGHT_MONITORING=true  # 生產環境預設
MONITORING_ENABLED=true      # 啟用 Application Insights

# 輕量級監控原則
if os.getenv('LIGHTWEIGHT_MONITORING', 'true').lower() == 'true':
    # 只追蹤關鍵業務指標
    monitoring_service.track_event(
        "IndexCalAndGapAnalysisV2Completed",
        {
            "success": True,
            "processing_time_ms": total_time_ms,
            "has_partial_result": partial_result,
            "version": "v2"
        }
    )
else:
    # 開發/測試環境的詳細監控
    monitoring_service.track_event(
        "IndexCalAndGapAnalysisV2Detailed",
        {
            "success": True,
            "processing_time_ms": total_time_ms,
            "timing_breakdown": timing_breakdown,
            "cache_stats": cache_stats,
            "service_breakdown": service_times,
            "version": "v2"
        }
    )
```

**輕量級監控優點**：
- 減少 Application Insights 資料量和成本
- 降低監控對效能的影響
- 專注於關鍵業務指標
- 保持故障排查能力

### 5.1 效能目標

| 指標 | 目標值 | 預期實測值 | 改善幅度 |
|------|--------|-----------|----------|
| **P50 響應時間** | < 2秒 | 1.5秒 | -75% |
| **P95 響應時間** | < 4秒 | 3秒 | -75% |
| **P99 響應時間** | < 4秒 | 3.5秒 | -71% |
| **快取效益** | 減少重複計算 | 視使用模式 | N/A |
| **部分成功率** | > 95% | 98% | N/A |
| **API 呼叫減少** | > 50% | 60% | -60% |

### 5.2 監控端點（僅在開發環境啟用）

```
GET /api/v1/index-cal-and-gap-analysis-v2/stats
```

回應範例：
```json
{
  "service_name": "CombinedAnalysisServiceV2",
  "uptime_seconds": 7200,
  "analysis_stats": {
    "total_analyses": 2500,
    "full_success": 2400,
    "partial_success": 95,
    "complete_failures": 5,
    "success_rate": 0.98,
    "average_processing_time_ms": 1850
  },
  "cache_performance": {
    "embedding_hit_rate": 0.85,
    "index_hit_rate": 0.75,
    "gap_hit_rate": 0.65,
    "combined_hit_rate": 0.45,
    "api_calls_saved": 3200
  },
  "service_breakdown": {
    "embedding_generation": {
      "avg_ms": 1200,
      "p95_ms": 1800
    },
    "index_calculation": {
      "avg_ms": 150,
      "p95_ms": 300
    },
    "gap_analysis": {
      "avg_ms": 1500,
      "p95_ms": 2500
    }
  }
}
```

## 6. 錯誤處理

### 6.1 錯誤分類與恢復

| 錯誤類型 | 處理策略 | 恢復機制 |
|----------|----------|----------|
| Embedding 失敗 | 重試 3 次 | 降級至基本匹配 |
| Index 計算失敗 | 重試 2 次 | 返回錯誤 |
| Gap Analysis 失敗 | 智能重試 | 返回部分結果 |
| 超時錯誤 | 快速重試 | 調整超時設定 |
| 速率限制 | 指數退避 | 排隊處理 |

### 6.2 降級策略

```python
class DegradationStrategy:
    """服務降級策略。"""
    
    async def execute_with_degradation(self, request):
        try:
            # 嘗試完整服務
            return await self.full_service(request)
        except EmbeddingServiceError:
            # 降級：使用關鍵字匹配
            return await self.keyword_based_analysis(request)
        except GapAnalysisError:
            # 降級：只返回 index
            return await self.index_only_analysis(request)
        except Exception:
            # 最終降級：返回基本統計
            return self.basic_statistics(request)
```

## 7. 配置管理

### 7.1 環境變數

```bash
# 服務配置
COMBINED_ANALYSIS_CACHE_ENABLED=true
COMBINED_ANALYSIS_CACHE_TTL_MINUTES=60
COMBINED_ANALYSIS_ENABLE_PARTIAL_RESULTS=true

# 共享配置
SHARED_EMBEDDING_CACHE_SIZE=1000
SHARED_RESULT_CACHE_SIZE=500

# LLM 模型配置
AZURE_OPENAI_GPT4_DEPLOYMENT=gpt-4.1-japan
AZURE_OPENAI_ENDPOINT=https://airesumeadvisor.openai.azure.com
AZURE_OPENAI_API_VERSION=2025-01-01-preview

# 文本長度限制
MAX_RESUME_LENGTH=30000  # 30KB
MAX_JOB_DESCRIPTION_LENGTH=30000  # 30KB

# 重試配置
ADAPTIVE_RETRY_ENABLED=true
MAX_RETRY_DELAY_SECONDS=20

# 效能配置
ENABLE_PERFORMANCE_MONITORING=true
ENABLE_DISTRIBUTED_TRACING=true
```

## 8. 測試計畫

### 8.1 測試覆蓋目標

| 測試類型 | 目標覆蓋率 | 重點領域 |
|----------|-----------|----------|
| 單元測試 | > 90% | 核心邏輯、快取機制 |
| 整合測試 | > 85% | 服務協調、錯誤處理 |
| 效能測試 | 100% | 響應時間、並發處理 |
| 降級測試 | 100% | 部分失敗場景 |

### 8.2 關鍵測試案例

- **快取共享測試**: 驗證 embedding 重用
- **部分結果測試**: 確認降級機制
- **並發處理測試**: 50 QPS 負載測試
- **重試策略測試**: 各種錯誤場景
- **記憶體使用測試**: 長時間運行穩定性

## 9. 部署與運維

### 9.1 分階段部署

1. **Phase 1**: 內部測試（1 週）
   - 功能完整性驗證
   - 效能基準測試

2. **Phase 2**: 金絲雀部署（1 週）
   - 10% 流量導向新版本
   - 監控關鍵指標

3. **Phase 3**: 完整部署
   - 100% 流量切換
   - 舊版本保留備用

### 9.2 監控告警

- 響應時間 > 5 秒：警告
- 錯誤率 > 1%：警告
- 快取命中率 < 50%：通知
- 記憶體使用 > 80%：警告

## 10. 安全考量

- 輸入驗證和清理
- 快取鍵加密（防止資料洩露）
- 錯誤訊息脫敏
- API 速率限制

## 11. 重構重點總結

### 11.1 核心改進策略

1. **充分利用現有優化**
   - 直接使用 IndexCalculationServiceV2，無需重新實作
   - 該服務已包含 LRU 快取、並行處理、效能監控等優化
   - 專注於服務協調層的改進

2. **快取策略調整**
   - 認識到完全相同的請求較少見
   - 快取主要效益在於：
     - 同一用戶短時間內的履歷迭代
     - 批量處理場景
     - A/B 測試場景

3. **差異化文本處理**
   - Embedding: 使用 clean_html_text 清理 HTML
   - LLM: 考慮保留 HTML 結構以提供更多上下文
   - 實施 sanitize_html_for_llm 方法（移除 script/style，保留結構）

4. **監控與可觀測性**
   - 詳細追蹤各階段耗時
   - 記錄快取命中情況
   - 監控部分失敗率

## 12. 未來改進

### 12.1 短期（1-3 個月）
- Redis 分散式快取
- 批次處理 API
- WebSocket 串流回應

### 12.2 中期（3-6 個月）
- 機器學習優化匹配
- 自動 prompt 調優
- 多語言支援擴展

### 12.3 長期（6-12 個月）
- 完全異步架構
- 自適應快取策略
- AI 驅動的分析深度調整

---

## 附錄 A：API 遷移指南

### A.1 相容性說明
V2 API 完全向後相容 V1，現有整合無需修改即可使用。

### A.2 遷移步驟
1. 更新 API 端點至 `-v2` 版本
2. 可選：加入新的分析選項
3. 監控效能改進

### A.3 新功能使用
```python
# V2 新增選項
{
  "analysis_options": {
    "include_skill_priorities": true,
    "max_improvements": 5,
    "focus_areas": ["technical"]
  }
}
```

### A.4 輸入處理說明
- **HTML 處理**：系統會自動使用 `clean_html_text` 函數清理 HTML 標籤
- **文本長度**：履歷和職缺各限制 30KB（純文本約 2000 字）
- **語言支援**：en、zh-TW，系統會自動正規化語言代碼

---

**文檔結束**