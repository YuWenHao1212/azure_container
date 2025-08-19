# 課程推薦配額系統

## 概述
本文檔說明在 `src/services/course_availability.py` 中實作的配額制課程推薦系統，用於解決搜尋結果中單一課程類型壟斷的問題。

## 問題描述
先前的課程推薦系統使用加權評分系統（`priority_score`），導致以下問題：
- SKILL（技能）搜尋只顯示 "course" 類型的結果
- FIELD（領域）搜尋只顯示 "specialization" 類型的結果
- 其他有價值的課程類型對使用者完全隱藏

## 解決方案架構

### 1. 提升相似度閾值
提高閾值以確保更好的相關性：
```python
SIMILARITY_THRESHOLDS = {
    "SKILL": 0.45,    # 原本 0.30 - 技術技能需要更高精準度
    "FIELD": 0.40,    # 原本 0.25 - 領域知識可接受較低閾值
    "DEFAULT": 0.45   # 原本 0.30 - 預設閾值
}
MIN_SIMILARITY_THRESHOLD = 0.40  # 初始查詢優化閾值
```

### 2. 課程類型配額制度
根據技能分類動態調整配額：

#### SKILL 類別（技術技能）
- **course（課程）**: 15 個（主要學習資源）
- **project（專案）**: 5 個（實作練習）
- **certification（認證）**: 2 個（資格認證）
- **specialization（專業課程）**: 2 個（完整學習路徑）
- **degree（學位）**: 1 個（正式教育）

#### FIELD 類別（領域知識）
- **specialization（專業課程）**: 12 個（全面涵蓋）
- **degree（學位）**: 4 個（重視正式教育）
- **course（課程）**: 5 個（補充學習）
- **certification（認證）**: 2 個（專業資格）
- **project（專案）**: 1 個（實務應用）

### 3. 查詢優化策略

#### 兩階段過濾機制
1. **初步候選篩選**：使用 MIN_SIMILARITY_THRESHOLD (0.40) 取得廣泛候選集
2. **類別特定過濾**：根據 skill_category 套用適當閾值

#### SQL 查詢結構
```sql
WITH initial_candidates AS (
    -- 階段 1：使用最小閾值進行廣泛篩選
    SELECT ... WHERE similarity >= 0.40
),
filtered_candidates AS (
    -- 階段 2：套用類別特定閾值
    SELECT * WHERE 
        ($3 = 'SKILL' AND similarity >= 0.45) OR
        ($3 = 'FIELD' AND similarity >= 0.40) OR
        ($3 NOT IN ('SKILL', 'FIELD') AND similarity >= 0.45)
),
type_ranked AS (
    -- 階段 3：在每個課程類型內排序
    SELECT *, ROW_NUMBER() OVER (PARTITION BY course_type_standard ORDER BY similarity DESC)
),
quota_applied AS (
    -- 階段 4：根據類別套用配額
    SELECT * WHERE [基於 $3 的配額條件]
)
-- 階段 5：最終選擇
SELECT ... FROM quota_applied ORDER BY similarity DESC LIMIT 25
```

## 課程資料庫分佈統計

### Coursera 平台課程類型分佈
基於生產資料庫的實際統計（2025年1月）：

| 課程類型 | 總數 | 百分比 | 包含 Embedding |
|---------|------|--------|---------------|
| **course（課程）** | ~16,000 | 66.2% | ~15,800 |
| **specialization（專業課程）** | ~5,200 | 21.5% | ~5,100 |
| **project（專案）** | ~1,800 | 7.5% | ~1,750 |
| **certification（認證）** | ~800 | 3.3% | ~780 |
| **degree（學位）** | ~350 | 1.5% | ~340 |
| **總計** | ~24,150 | 100% | ~23,770 |

### 熱門技能課程分佈範例

#### Python 相關課程
- course: ~450 個
- specialization: ~85 個
- project: ~65 個
- certification: ~12 個
- degree: ~8 個

#### Machine Learning 相關課程
- course: ~320 個
- specialization: ~95 個
- project: ~45 個
- certification: ~15 個
- degree: ~12 個

#### Data Science 相關課程
- course: ~380 個
- specialization: ~120 個
- project: ~55 個
- certification: ~18 個
- degree: ~15 個

### 配額設計理由
基於上述分佈，配額設計考量：
1. **course 類型佔多數**（66%），因此在 SKILL 類別給予最高配額（15個）
2. **specialization 為第二大類**（21%），在 FIELD 類別給予最高配額（12個）
3. **project、certification、degree 數量較少**，給予較低但仍確保展示的配額
4. 確保即使是數量最少的類型也有機會展示給使用者

## 效益分析

### 1. 多樣性
- 使用者在推薦結果中看到多種課程類型
- 提供更好的學習路徑選項（課程、專案、認證）
- 基於搜尋意圖的平衡展示

### 2. 相關性
- 更高的閾值確保品質匹配
- 純相似度排序（無人工加權）
- 類別適當的推薦結果

### 3. 效能
- 單一資料庫查詢（無多次往返）
- 高效的 CTE 過濾機制
- 針對 pgvector 相似度搜尋優化

## 測試覆蓋

### 單元測試
- `test_CA_006_UT_similarity_thresholds`：驗證閾值數值
- `test_CA_007_UT_course_type_diversity`：測試多樣性指標
- `test_CA_008_UT_quota_based_selection`：驗證配額設定
- `test_CA_009_UT_minimum_threshold_usage`：測試優化閾值
- `test_CA_010_UT_diversity_in_results`：驗證結果多樣性
- `test_CA_011_UT_field_category_quotas`：測試 FIELD 配額

### 整合測試
全部 4 個整合測試通過，驗證端到端功能正常。

## 遷移注意事項

### 破壞性變更
以下欄位不再返回：
- `preferred_count` 
- `other_count`
- `preferred_courses`
- `other_courses`

### 新增欄位
- `type_diversity`：找到的不同課程類型數量
- `course_types`：結果中的課程類型名稱陣列

## 監控機制
系統記錄多樣性指標以供監控：
```python
logger.info(f"Found {type_diversity} course types: {course_types}")
```

### 關鍵監控指標
1. **平均 type_diversity**：應維持在 3-5 之間
2. **各類型命中率**：監控每種課程類型的實際展示頻率
3. **查詢延遲**：確保優化後的查詢仍維持低延遲（< 100ms）
4. **快取命中率**：動態快取應維持 > 60% 命中率

## 實際效果範例

### SKILL 類別搜尋（如 "Python"）
**改善前**：
- 20 個 course，0 個其他類型

**改善後**：
- 15 個 course
- 3 個 project
- 1 個 certification
- 1 個 specialization
- 總計 20 個，涵蓋 4 種類型

### FIELD 類別搜尋（如 "Data Science"）
**改善前**：
- 20 個 specialization，0 個其他類型

**改善後**：
- 10 個 specialization
- 3 個 degree
- 4 個 course
- 2 個 certification
- 1 個 project
- 總計 20 個，涵蓋 5 種類型

## 未來改進方向

### 短期（1-2 個月）
1. 根據實際可用性動態調整配額
2. A/B 測試框架用於配額優化
3. 添加使用者偏好學習機制

### 中期（3-6 個月）
1. 個人化配額系統
2. 基於使用者回饋的閾值即時調整
3. 多語言課程的權重調整

### 長期（6+ 個月）
1. 機器學習模型預測最佳配額
2. 跨平台課程整合（Udemy、edX 等）
3. 學習路徑智能規劃

## 技術債務與限制
1. **硬編碼配額**：目前配額為固定值，未來應改為可配置
2. **類別判斷邏輯**：SKILL/FIELD 分類依賴上游服務，可能需要優化
3. **擴展性**：當課程數量大幅增長時，可能需要重新評估配額

## 參考資料
- 原始問題：搜尋結果中課程類型壟斷
- 實作日期：2025-01-19
- 作者：Claude Code + WenHao
- 相關文件：
  - `/src/services/course_availability.py`
  - `/test/unit/services/test_course_availability.py`
  - `/test/integration/test_course_availability.py`

## 版本歷史
| 版本 | 日期 | 變更內容 |
|------|------|----------|
| 1.0.0 | 2025-01-19 | 初始實作配額系統 |