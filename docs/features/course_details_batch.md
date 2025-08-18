# 課程詳情批次查詢（Course Details Batch Query）

## 功能概述

提供根據課程 ID 列表批次查詢課程詳細資訊的功能，支援 Bubble.io 前端在使用者選擇技能後顯示相關課程。這是專為前端課程展示頁面設計的高效能批次查詢 API。

## 使用情境

### Bubble.io 前端流程
```
1. Gap Analysis 回傳 SkillSearchQueries
   └── 包含 available_course_ids 列表（已排序）

2. 使用者點擊某個技能查看課程
   └── 建立 SkillQuery 物件
       └── 儲存 available_course_ids

3. 呼叫課程詳情 API ⭐ (本文檔功能)
   └── 輸入: course ID 列表
   └── 輸出: 完整課程資訊

4. 導航到課程詳情頁面
   └── 傳遞查詢結果作為參數

5. 在 Repeating Group 顯示課程
   └── 顯示名稱、描述、價格、圖片等
```

## API 端點

`POST /api/v1/courses/get-by-ids`

## 核心功能

### 1. 批次查詢
- 支援一次查詢多個課程 ID（最多 100 個）
- 自動過濾無效或不存在的 ID
- 保持 Gap Analysis 的排序順序返回結果

### 2. 完整課程資訊
返回每個課程的詳細資訊：
- **基本資訊**：ID、名稱、描述
- **提供者資訊**：標準化名稱、Logo URL
- **價格資訊**：價格、貨幣
- **媒體資源**：課程圖片、追蹤連結
- **分類資訊**：課程類型（標準化）

### 3. 效能優化
- 資料庫連線池複用
- 批次查詢減少資料庫往返
- 結果快取（15 分鐘有效期）

### 4. 錯誤處理
- 優雅處理部分失敗（返回可查詢到的課程）
- 查無任何課程時提供 fallback URL
- 明確標示找不到的課程 ID

## 技術實作

### 處理流程
```
請求接收
    │
    ├─> 預處理 (preparation)
    │   ├─> 驗證輸入（ID 列表長度 1-100）
    │   ├─> 驗證 ID 格式
    │   └─> 應用 max_courses 限制（只處理前 N 個）
    │
    ├─> 快取操作 (cache_operations)
    │   ├─> 並行檢查已快取的課程
    │   └─> 分離需查詢的 ID
    │
    ├─> 資料庫操作 (db_operations)
    │   ├─> 批次 SELECT 查詢（只查詢未快取的）
    │   ├─> 使用 array_position 保持原始順序
    │   └─> 保留 Gap Analysis 的排序
    │
    └─> 處理與回應 (processing)
        ├─> 格式化課程資料
        ├─> 處理描述截斷
        ├─> 標記未找到的 ID
        ├─> 生成時間追蹤報告
        └─> 返回結果
```

### 關鍵技術組件
1. **CourseSearchService**
   - 新增 `get_courses_by_ids()` 方法
   - 複用現有連線池
   - 整合快取機制

2. **資料庫查詢優化**
   - 使用 `WHERE id = ANY($1::text[])` 進行批次查詢
   - 使用 `array_position($1::text[], id)` 保持輸入順序
   - 索引優化確保快速查詢

3. **快取策略**
   - 課程資料快取 15 分鐘
   - 快取鍵包含描述模式參數
   - LRU 策略管理記憶體使用

## 使用範例

### 請求範例

```python
import requests

# 從 Gap Analysis 取得的課程 ID 列表
course_ids = [
    "coursera_crse:v1-2598",
    "coursera_crse:v1-2599",
    "coursera_spzn:react-basics",
    "coursera_crse:v1-2601",
    "coursera_crse:v1-2602"
]

response = requests.post(
    "https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io/api/v1/courses/get-by-ids",
    headers={"X-API-Key": "YOUR_API_KEY"},
    json={
        "course_ids": course_ids,
        "max_courses": 20,               # 可選：最多查詢前 20 個 ID（最大 100）
        "full_description": False,       # 可選：返回截斷的描述
        "description_max_length": 200,   # 可選：描述截斷至 200 字元
        "enable_time_tracking": True     # 可選：啟用時間追蹤（預設開啟） 
    }
)
```

### 回應範例（成功）

```json
{
  "success": true,
  "courses": [
    {
      "id": "coursera_crse:v1-2598",
      "name": "React - The Complete Guide",
      "description": "Learn React.js from the ground up and build modern, reactive web applications with the React framework...",
      "provider": "Academind",
      "provider_standardized": "Academind",
      "provider_logo_url": "https://example.com/academind-logo.png",
      "price": 49.99,
      "currency": "USD",
      "image_url": "https://example.com/react-course-image.jpg",
      "affiliate_url": "https://www.coursera.org/learn/react-complete-guide?aid=affiliate123",
      "course_type": "course",
      "duration": "40 hours",
      "difficulty": "Intermediate",
      "rating": 4.7,
      "enrollment_count": 150000
    },
    {
      "id": "coursera_crse:v1-2599",
      "name": "Advanced React and Redux",
      "description": "Master React v16.6.3 and Redux with React Router, Webpack, and Create-React-App...",
      "provider": "Stephen Grider",
      "provider_standardized": "Stephen Grider",
      "provider_logo_url": "https://example.com/grider-logo.png",
      "price": 84.99,
      "currency": "USD",
      "image_url": "https://example.com/advanced-react-image.jpg",
      "affiliate_url": "https://www.coursera.org/learn/advanced-react?aid=affiliate123",
      "course_type": "course",
      "duration": "52 hours",
      "difficulty": "Advanced",
      "rating": 4.6,
      "enrollment_count": 85000
    }
  ],
  "total_found": 2,
  "requested_count": 5,
  "processed_count": 5,
  "skipped_count": 0,
  "not_found_ids": [
    "coursera_crse:v1-2601",
    "coursera_crse:v1-2602"
  ],
  "cache_hit_rate": 0.4,
  "from_cache_count": 1,
  "all_not_found": false,
  "fallback_url": null,
  "time_tracking": {
    "enabled": true,
    "total_ms": 125,
    "timeline": [
      {
        "task": "preparation",
        "duration_ms": 3,
        "description": "Input validation and limits"
      },
      {
        "task": "cache_operations",
        "duration_ms": 15,
        "description": "Check cached courses"
      },
      {
        "task": "db_operations",
        "duration_ms": 85,
        "description": "Query uncached courses"
      },
      {
        "task": "processing",
        "duration_ms": 22,
        "description": "Format and build response"
      }
    ],
    "summary": {
      "preparation_pct": 2.4,
      "cache_operations_pct": 12.0,
      "db_operations_pct": 68.0,
      "processing_pct": 17.6
    }
  },
  "error": {
    "code": "",
    "message": "",
    "details": ""
  }
}
```

### 回應範例（使用 max_courses 限制）

```json
{
  "success": true,
  "data": {
    "courses": [
      // ... 3 個課程資料
    ],
    "total_found": 3,
    "not_found_ids": [],
    "query_info": {
      "requested_count": 10,      # 請求了 10 個 ID
      "processed_count": 3,        # 只處理前 3 個（max_courses=3）
      "found_count": 3,            # 找到 3 個
      "not_found_count": 0,        # 沒有查不到的
      "skipped_count": 7,          # 跳過了 7 個
      "all_not_found": false,
      "cache_hit_rate": 0.67
    }
  },
  "error": {
    "has_error": false
  },
  "metadata": {
    "query_time_ms": 45,
    "from_cache_count": 2,
    "from_db_count": 1,
    "time_tracking": {
      "enabled": true,
      "total_ms": 45,
      "timeline": [
        {"task": "preparation", "duration_ms": 2},
        {"task": "cache_operations", "duration_ms": 15},
        {"task": "db_operations", "duration_ms": 20},
        {"task": "processing", "duration_ms": 8}
      ],
      "summary": {
        "preparation_pct": 4.4,
        "cache_pct": 33.3,
        "db_pct": 44.4,
        "processing_pct": 17.8
      }
    }
  }
}
```

### 回應範例（查無任何課程）

```json
{
  "success": true,
  "data": {
    "courses": [],
    "total_found": 0,
    "not_found_ids": [
      "invalid_id_1",
      "invalid_id_2"
    ],
    "query_info": {
      "requested_count": 2,
      "found_count": 0,
      "not_found_count": 2,
      "all_not_found": true,
      "cache_hit_rate": 0.0
    }
  },
  "error": {
    "has_error": false,
    "code": "",
    "message": "",
    "details": ""
  },
  "metadata": {
    "query_time_ms": 45,
    "from_cache_count": 0,
    "from_db_count": 0,
    "fallback_url": "https://imp.i384100.net/mOkdyq"
  },
  "timestamp": "2025-08-17T14:30:00.000Z"
}
```

## 資料模型

### CourseDetailsBatchRequest
```python
{
  "course_ids": list[str],                  # 必填：課程 ID 列表（1-100 個）
  "max_courses": int | None = None,         # 可選：最多查詢幾個課程（1-100，只查詢前 N 個 ID）
  "full_description": bool = True,          # 可選：是否返回完整描述
  "description_max_length": int = 500,      # 可選：描述截斷長度-字元數（當 full_description=false 時生效）
  "enable_time_tracking": bool = True       # 可選：啟用時間追蹤（預設開啟）
}
```

### CourseDetail
```python
{
  "id": str,                        # 課程唯一識別碼
  "name": str,                      # 課程名稱
  "description": str,               # 課程描述（可截斷）
  "provider": str,                  # 提供者名稱
  "provider_standardized": str,     # 標準化提供者名稱
  "provider_logo_url": str,         # 提供者 Logo URL
  "price": float,                   # 課程價格
  "currency": str,                  # 貨幣代碼
  "image_url": str,                 # 課程圖片 URL
  "affiliate_url": str,             # 聯盟行銷連結
  "course_type": str,               # 標準化課程類型
  "duration": str | None,           # 課程時長（可選）
  "difficulty": str | None,         # 難度等級（可選）
  "rating": float | None,           # 評分（可選）
  "enrollment_count": int | None    # 註冊人數（可選）
}
```

### CourseDetailsBatchResponse (簡化版)
```python
{
  "success": bool,                      # 是否成功
  "courses": list[CourseDetail],        # 課程列表（扁平結構）
  "total_found": int,                   # 找到的課程總數
  "requested_count": int,               # 請求的 ID 數量
  "processed_count": int,               # 實際處理的 ID 數量  
  "skipped_count": int,                 # 跳過的 ID 數量
  "not_found_ids": list[str],           # 未找到的課程 ID
  "cache_hit_rate": float,              # 快取命中率 (0-1)
  "from_cache_count": int,              # 從快取返回的課程數
  "all_not_found": bool,                # 是否全部都找不到
  "fallback_url": str | None,           # 當全部找不到時的備用 URL
  "time_tracking": dict | None,         # 時間追蹤資訊（可選）
  "error": dict                         # 錯誤資訊
}
```

## Bubble.io 整合指南

### 1. API Connector 設定
```
Name: Get Course Details
Method: POST
URL: https://[your-domain]/api/v1/courses/get-by-ids
Headers:
  - X-API-Key: [YOUR_API_KEY]
  - Content-Type: application/json
Body (JSON):
{
  "course_ids": <course_ids>,
  "max_courses": 20,
  "full_description": false,
  "description_max_length": 200,
  "enable_time_tracking": false   # Bubble.io 建議關閉以減少回應大小
}
```

### 2. Workflow 設定
```
1. Trigger: When SkillQuery is clicked
2. Action 1: Set state course_ids = Current cell's SkillQuery's available_course_ids
3. Action 2: API Call - Get Course Details
   - course_ids = This page's course_ids
   - max_courses = 20 (optional)
   - full_description = false (optional)
4. Action 3: Check if courses returned
   - If query_info.all_not_found = true
   - Navigate to fallback_url
5. Action 4: Display data in Repeating Group
   - Type: API Response's courses
   - Data source: Result of step 2's courses
```

### 3. Repeating Group 顯示
```
設定 Repeating Group:
- Type of content: API.Get Course Details's courses
- Data source: API Response's courses

Cell 內容：
- Text: Current cell's course's name
- Text: Current cell's course's description
- Image: Current cell's course's image_url
- Text: Current cell's course's price
- Link: Current cell's course's affiliate_url
```

### 4. 處理查無課程情況
```
Condition: When API Response's query_info's all_not_found is true
Action: Navigate to external URL
URL: API Response's metadata's fallback_url
```

## 效能指標

### 回應時間目標
- **P50**：< 150ms（快取命中）
- **P95**：< 300ms（資料庫查詢）
- **P99**：< 500ms

### 吞吐量
- 支援每秒 100 個請求
- 批次大小：1-100 個課程 ID
- 並發請求：最多 20 個

### 快取效能
- 命中率目標：> 60%
- 快取有效期：15 分鐘
- 記憶體使用：< 100MB

## 限制與注意事項

### API 限制
- 單次請求最多 100 個課程 ID
- 超過限制返回 400 錯誤
- 空列表返回成功但空陣列（不是錯誤）

### 資料限制
- 課程描述預設完整返回
- 可透過 `full_description=false` 截斷描述
- 截斷長度可透過 `description_max_length` 控制
- 截斷時會在單詞邊界進行，避免斷詞
- 某些選填欄位可能為 null

### 效能考量
- 大量 ID 查詢可能稍慢（建議使用 `max_courses` 限制）
- 快取預熱需要時間
- 高峰期可能有輕微延遲

### 參數詳細說明

#### max_courses 行為
- **範圍**：1-100
- **行為**：只查詢 `course_ids` 列表的前 N 個 ID，而非查詢全部再截斷
- **效能優勢**：減少資料庫查詢和網路傳輸
- **範例**：
  - 輸入 50 個 ID，`max_courses=20` → 只查詢前 20 個
  - 輸入 10 個 ID，`max_courses=20` → 查詢全部 10 個

#### description_max_length 行為  
- **單位**：字元數（characters）
- **計算方式**：UTF-8 字元，包含所有字元（字母、數字、空格、標點符號）
- **截斷邏輯**：
  - 在單詞邊界截斷，避免斷詞
  - 自動加上 "..." 結尾
- **範例**：
  - "Hello World!" = 12 字元
  - "測試中文" = 4 字元
  - 截斷時會保持完整單詞

## 錯誤處理

### 常見錯誤
| 錯誤碼 | 說明 | 解決方案 |
|--------|------|----------|
| VALIDATION_ERROR | 輸入驗證失敗 | 檢查 ID 列表格式和長度 |
| TOO_MANY_IDS | 超過 100 個 ID | 分批查詢或使用 max_courses |
| DATABASE_ERROR | 資料庫連線錯誤 | 稍後重試 |
| INVALID_ID_FORMAT | ID 格式錯誤 | 檢查 ID 格式 |

### 特殊情況處理

#### 空列表請求
- 不再返回錯誤，而是返回成功但空結果
- `all_not_found` 設為 true
- 提供 `fallback_url` 供前端導向

#### 部分失敗處理
- API 會返回所有能查詢到的課程
- `not_found_ids` 欄位列出未找到的 ID
- 不會因為部分 ID 無效而完全失敗

#### 全部查無處理
- 返回成功狀態（`success: true`）
- `courses` 為空陣列
- `query_info.all_not_found` 設為 true
- `metadata.fallback_url` 提供 Coursera 主頁連結

## 監控與維護

### 監控配置（與 Gap Analysis API 一致）
```
LOG_LEVEL=INFO
MONITORING_ENABLED=false
LIGHTWEIGHT_MONITORING=true
```

使用輕量級監控策略：
- 記錄基本 metrics（請求數、回應時間、錯誤率）
- 不使用 Application Insights 詳細遙測
- 時間追蹤開銷 < 1ms（4 個主要區塊）
- 小於 50ms 的操作不單獨追蹤



### 關鍵指標
- 請求量和回應時間
- 快取命中率
- 資料庫查詢效能
- 錯誤率和類型分布
- 全部查無的頻率

### 日誌記錄
- 所有請求和回應
- 快取命中/未命中
- 資料庫查詢時間
- 錯誤詳情
- 查無課程的情況

## 未來改進方向

### 短期優化
- **批次快取更新**：預載熱門課程
- **壓縮回應**：支援 gzip 壓縮
- **欄位選擇**：允許客戶端選擇需要的欄位

### 中期增強
- **即時價格更新**：整合即時價格資訊
- **個性化排序**：根據使用者偏好調整順序
- **相關課程推薦**：當課程不足時補充相似課程

### 長期願景
- **GraphQL 支援**：更靈活的資料查詢
- **WebSocket 訂閱**：即時課程更新通知
- **批次操作 API**：支援更多批次操作

## 相關功能

- [差距分析](gap_analysis.md) - 生成 available_course_ids（已排序）
- [課程搜尋](course_search.md) - 語意搜尋課程
- [資料庫架構](../production/DATABASE_SCHEMA.md) - courses 表格結構