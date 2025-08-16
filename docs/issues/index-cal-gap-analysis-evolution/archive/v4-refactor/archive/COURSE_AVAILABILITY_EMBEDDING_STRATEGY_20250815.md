# 課程可用性檢查 Embedding 策略文件

**文件版本**: 1.0.0  
**建立日期**: 2025-08-15  
**狀態**: Approved  
**作者**: AI Resume Advisor Team

## 執行摘要

本文件定義了課程可用性檢查功能（Course Availability Check）中的 Embedding 文本生成與查詢策略。透過混合策略（Hybrid Strategy），我們能夠根據技能類別（SKILL/FIELD）智慧地引導課程搜尋，提高相關課程的匹配準確度，同時保持結果的全面性。

## 背景分析

### Coursera 課程類型分布

根據 2025-08-15 的資料庫分析（8,759 門課程），使用 `course_type_standard` 標準化欄位：

| 標準課程類型 | 數量 | 百分比 | 說明 | 原始類型對應 |
|-------------|------|--------|------|------------|
| course | 6,075 | 69.4% | 單一課程，快速學習特定技能 | course, specialization-course, mastertrack-certificate |
| specialization | 1,462 | 16.7% | 系列課程，深入學習領域知識 | specialization |
| project | 629 | 7.2% | 引導式專案，實作導向 | guided-project |
| degree | 434 | 5.0% | 學位課程，系統性學習 | degree |
| certification | 159 | 1.8% | 專業證書，職業技能認證 | professional-certificate |

**註**：我們使用 `course_type_standard` 欄位進行查詢，它將原始的 7 種類型標準化為 5 種核心類型。

### 技能類別與課程類型的關聯性

透過分析 10 個代表性技能的搜尋結果，我們發現：

**SKILL 類別（技術技能）傾向**：
- 58.4% 匹配到 `course`（單一課程）
- 17.3% 匹配到 `specialization`（系列課程）
- 11.9% 匹配到 `guided-project`（實作專案）

**FIELD 類別（領域知識）傾向**：
- 49.2% 匹配到 `course`
- 23.0% 匹配到 `specialization`
- 20.4% 匹配到 `degree`（學位課程）

## 混合策略設計（Hybrid Strategy）

### 策略核心原則

1. **不排除任何課程類型** - 所有相關課程都會被包含
2. **優先排序而非過濾** - 偏好的課程類型會獲得更高權重
3. **保持文本自然性** - 最小干預原始描述
4. **類別差異化處理** - SKILL 和 FIELD 使用不同策略

### 策略組成

混合策略包含四個關鍵組件：

#### 1. Embedding 文本增強

根據技能類別加入精準的引導詞彙，提高目標課程類型的相似度分數。

```python
def generate_embedding_text(skill_query):
    """
    生成優化的 embedding 文本
    保持自然性的同時加入引導詞彙
    """
    skill_name = skill_query['skill_name']
    description = skill_query.get('description', '')
    category = skill_query['skill_category']
    
    if category == "SKILL":
        # 引導向: course, project, certification (標準化類型)
        # 加入實作導向的關鍵詞
        text = f"{skill_name} course project certificate. {description}"
        
    elif category == "FIELD":
        # 引導向: specialization, degree (標準化類型)
        # 加入系統學習的關鍵詞
        text = f"{skill_name} specialization degree. {description}"
    
    return text
```

#### 2. 差異化相似度閾值

不同類別使用不同的相似度門檻，平衡精確度與涵蓋範圍。

```python
SIMILARITY_THRESHOLDS = {
    "SKILL": 0.30,  # 較高閾值，更精確的技術匹配
    "FIELD": 0.25,  # 較低閾值，更廣泛的領域匹配
}
```

#### 3. 查詢時優先排序

在資料庫查詢階段，給予偏好的課程類型更高的優先權。

```sql
-- 優先排序查詢（使用 course_type_standard 標準化欄位）
WITH ranked_courses AS (
    SELECT 
        course_type_standard,
        name,
        1 - (embedding <=> $1::vector) as similarity,
        CASE 
            -- SKILL 類的偏好順序
            WHEN $3 = 'SKILL' THEN
                CASE course_type_standard
                    WHEN 'course' THEN 3         -- 最高優先（單一課程）
                    WHEN 'project' THEN 2        -- 次高（實作專案）
                    WHEN 'certification' THEN 1  -- 第三（專業證書）
                    ELSE 0  -- 其他類型仍會包含
                END
            -- FIELD 類的偏好順序
            WHEN $3 = 'FIELD' THEN
                CASE course_type_standard
                    WHEN 'specialization' THEN 3  -- 最高優先（系列課程）
                    WHEN 'degree' THEN 2           -- 次高（學位課程）
                    WHEN 'certification' THEN 1    -- 第三（領域認證）
                    ELSE 0  -- 其他類型仍會包含
                END
            ELSE 0
        END as priority_score
    FROM courses
    WHERE platform = 'coursera'
    AND embedding IS NOT NULL
)
SELECT 
    COUNT(*) > 0 as has_courses,
    COUNT(*) as total_count,
    SUM(CASE WHEN priority_score > 0 THEN 1 ELSE 0 END) as preferred_count,
    SUM(CASE WHEN priority_score = 0 THEN 1 ELSE 0 END) as other_count
FROM ranked_courses
WHERE similarity >= $2  -- 使用類別對應的閾值
ORDER BY priority_score DESC, similarity DESC
LIMIT 10
```

#### 4. 彈性降級處理

當偏好的課程類型不存在時，自動降級返回其他相關課程。

```python
def handle_course_results(results, category):
    """
    處理查詢結果，確保靈活性
    """
    if results['preferred_count'] > 0:
        # 有偏好類型的課程
        return {
            "has_courses": True,
            "course_count": results['total_count'],
            "preferred_match": True,
            "breakdown": {
                "preferred": results['preferred_count'],
                "other": results['other_count']
            }
        }
    elif results['total_count'] > 0:
        # 沒有偏好類型，但有其他相關課程
        return {
            "has_courses": True,
            "course_count": results['total_count'],
            "preferred_match": False,
            "note": "使用降級策略，返回其他類型課程"
        }
    else:
        # 完全沒有相關課程
        return {
            "has_courses": False,
            "course_count": 0
        }
```

## 實際應用範例

### SKILL 類別範例

#### Python（技術技能）

```python
輸入：
{
    "skill_name": "Python",
    "skill_category": "SKILL",
    "description": "Gain proficiency in Python for data analysis"
}

生成的 Embedding 文本：
"Python course project certificate. Gain proficiency in Python for data analysis"

預期結果：
- 優先匹配：Python 單一課程、實作專案、專業證書
- 次要匹配：Python 系列課程（如果相關性高）
- 總計返回：所有相似度 >= 0.30 的課程
```

#### Docker（技術技能）

```python
輸入：
{
    "skill_name": "Docker",
    "skill_category": "SKILL",
    "description": "Develop hands-on skills in Docker for deployment"
}

生成的 Embedding 文本：
"Docker course project certificate. Develop hands-on skills in Docker for deployment"

預期結果：
- 優先匹配：Docker 實作課程、容器化專案
- 也會包含：Docker 專業認證、相關系列課程
```

### FIELD 類別範例

#### Machine Learning（領域知識）

```python
輸入：
{
    "skill_name": "Machine Learning",
    "skill_category": "FIELD",
    "description": "Master core ML algorithms and deployment"
}

生成的 Embedding 文本：
"Machine Learning specialization degree. Master core ML algorithms and deployment"

預期結果：
- 優先匹配：ML 系列課程、資料科學學位
- 次要匹配：單一 ML 課程（如入門課程）
- 總計返回：所有相似度 >= 0.25 的課程
```

#### Data Science（領域知識）

```python
輸入：
{
    "skill_name": "Data Science",
    "skill_category": "FIELD",
    "description": "Build expertise in data science methodology"
}

生成的 Embedding 文本：
"Data Science specialization degree. Build expertise in data science methodology"

預期結果：
- 優先匹配：資料科學專業課程、學位課程
- 也會包含：個別的資料分析課程、統計課程
```

## 效能優化配置

### 連線池配置

考慮到並行查詢需求（最多 20 個技能），建議配置：

```python
pool_config = {
    "min_size": 2,       # 最小保持 2 個連線
    "max_size": 20,      # 最大 20 個連線（匹配並行上限）
    "max_inactive_connection_lifetime": 600,  # 10 分鐘後關閉閒置連線
    "command_timeout": 30
}
```

### 批次處理策略

```python
# 批次 Embedding 生成
async def batch_generate_embeddings(skill_queries):
    """
    一次 API 呼叫生成所有技能的 embeddings
    """
    # 根據類別生成優化的文本
    texts = [generate_embedding_text(skill) for skill in skill_queries]
    
    # 批次呼叫 Embedding API
    embeddings = await embedding_client.create_embeddings(texts)
    
    return embeddings
```

### 並行查詢執行

```python
# 並行執行資料庫查詢
async def parallel_check_availability(skill_embeddings):
    """
    使用 asyncio.gather 並行查詢所有技能
    """
    tasks = [
        check_single_skill(emb, skill['skill_name'], skill['skill_category'])
        for emb, skill in zip(skill_embeddings, skill_queries)
    ]
    
    # 並行執行，最多 20 個同時查詢
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return results
```

## 實作檢查清單

### 必要組件

- [x] Embedding 文本生成函數
- [x] 類別相似度閾值配置
- [x] 課程類型偏好映射
- [x] 資料庫查詢優化（優先排序）
- [x] 彈性降級處理邏輯
- [ ] 連線池配置（min=2, max=20）
- [ ] 批次 Embedding 生成
- [ ] 並行查詢執行（asyncio.gather）
- [ ] 錯誤處理與監控

### 測試覆蓋

- [ ] SKILL 類別 Embedding 生成測試
- [ ] FIELD 類別 Embedding 生成測試
- [ ] 優先排序邏輯測試
- [ ] 降級處理測試
- [ ] 並行查詢效能測試（< 200ms）
- [ ] 邊界情況測試（無結果、全部非偏好類型）

## 監控指標

```python
# 關鍵監控指標
metrics = {
    "embedding_generation_time_ms": "Embedding 生成時間",
    "db_query_time_ms": "資料庫查詢時間",
    "preferred_match_rate": "偏好類型匹配率",
    "fallback_rate": "降級處理比率",
    "cache_hit_rate": "快取命中率",
    "parallel_efficiency": "並行處理效率"
}
```

## 預期效果

### 量化指標

| 指標 | 目標值 | 說明 |
|------|--------|------|
| 響應時間 | < 200ms | 端到端處理時間 |
| 偏好匹配率 | > 70% | SKILL/FIELD 找到偏好類型的比率 |
| 總體匹配率 | > 90% | 找到任何相關課程的比率 |
| 並行效率 | > 80% | 並行處理的時間節省 |

### 質化改善

1. **更精準的課程推薦**：技術技能優先推薦實作課程，領域知識優先推薦系統課程
2. **保持選擇彈性**：不會錯過任何相關課程，用戶仍能看到所有選項
3. **自然的搜尋體驗**：Embedding 文本保持自然，不會過度優化
4. **穩定的服務品質**：降級處理確保即使沒有偏好類型也能返回結果

## 未來優化方向

1. **動態閾值調整**：根據歷史數據動態調整相似度閾值
2. **個人化偏好**：根據用戶歷史學習記錄調整課程類型權重
3. **A/B 測試框架**：比較不同策略的實際效果
4. **快取預熱優化**：根據熱門技能組合預先計算結果

## 結論

混合策略透過 Embedding 增強、差異化閾值、優先排序和彈性降級四個組件的協同作用，實現了精準而全面的課程可用性檢查。這個策略既能引導用戶找到最適合的課程類型，又不會限制他們的選擇，達到了準確性與靈活性的平衡。

---

**文件維護**：
- 最後更新：2025-08-15
- 下次審查：2025-09-15
- 負責團隊：AI Resume Advisor Platform Team