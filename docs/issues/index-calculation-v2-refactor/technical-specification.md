# Index Calculation V2 技術規格書

## 0. 環境要求

### 0.1 執行環境
- **Python 版本**: 3.11.8（專案指定版本，與 pyproject.toml 一致）
- **作業系統**: Linux (生產環境) / macOS (開發環境)
- **容器環境**: Docker 20.10+
- **記憶體要求**: 最少 2GB RAM

### 0.2 Python 套件要求
- FastAPI >= 0.104.0
- Python 3.11.8 特定功能：
  - 使用 `asyncio.TaskGroup` (3.11+)
  - 改進的錯誤訊息
  - 效能優化（比 3.9 快 10-60%）

## 1. API 介面規格

### 1.1 端點定義

#### 現有端點 (保持不變)
```
POST /api/v1/index-calculation
```

#### 請求格式
```json
{
  "resume": "string (HTML 或純文字)",
  "job_description": "string (HTML 或純文字)",
  "keywords": ["string"] 或 "string"  // 關鍵字陣列或逗號分隔字串
}
```

#### 回應格式
**重要**: Bubble.io API Connector 要求固定 schema，所有欄位必須存在
```json
{
  "success": true,
  "data": {
    "raw_similarity_percentage": 65,
    "similarity_percentage": 75,
    "keyword_coverage": {
      "total_keywords": 20,
      "covered_count": 15,
      "coverage_percentage": 75,
      "covered_keywords": ["Python", "API development", "Azure"],
      "missed_keywords": ["Docker", "Kubernetes", "GraphQL", "Redis", "MongoDB"]
    },
    "processing_time_ms": 1250,
    "cache_hit": false,
    "timing_breakdown": {  // 必須存在，但在生產環境返回空物件
      "validation_ms": 5,
      "embedding_generation_ms": 850,
      "similarity_calculation_ms": 120,
      "keyword_analysis_ms": 275,
      "total_ms": 1250
    }
  },
  "error": {
    "code": "",
    "message": "",
    "details": ""
  },
  "timestamp": "2025-08-02T10:30:00.000Z"
}
```

### 1.2 新增功能

#### 服務統計端點 (新增)
```
GET /api/v1/index-calculation/stats
```

**用途**: 
- 提供服務內部統計資料
- 可供 Azure Workbook 定期抓取進行視覺化
- 輕量級監控資料來源（無需 Application Insights）

回應格式：
```json
{
  "service_name": "IndexCalculationServiceV2",
  "calculation_stats": {
    "total_calculations": 1520,
    "average_processing_time_ms": 1250,
    "cache_hit_rate": 0.65
  },
  "performance_optimizations": {
    "parallel_processing_enabled": true,
    "cache_enabled": true,
    "cache_ttl_minutes": 60,
    "cache_size": 850
  }
}
```

## 2. 資料模型

### 2.1 請求模型 (保持現有)
```python
class IndexCalculationRequest(BaseModel):
    resume: str = Field(..., min_length=100, max_length=500000)
    job_description: str = Field(..., min_length=50, max_length=50000)
    keywords: Union[List[str], str] = Field(...)
    
    # 新增選項 (向後相容)
    options: Optional[IndexCalculationOptions] = None
```

### 2.2 選項模型 (新增)
```python
class IndexCalculationOptions(BaseModel):
    enable_cache: bool = True
    cache_ttl_override: Optional[int] = None  # 分鐘
    parallel_processing: bool = True
    include_timing_breakdown: bool = False  # 生產環境預設關閉，開發環境可開啟
```

### 2.3 內部模型
```python
class EmbeddingCache(BaseModel):
    text_hash: str
    embedding: List[float]
    created_at: datetime
    expires_at: datetime
    
class CalculationStats(BaseModel):
    total_calculations: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_processing_time_ms: float = 0
    error_count: int = 0
```

## 3. 效能規格

### 3.1 響應時間要求
| 場景 | 目標時間 | 最大時間 |
|------|---------|---------|
| Cache Hit | < 50ms | 100ms |
| Cache Miss (小文檔) | < 1秒 | 2秒 |
| Cache Miss (大文檔) | < 2秒 | 3秒 |
| 並發請求 (50 QPS) | < 2秒 | 3秒 |

### 3.2 資源限制
- **記憶體使用**: < 2GB (包含快取)
- **CPU 使用**: < 80% (1 vCPU)
- **快取大小**: 最大 1000 個條目
- **連線池**: 10-20 個持久連線

### 3.3 並發規格
- **最大並發請求**: 100
- **目標 QPS**: 50+
- **連線逾時**: 30 秒
- **請求逾時**: 10 秒

## 4. 快取策略

### 4.1 快取鍵設計
```python
def generate_cache_key(text: str, cache_type: str) -> str:
    """
    生成快取鍵
    - text: 原始文本
    - cache_type: "embedding" | "similarity" | "coverage"
    """
    normalized_text = normalize_text(text)
    return hashlib.sha256(
        f"{cache_type}:{normalized_text}".encode()
    ).hexdigest()
```

### 4.2 快取失效策略
- **TTL**: 預設 60 分鐘
- **LRU**: 超過 1000 個條目時淘汰最少使用
- **主動清理**: 每 100 次寫入觸發過期檢查

### 4.3 快取預熱
- 支援批量預熱常見查詢
- 背景任務定期更新熱門快取

## 5. 錯誤處理規格 

### 5.1 錯誤分類
| 錯誤碼 | HTTP 狀態 | 說明 |
|-------|-----------|------|
| VALIDATION_ERROR | 400 | 輸入驗證失敗 |
| EMBEDDING_ERROR | 500 | Embedding 生成失敗 |
| CACHE_ERROR | 500 | 快取操作失敗（降級處理）|
| TIMEOUT_ERROR | 504 | 請求處理超時 |
| SERVICE_UNAVAILABLE | 503 | Azure OpenAI 不可用 |

### 5.2 錯誤恢復策略
1. **快取錯誤**: 降級為無快取模式
2. **Embedding 錯誤**: 重試 3 次，指數退避
3. **超時錯誤**: 返回部分結果（如有）

### 5.3 錯誤日誌儲存機制（非 200 狀態）
為了協助 Operation Team 除錯，所有非 200 狀態都需要記錄詳細資訊：

```python
class ErrorLogger:
    """錯誤日誌記錄器"""
    
    async def log_error(
        self,
        request_id: str,
        status_code: int,
        error_info: dict,
        request_data: dict,
        response_data: dict
    ):
        """記錄錯誤詳情供除錯使用"""
        error_log = {
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status_code": status_code,
            "error": error_info,
            "request": {
                # 脫敏處理：只記錄必要資訊
                "resume_length": len(request_data.get("resume", "")),
                "job_description_length": len(request_data.get("job_description", "")),
                "keywords_count": len(request_data.get("keywords", [])),
                "options": request_data.get("options", {})
            },
            "response": response_data,
            "environment": {
                "service_version": settings.SERVICE_VERSION,
                "container_id": os.environ.get("CONTAINER_ID", "unknown")
            }
        }
        
        # 儲存選項：
        # 1. Azure Blob Storage (推薦)
        # 2. Application Insights Custom Events
        # 3. 本地檔案 (開發環境)
        await self._store_error_log(error_log)
```

**儲存策略**：
- 保留 7 天錯誤日誌
- 敏感資料脫敏（不儲存完整履歷內容）
- 包含足夠的 context 供除錯
- 可透過 request_id 追蹤完整流程

## 6. 監控指標

### 6.1 監控架構 
採用與 Keyword Extraction V2 相同的輕量級監控模式：
- **儲存位置**: 服務記憶體內統計（與 KeywordExtractionServiceV2 一致）
- **監控模式**: LIGHTWEIGHT_MONITORING=true（生產環境）
- **資料持久化**: 透過 /stats 端點定期收集

### 6.2 業務指標計算方式
- `index_calculation.total_requests` - 總請求數
  - 計算方式：每次 API 呼叫 +1
  - 儲存位置：service.calculation_stats["total_calculations"]
  
- `index_calculation.cache_hit_rate` - 快取命中率
  - 分子：cache_hits（快取命中次數）
  - 分母：total_calculations（總計算次數）
  - 公式：cache_hits / total_calculations
  
- `index_calculation.average_similarity` - 平均相似度
  - 分子：所有相似度分數總和
  - 分母：總計算次數
  - 公式：sum(similarity_scores) / total_calculations
  
- `index_calculation.keyword_coverage_rate` - 平均關鍵字覆蓋率
  - 分子：所有覆蓋率總和
  - 分母：總計算次數
  - 公式：sum(coverage_percentages) / total_calculations

### 6.3 效能指標
- `index_calculation.response_time` - 響應時間分布
- `index_calculation.embedding_time` - Embedding 生成時間
- `index_calculation.cache_operation_time` - 快取操作時間
- `index_calculation.concurrent_requests` - 並發請求數

### 6.4 錯誤指標
- `index_calculation.error_rate` - 錯誤率
- `index_calculation.error_by_type` - 按類型分類的錯誤
- `index_calculation.timeout_rate` - 超時率

### 6.5 監控儲存與 Dashboard 整體規劃
**階段性實作策略**：
1. **Phase 1 (當前)**: 輕量級記憶體內監控
   - 各端點獨立實作 `/stats` API
   - 記憶體內統計，重啟後重置
   - 適合開發和初期部署

2. **Phase 2 (未來)**: 統一監控基礎設施
   - 待所有端點完成後統一規劃
   - 考慮選項：
     - Azure Monitor Workbook（可視化 /stats 資料）
     - Application Insights（完整但成本較高）
     - 自建時序資料庫（如 InfluxDB）
   
3. **實作時機**: 
   - 建議在所有核心功能完成後
   - 統一設計監控 Dashboard
   - 避免重複工作和不一致的實作

## 7. 安全規格

### 7.1 輸入驗證
- HTML/Script 標籤清理
- 文本長度限制
- 關鍵字數量限制 (最多 100)

### 7.2 資料保護
- 不記錄完整的履歷內容
- 快取使用 hash 鍵，不存原文
- 敏感資料不進入日誌

## 8. 配置參數

### 8.1 環境變數
```bash
# 快取配置
INDEX_CALC_CACHE_ENABLED=true
INDEX_CALC_CACHE_TTL_MINUTES=60
INDEX_CALC_CACHE_MAX_SIZE=1000

# 效能配置
INDEX_CALC_PARALLEL_PROCESSING=true
INDEX_CALC_CONNECTION_POOL_SIZE=20
INDEX_CALC_REQUEST_TIMEOUT_SECONDS=10

# Sigmoid 轉換參數
SIGMOID_X0=0.373
SIGMOID_K=15.0

# 監控配置
INDEX_CALC_ENABLE_DETAILED_MONITORING=true
INDEX_CALC_METRICS_SAMPLE_RATE=0.1
```

## 9. 實作策略

### 9.1 簡化原則
- **無需向後相容**: 直接替換現有實作，追求程式碼簡潔
- **全新設計**: 不保留舊有程式碼結構
- **效能優先**: 生產環境關閉 timing_breakdown 等除錯資訊

### 9.2 核心邏輯保留
- **Sigmoid 轉換**: 保持現有邏輯（確保計算結果一致）
- **關鍵字匹配**: 保持現有規則
- **API 介面**: 保持相同的請求/回應格式（僅新增選填欄位）

### 9.3 部署策略
- **直接替換**: 無需 feature flag 或漸進式遷移
- **一次性切換**: 部署後直接使用 V2
- **無需回滾機制**: 舊程式碼將被完全移除

## 10. Bubble.io 相容性考量

### 10.1 固定 Schema 要求
Bubble.io API Connector 要求 200 狀態碼時必須返回相同的 schema，不支援 optional 欄位：

```python
def format_response(data: dict, include_timing: bool = False) -> dict:
    """確保回應格式符合 Bubble.io 要求"""
    response = {
        "success": True,
        "data": {
            "raw_similarity_percentage": data.get("raw_similarity_percentage", 0),
            "similarity_percentage": data.get("similarity_percentage", 0),
            "keyword_coverage": {
                "total_keywords": data.get("total_keywords", 0),
                "covered_count": data.get("covered_count", 0),
                "coverage_percentage": data.get("coverage_percentage", 0),
                "covered_keywords": data.get("covered_keywords", []),
                "missed_keywords": data.get("missed_keywords", [])
            },
            "processing_time_ms": data.get("processing_time_ms", 0),
            "cache_hit": data.get("cache_hit", False),
            "timing_breakdown": {}  # 生產環境返回空物件
        },
        "error": {
            "code": "",
            "message": "",
            "details": ""
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    # 開發環境才填充 timing_breakdown
    if include_timing and settings.ENVIRONMENT == "development":
        response["data"]["timing_breakdown"] = {
            "validation_ms": data.get("validation_ms", 0),
            "embedding_generation_ms": data.get("embedding_generation_ms", 0),
            "similarity_calculation_ms": data.get("similarity_calculation_ms", 0),
            "keyword_analysis_ms": data.get("keyword_analysis_ms", 0),
            "total_ms": data.get("total_ms", 0)
        }
    
    return response
```

### 10.2 實作建議
1. 所有欄位必須有預設值，避免 None 或缺失
2. 陣列欄位預設為空陣列 `[]`
3. 物件欄位預設為空物件 `{}`
4. 數值欄位預設為 `0`
5. 布林欄位預設為 `false`
6. 字串欄位預設為空字串 `""`

## 11. 測試要求

### 11.1 單元測試
- 服務類別方法覆蓋率 > 90%
- 快取邏輯覆蓋率 100%
- 錯誤處理路徑覆蓋率 100%

### 11.2 整合測試
- API 端點測試
- 快取行為測試
- 並發場景測試

### 11.3 效能測試
- 基準測試 (Baseline)
- 負載測試 (50 QPS)
- 壓力測試 (找出極限)

---

**規格版本**: 1.0.0  
**建立日期**: 2025-08-02  
**審核狀態**: 待審核