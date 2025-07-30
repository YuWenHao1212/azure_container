# 課程搜尋功能

## 功能概述

根據技能差距智能推薦 Coursera 平台上的相關課程，協助求職者快速提升所需技能。

## API 端點

`POST /api/v1/search-relevant-courses`

## 核心功能

### 1. 智能搜尋
- **語義匹配**：理解技能含義
- **相關性排序**：最相關課程優先
- **多維度過濾**：類型、語言、難度
- **個人化推薦**：基於背景調整

### 2. 課程分類
- **單一課程**（Course）：4-6 週完成
- **專項課程**（Specialization）：3-6 個月系列
- **專業證書**（Professional Certificate）：職業導向
- **指導專案**（Guided Project）：2 小時實作
- **學位課程**（Degree）：完整學位

### 3. 豐富資訊
- 課程名稱與連結
- 提供機構
- 涵蓋技能
- 相似度評分
- 預估時長

## 技術實作

### 資料來源
- **課程資料庫**：20,000+ Coursera 課程
- **更新頻率**：每月更新
- **資料結構**：SQLite 本地資料庫
- **索引優化**：全文搜尋支援

### 搜尋演算法
```python
def search_courses(keywords, filters):
    # 1. 向量化關鍵字
    keyword_embeddings = embed_keywords(keywords)
    
    # 2. 計算相似度
    similarities = compute_similarities(
        keyword_embeddings, 
        course_embeddings
    )
    
    # 3. 應用過濾條件
    filtered_courses = apply_filters(courses, filters)
    
    # 4. 排序並返回
    return sort_by_relevance(filtered_courses, similarities)
```

### 效能優化
- 預計算課程嵌入向量
- 快取熱門搜尋結果
- 批次處理請求
- 索引優化查詢

## 使用範例

### 請求範例
```python
import requests

response = requests.post(
    "https://airesumeadvisor-fastapi.azurewebsites.net/api/v1/search-relevant-courses",
    params={"code": "YOUR_HOST_KEY"},
    json={
        "keywords": ["Python", "Machine Learning", "Data Science"],
        "filters": {
            "max_results": 10,
            "course_type": "specialization",
            "language": "en"
        }
    }
)
```

### 回應範例
```json
{
  "success": true,
  "data": {
    "courses": [
      {
        "course_name": "Python for Data Science and Machine Learning",
        "course_id": "python-data-science-ml",
        "url": "https://www.coursera.org/specializations/python-data-science-ml",
        "provider": "University of Michigan",
        "skills": ["Python", "Machine Learning", "Data Analysis", "NumPy", "Pandas"],
        "similarity_score": 95.2,
        "course_type_standard": "specialization",
        "duration": "5 months at 10 hours/week",
        "rating": 4.7,
        "enrolled_students": "250,000+"
      },
      {
        "course_name": "Applied Data Science with Python",
        "course_id": "data-science-python",
        "url": "https://www.coursera.org/specializations/data-science-python",
        "provider": "University of Michigan",
        "skills": ["Python", "Data Science", "Machine Learning", "Visualization"],
        "similarity_score": 92.8,
        "course_type_standard": "specialization",
        "duration": "5 months at 7 hours/week"
      }
    ],
    "search_metadata": {
      "total_found": 156,
      "returned": 10,
      "search_time_ms": 245,
      "filters_applied": ["course_type", "language"]
    }
  },
  "error": {
    "code": "",
    "message": ""
  }
}
```

## 搜尋過濾器

### 課程類型過濾
| 類型 | 說明 | 典型時長 |
|------|------|----------|
| course | 單一主題課程 | 4-6 週 |
| specialization | 系列課程 | 3-6 個月 |
| professional | 職業證書 | 3-9 個月 |
| project | 實作專案 | 1-2 小時 |
| degree | 學位課程 | 1-4 年 |

### 其他過濾選項
- **語言**：en, zh, es, fr 等
- **難度**：beginner, intermediate, advanced
- **提供者**：大學或企業名稱
- **評分**：最低評分要求

## 相似度計算

### 演算法說明
1. **文本嵌入**：使用 Azure Embedding API
2. **餘弦相似度**：計算向量夾角
3. **權重調整**：
   - 課程標題：40%
   - 技能標籤：35%
   - 課程描述：25%

### 分數解讀
- **90-100**：高度相關，強烈推薦
- **75-89**：相關性良好，建議考慮
- **60-74**：部分相關，可作補充
- **< 60**：相關性較低

## 資料庫架構

### 課程資料表
```sql
CREATE TABLE courses (
    course_id TEXT PRIMARY KEY,
    course_name TEXT NOT NULL,
    url TEXT NOT NULL,
    provider TEXT,
    skills TEXT,  -- JSON array
    course_type TEXT,
    language TEXT,
    embedding BLOB  -- 預計算的向量
);
```

### 索引優化
- 全文搜尋索引
- 課程類型索引
- 語言索引
- 提供者索引

## 效能指標

### 搜尋效能
- 平均回應時間：0.8 秒
- P95 回應時間：< 2 秒
- 並發搜尋：50 req/s

### 準確度指標
- 相關性準確率：> 85%
- 使用者點擊率：> 40%
- 課程完成率追蹤

## 最佳實踐

### 關鍵字選擇
1. 使用具體技能名稱
2. 包含相關認證名稱
3. 混合不同層級技能
4. 考慮同義詞變化

### 結果應用
1. 優先學習高相關課程
2. 建立學習路徑
3. 追蹤學習進度
4. 更新履歷技能

## 資料維護

### 更新機制
- 每月同步 Coursera 資料
- 自動檢測新課程
- 更新課程評分
- 移除下架課程

### 品質控制
- 驗證 URL 有效性
- 檢查重複課程
- 標準化技能標籤
- 維護分類準確性

## 限制與注意事項

### 系統限制
- 僅包含 Coursera 課程
- 需要定期更新資料
- 搜尋結果上限 50

### 使用建議
- 課程資訊可能變動
- 價格需在 Coursera 確認
- 部分課程有地區限制

## 未來改進

### 短期計畫
- 整合更多平台（Udemy, edX）
- 加入價格資訊
- 學習路徑推薦

### 長期規劃
- 個人化推薦引擎
- 學習成效追蹤
- 技能認證整合

## 相關功能

- [差距分析](gap_analysis.md)
- [關鍵字提取](keyword_extraction.md)
- [履歷客製化](resume_tailoring.md)