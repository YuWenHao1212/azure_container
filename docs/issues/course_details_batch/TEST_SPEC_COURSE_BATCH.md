# 測試規格文檔 - Course Batch Query API

## 文檔資訊
- **版本**: 1.0.0
- **建立日期**: 2025-08-18
- **文檔名稱**: TEST_SPEC_COURSE_BATCH.md
- **維護者**: AI Resume Advisor Team
- **測試總數**: 21 個測試
  - 單元測試: 10 個
  - 整合測試: 9 個 (5個規格測試 + 4個額外測試)
  - 效能測試: 2 個

## 測試案例編號系統

### 編號格式
```
API-CDB-[序號]-[類型]

範例: API-CDB-001-UT
```

### 編號分配
| 序號範圍 | 測試類型 | 數量 | 說明 |
|----------|----------|------|------|
| 001-005 | 單元測試(UT) | 5 | CourseSearchService.get_courses_by_ids 方法測試（規格） |
| 006-010 | 單元測試(UT) | 5 | 額外的單元測試（處理錯誤、快取、時間追蹤等） |
| 001-005 | 整合測試(IT) | 5 | API 端點整合測試（規格） |
| 006-009 | 整合測試(IT) | 4 | 額外的整合測試（認證、驗證、預設值） |
| 001-002 | 效能測試(PT) | 2 | 批次查詢效能測試 |

## 單元測試 (10個)

### 規格測試 (5個)

### API-CDB-001-UT: 基本批次查詢功能
- **名稱**: 批次查詢多個課程 ID
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證基本批次查詢功能正常運作
- **測試資料**: 
  ```yaml
  input:
    course_ids: 
      - "coursera_crse:v1-2598"
      - "coursera_crse:v1-2599"
      - "coursera_crse:v1-2600"
    max_courses: null
    full_description: true
    description_max_length: 500
    enable_time_tracking: false
  expected:
    success: true
    total_found: 3
    courses_count: 3
  ```
- **判斷標準**: 
  - 成功返回所有查詢的課程
  - 課程順序與輸入順序一致
  - 所有欄位正確填充

### API-CDB-002-UT: max_courses 限制測試
- **名稱**: 驗證 max_courses 參數限制查詢數量
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 確認 max_courses 只處理前 N 個 ID
- **測試資料**:
  ```yaml
  input:
    course_ids: [10 個課程 ID]
    max_courses: 3
  expected:
    processed_count: 3
    skipped_count: 7
    found_count: <= 3
  ```
- **判斷標準**: 
  - 只查詢前 3 個 ID
  - skipped_count 正確計算
  - 資料庫查詢不包含跳過的 ID

### API-CDB-003-UT: 描述截斷測試
- **名稱**: 驗證描述文字截斷功能
- **優先級**: P1
- **類型**: 單元測試
- **測試目標**: 確認描述正確截斷並保持單詞邊界
- **測試資料**:
  ```yaml
  input:
    course_ids: ["coursera_crse:v1-2598"]
    full_description: false
    description_max_length: 100
  expected:
    description_length: <= 100
    description_ends_with: "..."
    word_boundary_preserved: true
  ```
- **判斷標準**: 
  - 描述長度不超過限制
  - 在單詞邊界截斷
  - 加上 "..." 結尾

### API-CDB-004-UT: 快取命中測試
- **名稱**: 驗證快取機制正常運作
- **優先級**: P1
- **類型**: 單元測試
- **測試目標**: 確認相同查詢從快取返回
- **測試步驟**:
  1. 第一次查詢課程 ID 列表
  2. 立即重複相同查詢
  3. 驗證第二次查詢從快取返回
- **判斷標準**: 
  - cache_hit_rate > 0
  - from_cache_count > 0
  - 查詢時間顯著降低

### API-CDB-005-UT: 排序保持測試
- **名稱**: 驗證結果保持輸入順序
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 確認使用 array_position 保持順序
- **測試資料**:
  ```yaml
  input:
    course_ids: 
      - "coursera_crse:v1-2600"  # 第三個
      - "coursera_crse:v1-2598"  # 第一個
      - "coursera_crse:v1-2599"  # 第二個
  expected:
    courses_order: [2600, 2598, 2599]
  ```
- **判斷標準**: 
  - 返回順序與輸入順序完全一致
  - 不受資料庫自然順序影響

### 額外測試 (5個)

### API-CDB-006-UT: Not Found 課程處理
- **名稱**: 驗證未找到課程的處理
- **優先級**: P1
- **類型**: 單元測試
- **測試目標**: 確認正確標記未找到的課程 ID
- **判斷標準**: 
  - 成功返回找到的課程
  - not_found_ids 列表正確

### API-CDB-007-UT: 時間追蹤啟用測試
- **名稱**: 驗證時間追蹤功能
- **優先級**: P2
- **類型**: 單元測試
- **測試目標**: 確認時間追蹤資訊完整且正確
- **判斷標準**: 
  - timeline 包含 4 個任務區塊
  - 每個任務有有效的時間資訊

### API-CDB-008-UT: 空列表驗證
- **名稱**: 驗證空課程 ID 列表
- **優先級**: P1
- **類型**: 單元測試
- **測試目標**: 確認空列表觸發驗證錯誤
- **判斷標準**: 
  - 拋出 ValidationError

### API-CDB-009-UT: 資料庫錯誤處理
- **名稱**: 驗證資料庫錯誤的優雅處理
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 確認資料庫錯誤不會導致崩潰
- **判斷標準**: 
  - 返回 success: false
  - 包含錯誤訊息

### API-CDB-010-UT: 快取重複測試
- **名稱**: 驗證快取機制運作（與 004 不同的測試方式）
- **優先級**: P2
- **類型**: 單元測試
- **測試目標**: 確認資料庫只被調用一次
- **判斷標準**: 
  - mock 只被調用一次
  - 兩次查詢結果相同

## 整合測試 (9個)

### 規格測試 (5個)

### API-CDB-001-IT: API 端點基本功能
- **名稱**: POST /api/v1/courses/get-by-ids 基本功能
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證 API 端點正常運作
- **測試資料**:
  ```json
  {
    "course_ids": [
      "coursera_crse:v1-2598",
      "coursera_crse:v1-2599"
    ],
    "enable_time_tracking": true
  }
  ```
- **判斷標準**: 
  - HTTP 200 回應
  - success: true
  - 包含 time_tracking 資訊
  - 4 個時間區塊都存在

### API-CDB-002-IT: 邊界值測試
- **名稱**: 測試 1-100 個 ID 的邊界情況
- **優先級**: P1
- **類型**: 整合測試
- **測試目標**: 驗證最小和最大輸入限制
- **測試案例**:
  1. 1 個 ID（最小值）
  2. 100 個 ID（最大值）
  3. 101 個 ID（超過限制，應返回錯誤）
  4. 0 個 ID（空列表）
- **判斷標準**: 
  - 1-100 個正常處理
  - 超過 100 個返回驗證錯誤
  - 空列表返回成功但空結果

### API-CDB-003-IT: 錯誤處理測試
- **名稱**: 驗證各種錯誤情況的處理
- **優先級**: P1
- **類型**: 整合測試
- **測試目標**: 確認錯誤優雅處理
- **測試案例**:
  1. 無效的課程 ID 格式
  2. 不存在的課程 ID
  3. 混合有效和無效 ID
  4. 資料庫連線失敗（模擬）
- **判斷標準**: 
  - 部分失敗返回找到的課程
  - not_found_ids 正確標記
  - 錯誤訊息清晰

### API-CDB-004-IT: 時間追蹤測試
- **名稱**: 驗證時間追蹤功能完整性
- **優先級**: P2
- **類型**: 整合測試
- **測試目標**: 確認時間追蹤資訊正確
- **測試資料**:
  ```json
  {
    "course_ids": ["coursera_crse:v1-2598"],
    "enable_time_tracking": true
  }
  ```
- **判斷標準**: 
  - timeline 包含 4 個任務
  - 每個任務有 duration_ms
  - summary 百分比加總約 100%
  - total_ms 等於各任務總和

### API-CDB-005-IT: 查無任何課程測試
- **名稱**: 全部課程都找不到的情況
- **優先級**: P2
- **類型**: 整合測試
- **測試目標**: 驗證查無課程時的 fallback 處理
- **測試資料**:
  ```json
  {
    "course_ids": ["invalid_id_1", "invalid_id_2"]
  }
  ```
- **判斷標準**: 
  - success: true（不是錯誤）
  - all_not_found: true
  - fallback_url 提供
  - courses 為空陣列

### 額外測試 (4個)

### API-CDB-006-IT: 認證要求測試
- **名稱**: 驗證 API Key 認證要求
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 確認 API 需要有效的認證
- **測試案例**:
  1. 無 API Key - 應返回 401
  2. 無效 API Key - 應返回 401
- **判斷標準**: 
  - 正確的 HTTP 狀態碼
  - 適當的錯誤訊息

### API-CDB-007-IT: 請求驗證測試
- **名稱**: 驗證請求參數驗證
- **優先級**: P1
- **類型**: 整合測試
- **測試目標**: 確認參數驗證正常運作
- **測試案例**:
  1. description_max_length < 50 - 應返回 422
  2. max_courses < 1 - 應返回 422
  3. max_courses > 100 - 應返回 422
- **判斷標準**: 
  - 返回 422 驗證錯誤

### API-CDB-008-IT: 預設值測試
- **名稱**: 驗證預設值正確套用
- **優先級**: P2
- **類型**: 整合測試
- **測試目標**: 確認預設參數值正確
- **判斷標準**: 
  - full_description 預設為 true
  - description_max_length 預設為 500
  - enable_time_tracking 預設為 true

### API-CDB-009-IT: Error Handler 整合測試
- **名稱**: 驗證統一錯誤處理機制
- **優先級**: P1
- **類型**: 整合測試
- **測試目標**: 確認使用 @handle_api_errors decorator
- **判斷標準**: 
  - 錯誤回應格式符合統一標準
  - 包含 error code 和 message

## 效能測試 (2個)

### API-CDB-001-PT: P50 響應時間測試
- **名稱**: 測試中位數響應時間（真實資料庫）
- **優先級**: P0
- **類型**: 效能測試
- **測試目標**: 驗證快取命中效能 P50 < 150ms
- **測試準備**:
  ```python
  # 從資料庫取得 5 個真實課程 ID
  query = """
    SELECT id FROM courses 
    WHERE platform = 'coursera' 
    AND embedding IS NOT NULL
    LIMIT 5
  """
  real_course_ids = await conn.fetch(query)
  ```
- **測試方法**:
  1. **預熱階段**：
     - 執行一次查詢，建立快取
     - 確認 cache_hit_rate = 0（首次查詢）
  2. **測試階段**：
     - 連續執行 20 次相同查詢
     - 記錄每次響應時間
  3. **分析階段**：
     - 計算 P50、P90、P95 響應時間
     - 驗證 cache_hit_rate = 1.0
- **測試資料**:
  ```yaml
  course_ids: [實際從 DB 查詢的 5 個 ID]
  enable_time_tracking: true
  full_description: true
  ```
- **判斷標準**: 
  - P50 < 150ms（快取命中）
  - P90 < 200ms
  - cache_hit_rate = 1.0（第 2-20 次查詢）
  - from_cache_count = 5（每次查詢）

### API-CDB-002-PT: 大批量查詢測試
- **名稱**: 測試 100 個 ID 的查詢效能（真實資料庫）
- **優先級**: P1
- **類型**: 效能測試
- **測試目標**: 驗證大批量查詢在不同快取狀態下的效能

#### 測試準備
```python
# 從資料庫取得 100 個真實課程 ID
query = """
  SELECT id FROM courses 
  WHERE platform = 'coursera' 
  AND embedding IS NOT NULL
  ORDER BY RANDOM()
  LIMIT 100
"""
real_100_course_ids = await conn.fetch(query)
# 儲存到 test/fixtures/course_batch/performance_course_ids.json
```

#### 子測試 1: 冷啟動效能
- **目標**: 測試無快取狀態下的查詢效能
- **步驟**:
  1. 清除所有快取
  2. 查詢 100 個課程 ID
  3. 記錄總時間和各階段時間分配
- **預期結果**:
  ```yaml
  total_time: < 500ms
  cache_hit_rate: 0
  from_cache_count: 0
  time_breakdown:
    preparation: < 5%
    cache_operations: < 10%
    db_operations: > 70%
    processing: < 15%
  ```

#### 子測試 2: 部分快取命中
- **目標**: 測試 50% 快取命中率的效能
- **步驟**:
  1. 清除所有快取
  2. 先查詢前 50 個 ID（建立快取）
  3. 查詢全部 100 個 ID（50 個從快取，50 個從 DB）
  4. 分析快取命中率和時間分配
- **預期結果**:
  ```yaml
  total_time: < 300ms
  cache_hit_rate: 0.5
  from_cache_count: 50
  time_breakdown:
    preparation: < 5%
    cache_operations: 20-30%
    db_operations: 50-60%
    processing: < 15%
  ```

#### 子測試 3: 完全快取命中
- **目標**: 測試 100% 快取命中的效能
- **步驟**:
  1. 預熱：查詢全部 100 個 ID
  2. 再次查詢相同 100 個 ID
  3. 驗證全部從快取返回
- **預期結果**:
  ```yaml
  total_time: < 100ms
  cache_hit_rate: 1.0
  from_cache_count: 100
  time_breakdown:
    preparation: < 10%
    cache_operations: > 70%
    db_operations: 0%
    processing: < 20%
  ```

#### 時間分析與視覺化
- **資料來源**: API response 的 `time_tracking` 欄位
- **分析內容**:
  ```json
  {
    "timeline": [
      {"task_name": "preparation", "duration_ms": 2},
      {"task_name": "cache_operations", "duration_ms": 15},
      {"task_name": "db_operations", "duration_ms": 280},
      {"task_name": "processing", "duration_ms": 8}
    ],
    "summary": {
      "total_ms": 305,
      "preparation_pct": 0.66,
      "cache_operations_pct": 4.92,
      "db_operations_pct": 91.80,
      "processing_pct": 2.62
    }
  }
  ```
- **Gantt Chart 生成**:
  - X 軸：時間（毫秒）
  - Y 軸：任務階段
  - 顏色編碼：
    - preparation: 藍色
    - cache_operations: 綠色
    - db_operations: 橙色
    - processing: 紫色

## 測試資料準備

### Fixtures 結構
```
test/fixtures/course_batch/
├── test_data.json                  # 基本測試資料
├── course_ids.json                 # 20 組不同的課程 ID 組合
├── mock_courses.json               # 模擬課程資料
├── performance_course_ids.json     # 真實資料庫查詢的課程 ID（效能測試用）
└── performance_results.json        # 效能測試結果記錄
```

### 效能測試資料準備腳本
```python
# scripts/prepare_performance_test_data.py
import asyncio
import json
import asyncpg
from pathlib import Path

async def prepare_test_data():
    """準備效能測試所需的真實課程 ID"""
    
    # 連接資料庫
    conn = await asyncpg.connect(
        host=os.getenv('POSTGRES_HOST'),
        database=os.getenv('POSTGRES_DATABASE'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
        ssl='require'
    )
    
    try:
        # 取得 5 個課程 ID（P50 測試用）
        small_batch = await conn.fetch("""
            SELECT id, name FROM courses 
            WHERE platform = 'coursera' 
            AND embedding IS NOT NULL
            LIMIT 5
        """)
        
        # 取得 100 個課程 ID（大批量測試用）
        large_batch = await conn.fetch("""
            SELECT id, name FROM courses 
            WHERE platform = 'coursera' 
            AND embedding IS NOT NULL
            ORDER BY RANDOM()
            LIMIT 100
        """)
        
        # 儲存到 fixture 檔案
        test_data = {
            "small_batch": {
                "description": "5 course IDs for P50 response time test",
                "course_ids": [row['id'] for row in small_batch],
                "course_names": {row['id']: row['name'] for row in small_batch}
            },
            "large_batch": {
                "description": "100 course IDs for batch performance test",
                "course_ids": [row['id'] for row in large_batch],
                "count": len(large_batch)
            },
            "generated_at": datetime.now().isoformat(),
            "database": os.getenv('POSTGRES_DATABASE')
        }
        
        # 寫入檔案
        output_path = Path('test/fixtures/course_batch/performance_course_ids.json')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(test_data, f, indent=2)
            
        print(f"✅ Saved {len(small_batch)} + {len(large_batch)} course IDs to {output_path}")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(prepare_test_data())
```

### 課程 ID 範例
```json
{
  "valid_ids": [
    "coursera_crse:v1-2598",
    "coursera_crse:v1-2599",
    "coursera_spzn:react-basics"
  ],
  "invalid_ids": [
    "invalid_id_1",
    "not_exist_id"
  ],
  "mixed_ids": [
    "coursera_crse:v1-2598",
    "invalid_id_1",
    "coursera_crse:v1-2599"
  ]
}
```

## 執行指令

### 單元測試
```bash
pytest test/unit/test_course_batch.py -v
```

### 整合測試
```bash
pytest test/integration/test_course_batch_integration.py -v
```

### 效能測試
```bash
pytest test/performance/test_course_batch_performance.py -v
```

### 完整測試
```bash
pytest test/unit/test_course_batch.py test/integration/test_course_batch_integration.py test/performance/test_course_batch_performance.py -v
```

## 成功標準

1. **功能完整性**: 所有單元測試和整合測試通過
2. **效能達標**: 
   - P50 < 150ms（快取命中）
   - P95 < 300ms（資料庫查詢）
3. **程式碼品質**: 
   - Ruff 檢查通過
   - 測試覆蓋率 > 80%
4. **文檔完整**: 
   - 測試規格清晰
   - 測試資料完整

---

**文檔版本**: 1.0.0  
**最後更新**: 2025-08-18  
**下一步**: 實作測試程式碼和 fixtures