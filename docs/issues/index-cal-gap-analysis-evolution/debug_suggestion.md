# Course Details 空陣列問題 - Debug 指南

## 📊 問題摘要

**核心問題**: SQL查詢成功找到課程（`course_ids` 有值），但 `course_details` 的JSON聚合失敗返回空陣列。

### 關鍵觀察點
1. ✅ `array_agg(id)` **正常運作** → 資料存在且可訪問
2. ❌ `array_agg(json_build_object(...))` **失敗** → JSON建構或聚合有問題  
3. ⚠️ 測試環境正常，生產環境失敗 → 環境差異或資料差異

---

## 🎯 可能的根本原因

### 1. PostgreSQL JSON聚合的隱性失敗
```sql
-- 當array_agg遇到任何NULL的json_build_object時，整個聚合可能返回NULL
-- 即使使用了COALESCE包裝個別欄位
```

### 2. 特殊字符或編碼問題
生產資料可能包含導致JSON建構失敗的特殊字符：
- 無效的UTF-8序列
- 控制字符
- 不可見字符

### 3. 型別轉換陷阱
```sql
ARRAY[]::json[]  -- 這個空陣列轉換可能在某些PostgreSQL版本中有問題
```

---

## 📋 Debug方向和具體做法

### 方向1: 診斷JSON建構失敗

#### 1.1 測試JSON建構是否成功（逐步隔離）
```sql
-- 測試每個欄位的JSON建構
SELECT 
    id,
    -- 測試每個欄位的JSON建構
    json_build_object('id', id) as test_id,
    json_build_object('name', name) as test_name,
    json_build_object('description', LEFT(description, 200)) as test_desc,
    -- 測試完整的JSON物件
    CASE 
        WHEN json_build_object(
            'id', id,
            'name', COALESCE(name, ''),
            'description', COALESCE(LEFT(description, 200), '')
        ) IS NULL THEN 'JSON_BUILD_FAILED'
        ELSE 'JSON_BUILD_SUCCESS'
    END as json_status
FROM courses
WHERE platform = 'coursera'
AND id IN ('coursera_crse:fcHyUPEPEe6gPxJK4ChNFw')  -- 使用已知的課程ID
LIMIT 5;
```

#### 1.2 檢查特殊字符問題
```sql
-- 檢查是否有特殊字符導致JSON失敗
SELECT 
    id,
    name,
    -- 檢查非ASCII字符
    name ~ '[^\x00-\x7F]' as has_non_ascii,
    -- 檢查控制字符
    name ~ '[\x00-\x1F\x7F]' as has_control_chars,
    -- 檢查無效的UTF-8序列
    CASE WHEN name::bytea IS DISTINCT FROM CONVERT_TO(name, 'UTF8') 
         THEN true ELSE false END as invalid_utf8,
    -- 檢查長度
    LENGTH(name) as name_length,
    OCTET_LENGTH(name) as name_bytes
FROM courses
WHERE platform = 'coursera'
AND id IN (SELECT id FROM courses WHERE platform = 'coursera' LIMIT 100);
```

#### 1.3 找出問題資料
```sql
-- 找出可能有問題的記錄
SELECT 
    id,
    name,
    -- 顯示前10個字符的byte值
    encode(CAST(LEFT(name, 10) AS bytea), 'hex') as name_hex,
    -- 檢查是否能成功建構JSON
    json_build_object('test', name) IS NULL as json_fails
FROM courses
WHERE platform = 'coursera'
AND (
    name ~ '[\x00-\x1F\x7F]' OR  -- 有控制字符
    name IS NULL OR               -- NULL值
    LENGTH(name) = 0              -- 空字串
)
LIMIT 20;
```

---

### 方向2: 測試聚合行為差異

#### 2.1 比較不同聚合方法
```sql
-- 比較不同聚合方法的結果
WITH test_data AS (
    SELECT * FROM courses 
    WHERE platform = 'coursera' 
    AND embedding IS NOT NULL 
    LIMIT 10
)
SELECT 
    -- 方法1: 原始方法
    array_agg(
        json_build_object('id', id, 'name', name)
    ) as method1,
    
    -- 方法2: 使用jsonb而非json
    array_agg(
        jsonb_build_object('id', id, 'name', name)
    ) as method2,
    
    -- 方法3: 使用row_to_json
    array_agg(
        row_to_json(ROW(id, name))
    ) as method3,
    
    -- 方法4: 先過濾NULL再聚合
    array_agg(
        CASE WHEN id IS NOT NULL AND name IS NOT NULL 
        THEN json_build_object('id', id, 'name', name)
        END
    ) as method4,
    
    -- 方法5: 使用JSON_AGG
    JSON_AGG(
        JSON_BUILD_OBJECT('id', id, 'name', name)
    ) as method5
FROM test_data;
```

#### 2.2 檢查FILTER子句行為
```sql
-- 測試FILTER在不同情況下的行為
SELECT 
    -- 測試FILTER在沒有符合條件時的返回值
    array_agg(id) FILTER (WHERE false) as empty_filter,
    array_agg(id) FILTER (WHERE false) IS NULL as filter_is_null,
    -- 測試COALESCE是否能處理
    COALESCE(array_agg(id) FILTER (WHERE false), ARRAY[]::text[]) as coalesced_filter,
    -- 測試JSON陣列
    COALESCE(
        array_agg(json_build_object('id', id)) FILTER (WHERE false), 
        ARRAY[]::json[]
    ) as json_filter
FROM courses LIMIT 1;
```

---

### 方向3: 環境差異診斷

#### 3.1 檢查資料庫環境
```sql
-- PostgreSQL版本和配置
SELECT version();
SELECT current_setting('server_version_num');

-- 編碼設定
SELECT 
    current_setting('server_encoding') as server_encoding,
    current_setting('client_encoding') as client_encoding,
    current_setting('lc_collate') as lc_collate,
    current_setting('lc_ctype') as lc_ctype;

-- pgvector擴充套件
SELECT 
    extname,
    extversion,
    extnamespace::regnamespace as schema
FROM pg_extension 
WHERE extname = 'vector';

-- JSON相關設定
SELECT name, setting, unit, context 
FROM pg_settings 
WHERE name LIKE '%json%' 
   OR name LIKE '%encoding%'
   OR name LIKE '%bytea%';
```

#### 3.2 比較測試與生產環境
```sql
-- 產生環境快照
CREATE TABLE env_snapshot AS
SELECT 
    'production' as environment,
    version() as pg_version,
    current_setting('server_encoding') as encoding,
    (SELECT extversion FROM pg_extension WHERE extname = 'vector') as vector_version,
    COUNT(*) as course_count,
    COUNT(DISTINCT provider_standardized) as provider_count,
    NOW() as snapshot_time
FROM courses
WHERE platform = 'coursera';

-- 檢查資料特徵差異
SELECT 
    'name_lengths' as metric,
    MIN(LENGTH(name)) as min_val,
    AVG(LENGTH(name))::int as avg_val,
    MAX(LENGTH(name)) as max_val,
    COUNT(*) FILTER (WHERE name IS NULL) as null_count,
    COUNT(*) FILTER (WHERE LENGTH(name) = 0) as empty_count
FROM courses
WHERE platform = 'coursera'
UNION ALL
SELECT 
    'description_lengths',
    MIN(LENGTH(description)),
    AVG(LENGTH(description))::int,
    MAX(LENGTH(description)),
    COUNT(*) FILTER (WHERE description IS NULL),
    COUNT(*) FILTER (WHERE LENGTH(description) = 0)
FROM courses
WHERE platform = 'coursera';
```

---

### 方向4: 漸進式修復策略

#### 4.1 最簡化測試
```sql
-- 步驟1: 確認基本功能
SELECT 
    array_agg(id) as ids,
    array_agg(name) as names,
    COUNT(*) as total
FROM courses
WHERE platform = 'coursera'
AND embedding IS NOT NULL
LIMIT 25;
```

#### 4.2 逐步增加複雜度
```sql
-- Step 1: 只建構最簡單的JSON
SELECT array_to_json(array_agg(id)) as simple_json
FROM courses WHERE platform = 'coursera' LIMIT 5;

-- Step 2: 增加一個欄位
SELECT array_to_json(
    array_agg(
        json_build_object('id', id, 'name', name)
    )
) as two_field_json
FROM courses WHERE platform = 'coursera' LIMIT 5;

-- Step 3: 處理NULL值
SELECT array_to_json(
    array_agg(
        json_build_object(
            'id', COALESCE(id, 'NO_ID'),
            'name', COALESCE(name, 'NO_NAME')
        )
    )
) as safe_json
FROM courses WHERE platform = 'coursera' LIMIT 5;

-- Step 4: 加入描述欄位（可能的問題來源）
SELECT array_to_json(
    array_agg(
        json_build_object(
            'id', id,
            'name', COALESCE(name, ''),
            'description', COALESCE(
                REGEXP_REPLACE(LEFT(description, 200), '[\x00-\x1F\x7F]', '', 'g'),
                ''
            )
        )
    )
) as full_json
FROM courses WHERE platform = 'coursera' LIMIT 5;
```

---

### 方向5: 替代實作方案

#### 5.1 使用JSON_AGG（更穩定）
```sql
-- 使用JSON_AGG代替array_agg(json_build_object)
WITH quota_applied AS (
    -- 你的原始CTE查詢
    SELECT * FROM courses WHERE platform = 'coursera' LIMIT 25
)
SELECT 
    COUNT(*) as count,
    array_agg(id) as course_ids,
    JSON_AGG(
        JSON_BUILD_OBJECT(
            'id', id,
            'name', COALESCE(name, ''),
            'type', COALESCE(course_type_standard, 'course'),
            'provider_standardized', COALESCE(provider_standardized, 'Coursera'),
            'description', COALESCE(
                REGEXP_REPLACE(LEFT(description, 200), '[\x00-\x1F\x7F]', '', 'g'),
                ''
            ),
            'similarity', similarity
        )
        ORDER BY similarity DESC
    ) as course_details_json
FROM quota_applied;
```

#### 5.2 分離查詢策略
```sql
-- 第一步：只取得ID和similarity
CREATE TEMP TABLE temp_course_results AS
WITH quota_applied AS (
    -- 你的CTE查詢
)
SELECT id, similarity 
FROM quota_applied;

-- 第二步：根據ID取得詳細資料（避免複雜聚合）
SELECT 
    t.id,
    c.name,
    c.course_type_standard as type,
    c.provider_standardized,
    LEFT(c.description, 200) as description,
    t.similarity
FROM temp_course_results t
JOIN courses c ON c.id = t.id
ORDER BY t.similarity DESC;
```

#### 5.3 清理資料的聚合
```sql
-- 在聚合前清理資料
WITH cleaned_data AS (
    SELECT 
        id,
        -- 清理name欄位
        REGEXP_REPLACE(
            COALESCE(name, ''),
            '[\x00-\x1F\x7F]',  -- 移除控制字符
            '',
            'g'
        ) as clean_name,
        -- 清理description欄位
        REGEXP_REPLACE(
            COALESCE(LEFT(description, 200), ''),
            '[\x00-\x1F\x7F]',
            '',
            'g'
        ) as clean_description,
        course_type_standard,
        provider_standardized,
        similarity
    FROM quota_applied
)
SELECT 
    array_agg(
        json_build_object(
            'id', id,
            'name', clean_name,
            'description', clean_description,
            'type', COALESCE(course_type_standard, 'course'),
            'provider', COALESCE(provider_standardized, 'Coursera'),
            'similarity', similarity
        )
        ORDER BY similarity DESC
    ) as course_details
FROM cleaned_data;
```

---

## 🚀 立即行動計畫

### 優先順序1: 快速診斷（15分鐘）
1. 執行 **方向1.1** - 測試JSON建構是否成功
2. 執行 **方向1.2** - 檢查特殊字符問題
3. 執行 **方向3.1** - 確認環境設定

### 優先順序2: 驗證假設（30分鐘）
1. 執行 **方向2.1** - 比較不同聚合方法
2. 執行 **方向1.3** - 找出問題資料
3. 執行 **方向4.2** - 逐步測試複雜度

### 優先順序3: 實施修復（1小時）
1. 如果是特殊字符問題 → 實施 **方向5.3**（清理資料）
2. 如果是聚合方法問題 → 實施 **方向5.1**（使用JSON_AGG）
3. 如果問題複雜 → 實施 **方向5.2**（分離查詢）

---

## 📊 監控指標

修復後應監控以下指標：

```sql
-- 建立監控查詢
CREATE OR REPLACE VIEW course_details_monitor AS
SELECT 
    DATE_TRUNC('hour', query_time) as hour,
    COUNT(*) as total_queries,
    COUNT(*) FILTER (WHERE course_count > 0) as queries_with_courses,
    COUNT(*) FILTER (WHERE course_count > 0 AND course_details_count = 0) as empty_details_issues,
    AVG(course_count) as avg_course_count,
    AVG(course_details_count) as avg_details_count,
    (COUNT(*) FILTER (WHERE course_count > 0 AND course_details_count > 0))::float / 
    NULLIF(COUNT(*) FILTER (WHERE course_count > 0), 0) * 100 as success_rate
FROM api_query_logs
WHERE endpoint = '/api/v1/index-cal-and-gap-analysis'
GROUP BY 1
ORDER BY 1 DESC;
```

---

## 🎯 成功標準

修復成功的標誌：
- [ ] `course_details` 不再返回空陣列（當 `course_count > 0` 時）
- [ ] 所有課程詳細資料包含必要欄位
- [ ] 查詢效能影響 < 100ms
- [ ] 監控顯示 success_rate > 99%

---

## 📝 備註

**最可能的原因**：生產資料包含特殊字符或編碼問題，導致 `json_build_object` 靜默失敗。

**建議立即嘗試**：方向5.1 的 JSON_AGG 方案，這通常更穩定且對特殊字符的容錯性更好。