# 動態課程快取系統設計文檔

**建立日期**: 2025-08-19 12:34 CST  
**設計者**: Claude Code  
**版本**: v1.0.0

## 設計目標

實作一個高效能、記憶體友善的動態快取系統，解決 Course Availability Check 中假課程 ID 和效能問題。

### 核心需求
1. **真實資料**: 快取實際資料庫查詢結果，包含有效課程 ID
2. **精確匹配**: 基於完整 embedding text 而非僅 skill_name 進行快取
3. **效能優化**: 快取命中時 < 1ms，避免重複 embedding 計算和資料庫查詢
4. **記憶體控制**: 限制快取大小，使用 LRU 淘汰策略
5. **資料新鮮度**: TTL 機制確保資料不會過期太久

## 技術架構

### 1. 快取鍵設計

#### 快取鍵生成算法
```python
def generate_cache_key(skill_query: dict, skill_category: str, threshold: float) -> str:
    # 1. 生成完整 embedding text
    embedding_text = self._generate_embedding_text(skill_query)
    
    # 2. 組合查詢條件
    cache_components = [
        embedding_text,
        skill_category, 
        str(threshold),
        "coursera"  # platform 固定值
    ]
    
    # 3. 生成 MD5 hash (截取前16字元)
    cache_string = "|".join(cache_components)
    return hashlib.md5(cache_string.encode()).hexdigest()[:16]
```

#### 快取鍵示例
```
Input:
- skill_name: "Python"
- description: "Programming language for web development"
- skill_category: "SKILL"
- threshold: 0.30

embedding_text: "Python course project certificate. Programming language for web development"
cache_key: "a1b2c3d4e5f6g7h8"  # MD5 hash 前16字元
```

### 2. 快取資料結構

#### 快取項目格式
```python
@dataclass
class CacheItem:
    """快取項目資料結構"""
    data: dict[str, Any]          # 查詢結果
    timestamp: datetime           # 快取時間
    access_count: int = 0         # 存取次數
    last_access: datetime = None  # 最後存取時間
```

#### 查詢結果格式
```python
cached_result = {
    "has_courses": True,
    "count": 8,
    "preferred_count": 5,
    "other_count": 3,
    "course_ids": [
        "coursera_crse:v1-12345",
        "coursera_prjt:v1-67890",
        # ... 真實課程 ID
    ],
    "similarity_scores": [0.85, 0.82, 0.78, ...],  # 可選：用於調試
    "query_timestamp": "2025-08-19T12:34:48Z"
}
```

### 3. 記憶體管理策略

#### LRU (Least Recently Used) 實作
```python
class DynamicCourseCache:
    def __init__(self, max_size: int = 1000, ttl_minutes: int = 30):
        self._cache: dict[str, CacheItem] = {}
        self._access_order: deque = deque()  # LRU 追蹤
        self._max_size = max_size
        self._ttl = timedelta(minutes=ttl_minutes)
        self._lock = asyncio.Lock()  # 執行緒安全
```

#### 容量管理
- **最大項目**: 1000 個快取項目
- **預估記憶體**: 30-50MB (每項目約 30-50KB)
- **淘汰策略**: 當達到容量限制時，移除最少使用的項目
- **清理觸發**: 每次新增時檢查容量，每小時背景清理過期項目

### 4. TTL (Time To Live) 機制

#### 過期策略
- **TTL 時間**: 30 分鐘 (平衡資料新鮮度與快取效率)
- **被動清理**: 存取時檢查是否過期
- **主動清理**: 背景任務每小時清理過期項目
- **優雅降級**: 過期時自動回退到資料庫查詢

#### 時間計算
```python
def is_expired(self, item: CacheItem) -> bool:
    return datetime.now() - item.timestamp > self._ttl

def cleanup_expired(self):
    """移除所有過期項目"""
    expired_keys = []
    for key, item in self._cache.items():
        if self.is_expired(item):
            expired_keys.append(key)
    
    for key in expired_keys:
        self._remove_item(key)
```

## 整合設計

### 1. CourseAvailabilityChecker 整合

#### 修改後的查詢流程
```python
async def check_course_availability(self, skill_queries: list[dict]) -> list[dict]:
    """Enhanced with dynamic cache"""
    
    for skill in skill_queries:
        # 1. 生成快取鍵
        cache_key = self._cache.generate_cache_key(
            skill, 
            skill.get('skill_category', 'DEFAULT'),
            threshold
        )
        
        # 2. 檢查快取
        cached_result = await self._cache.get(cache_key)
        if cached_result:
            # 快取命中：直接使用結果
            skill.update(cached_result)
            continue
        
        # 3. 快取未命中：執行查詢
        embedding_text = self._generate_embedding_text(skill)
        embedding = await self._embedding_client.create_embeddings([embedding_text])
        result = await self._check_single_skill(embedding[0], skill['skill_name'])
        
        # 4. 儲存到快取
        await self._cache.set(cache_key, result)
        skill.update(result)
```

### 2. 與現有快取的相容性

#### 移除靜態快取
```python
# 移除或重構 POPULAR_SKILLS_CACHE
# 保留作為 fallback 或統計用途，但不用於主要快取邏輯

POPULAR_SKILLS_REFERENCE = {
    # 僅保留統計資訊，用於監控和比較
    "Python": {"expected_courses": True, "category": "SKILL"},
    "JavaScript": {"expected_courses": True, "category": "SKILL"},
    # ...
}
```

## 監控與除錯

### 1. 快取統計

#### 關鍵指標
```python
@dataclass
class CacheStats:
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    hit_rate: float = 0.0
    avg_retrieval_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    active_items: int = 0
    expired_items_cleaned: int = 0
```

#### 監控整合
```python
def track_cache_metrics(self, operation: str, duration_ms: float):
    """整合輕量級監控"""
    if settings.LIGHTWEIGHT_MONITORING:
        monitoring_service.track_event("DynamicCacheOperation", {
            "operation": operation,
            "duration_ms": duration_ms,
            "hit_rate": self.get_hit_rate(),
            "cache_size": len(self._cache)
        })
```

### 2. 除錯端點

#### 快取狀態 API
```python
# GET /api/v1/debug/course-cache/stats
{
    "cache_stats": {
        "hit_rate": "75.5%",
        "total_requests": 1250,
        "active_items": 342,
        "memory_usage_mb": 18.5
    },
    "top_cached_items": [
        {"cache_key": "a1b2c3d4...", "hits": 45, "skill": "Python"},
        {"cache_key": "e5f6g7h8...", "hits": 38, "skill": "JavaScript"}
    ]
}
```

## 效能預期

### 1. 回應時間對比

| 情況 | 現有實作 | 動態快取 | 改善比例 |
|------|----------|----------|----------|
| 快取命中 | 300-500ms | < 1ms | 99.7% |
| 快取未命中 | 300-500ms | 300-500ms | 0% |
| 整體平均 (70% 命中率) | 350ms | 90ms | 74% |

### 2. 資源使用

| 資源 | 預估使用量 | 說明 |
|------|------------|------|
| 記憶體 | 30-50MB | 1000 項目快取 |
| CPU | < 1% | 快取操作開銷 |
| 網路 | -70% | 減少資料庫連線 |

### 3. 擴展性考量

#### 垂直擴展
- **記憶體限制**: 單容器最大快取 < 100MB
- **項目數量**: 最多 2000 項目 (可設定)

#### 水平擴展  
- **容器間獨立**: 每個容器維護獨立快取
- **一致性**: 30 分鐘 TTL 確保最終一致性
- **無狀態**: 容器重啟自動清理快取

## 實作計畫

### Phase 1: 核心快取模組 (45 分鐘)
- [ ] 建立 `DynamicCourseCache` 類別
- [ ] 實作快取鍵生成
- [ ] 實作 LRU + TTL 機制
- [ ] 新增執行緒安全保護

### Phase 2: 服務整合 (30 分鐘)
- [ ] 修改 `CourseAvailabilityChecker`
- [ ] 更新查詢流程
- [ ] 新增快取統計追蹤

### Phase 3: 監控與 API (30 分鐘)
- [ ] 新增除錯 API 端點
- [ ] 整合輕量級監控
- [ ] 新增背景清理任務

### Phase 4: 測試驗證 (45 分鐘)
- [ ] 單元測試
- [ ] 整合測試
- [ ] 效能驗證

## 風險評估

### 潛在風險與緩解

| 風險 | 影響 | 機率 | 緩解策略 |
|------|------|------|----------|
| 記憶體洩漏 | 高 | 低 | 嚴格容量限制 + 定期清理 |
| 資料不一致 | 中 | 中 | 30分鐘 TTL + 手動清理 API |
| 快取雪崩 | 高 | 低 | 分散過期時間 + 優雅降級 |
| 冷啟動效能 | 低 | 高 | 預期行為，首次查詢建立快取 |

### 回滾計畫
- 通過環境變數 `ENABLE_COURSE_CACHE` 控制快取啟用/停用（預設：啟用）
- 快取停用時直接查詢資料庫（無快取模式）
- 保留監控 API 端點以觀察效能差異
- 可隨時透過環境變數切換，無需重新部署

---

**下一步**: 實作 `DynamicCourseCache` 模組 (參考 src/services/dynamic_course_cache.py)