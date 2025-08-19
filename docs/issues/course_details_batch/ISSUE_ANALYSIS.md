# Course Availability Cache 問題分析

**建立日期**: 2025-08-19 12:34 CST  
**分析者**: Claude Code  
**優先級**: 高 (影響 Gap Analysis API 用戶體驗)

## 問題概述

Gap Analysis API (`/api/v1/index-cal-and-gap-analysis`) 在返回 SkillSearchQueries 時，會包含不存在於資料庫的假課程 ID，導致下游 Course Batch API 無法找到對應課程，影響用戶體驗。

### 受影響的 API 端點
- `/api/v1/index-cal-and-gap-analysis` (主要)
- `/api/v1/courses/get-by-ids` (下游影響)

### 問題影響範圍
- **用戶體驗**: 用戶點擊推薦課程連結時出現 404 錯誤
- **資料一致性**: API 返回與資料庫不符的課程 ID
- **下游服務**: Course Batch API 需要處理大量無效 ID

## 根本原因分析

### 1. 假課程 ID 來源

**位置**: `src/services/course_availability.py:25-81`

```python
POPULAR_SKILLS_CACHE = {
    "Python": {
        "has_courses": True,
        "count": 10,
        # 以前包含假的 course_ids，現已移除
    },
    # ... 其他技能
}
```

**問題**: 原本的 `POPULAR_SKILLS_CACHE` 包含硬編碼的假課程 ID，如：
- `coursera_crse:v1-2702`
- `coursera_crse:v1-2703` 
- `coursera_spzn:deep-learning`

### 2. 快取機制缺陷

**位置**: `src/services/course_availability.py:280-302`

當技能名稱在 `POPULAR_SKILLS_CACHE` 中被找到時：

```python
def _check_cache(self, skill_queries: list[dict]) -> dict[str, dict]:
    for skill in skill_queries:
        name = skill['skill_name']
        if name in POPULAR_SKILLS_CACHE:
            # 快取命中，但返回空陣列
            skill["available_course_ids"] = []  # 臨時解決方案
```

**問題**:
1. 快取命中時僅根據 `skill_name` 判斷，忽略 `description` 和 `skill_category`
2. 返回空的 `available_course_ids` 陣列，無法提供真實課程推薦
3. 沒有真正的動態快取機制

### 3. Embedding 與查詢不一致

**位置**: `src/services/course_availability.py:140-166`

系統生成 embedding text 的邏輯：

```python
def _generate_embedding_text(self, skill_query: dict[str, Any]) -> str:
    if category == "SKILL":
        text = f"{skill_name} course project certificate. {description}"
    elif category == "FIELD":
        text = f"{skill_name} specialization degree. {description}"
```

**問題**: 快取鍵僅使用 `skill_name`，但實際查詢使用完整的 embedding text，導致：
- 相同技能名稱但不同描述的查詢被錯誤快取
- 快取命中率計算不準確
- 語義相似但表達不同的技能被歸為同一快取項目

## 現狀評估

### 已修復問題 ✅
1. **假課程 ID 移除**: 已從 `POPULAR_SKILLS_CACHE` 中移除所有假課程 ID
2. **欄位完整性**: 確保 `available_course_ids` 欄位總是存在
3. **錯誤處理**: 失敗時正確設定空陣列

### 待解決問題 ❌
1. **快取命中返回空陣列**: 用戶無法獲得課程推薦
2. **快取鍵不準確**: 基於 skill_name 而非 embedding text
3. **無動態快取**: 無法儲存真實查詢結果
4. **效能未優化**: 每次都需要重新生成 embedding 和查詢資料庫

## 資料流分析

### 當前流程 (有問題)
```
Gap Analysis Request
    ↓
CourseAvailabilityChecker.check_course_availability()
    ↓
_check_cache() [基於 skill_name]
    ↓ (快取命中)
skill["available_course_ids"] = []  ← 空陣列
    ↓
返回 SkillSearchQueries (無課程推薦)
```

### 期望流程 (目標)
```
Gap Analysis Request
    ↓
CourseAvailabilityChecker.check_course_availability()
    ↓
DynamicCourseCache.get() [基於 embedding_text hash]
    ↓ (快取命中)
返回真實課程 ID 和統計資料
    ↓
返回 SkillSearchQueries (包含有效課程推薦)
```

## 效能影響分析

### 當前效能問題
- **重複 embedding 計算**: 相同技能重複計算向量
- **重複資料庫查詢**: 相同查詢條件重複執行 SQL
- **快取命中率低**: 基於 skill_name 的粗糙匹配

### 預期改善 (實作動態快取後)
- **Embedding 計算**: 減少 70-80% (快取命中時跳過)
- **資料庫查詢**: 減少 70-80% (快取命中時跳過)
- **回應時間**: 從 300-500ms 降至 < 1ms (快取命中時)

## 驗證方法

### 問題重現步驟
1. 發送 Gap Analysis 請求 (包含常見技能如 "Python")
2. 檢查返回的 `skill_queries[].available_course_ids`
3. 確認是否包含假課程 ID 或空陣列

### 測試案例
```bash
# 驗證假課程 ID 已移除
python scripts/check_courses.py

# 測試 Gap Analysis API
curl -X POST "https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io/api/v1/index-cal-and-gap-analysis" \
  -H "X-API-Key: $API_KEY" \
  -d '{"jd": "Python developer needed...", "resume": "..."}'
```

## 解決方案概述

實作 **動態課程快取系統** 來解決上述問題：

1. **精確快取鍵**: 基於完整 embedding text 的 hash
2. **真實資料儲存**: 快取實際查詢結果 (包含課程 ID)
3. **TTL 機制**: 30 分鐘自動過期確保資料新鮮度
4. **LRU 淘汰**: 限制記憶體使用並移除舊項目
5. **輕量監控**: 整合現有監控系統追蹤效能

詳細技術設計請參考: `DYNAMIC_CACHE_DESIGN.md`

---

**下一步**: 設計並實作動態快取系統 (參考 DYNAMIC_CACHE_DESIGN.md)