# Course Database Schema Documentation

> 📅 Last Updated: 2025-08-17  
> 🗄️ Database: PostgreSQL with pgvector extension  
> 🌐 Production Environment: Azure Container Apps

## 📊 Database Tables Overview

本專案使用 PostgreSQL 資料庫，包含兩個主要表格：
1. **courses** - 儲存所有課程資料
2. **course_embeddings** - 儲存課程向量 (用於相似度搜尋)

---

## 1. 📚 Courses Table

主要課程資料表，儲存從 Coursera 等平台抓取的課程資訊。

### Schema Structure

| Column Name | Data Type | Constraints | Description |
|-------------|-----------|-------------|-------------|
| **id** | `TEXT` | PRIMARY KEY | 課程唯一識別碼，格式: `{platform}_{external_id}` |
| **name** | `TEXT` | NOT NULL | 課程名稱 |
| **description** | `TEXT` | | 課程詳細描述 |
| **provider** | `TEXT` | | 原始提供者名稱 (如: "Stanford University") |
| **provider_standardized** | `TEXT` | | 標準化提供者名稱 |
| **provider_logo_url** | `TEXT` | | 提供者 Logo 圖片 URL |
| **price** | `NUMERIC(10,2)` | DEFAULT 0 | 課程價格 |
| **currency** | `TEXT` | DEFAULT 'USD' | 貨幣代碼 (USD, EUR, etc.) |
| **image_url** | `TEXT` | | 課程封面圖片 URL |
| **affiliate_url** | `TEXT` | | 聯盟行銷追蹤連結 |
| **course_type** | `TEXT` | | 原始課程類型 |
| **course_type_standard** | `TEXT` | | 標準化課程類型 (見下方對照表) |
| **platform** | `TEXT` | NOT NULL | 平台名稱 (目前為 'coursera') |
| **platform_id** | `TEXT` | | 平台識別碼 |
| **external_id** | `TEXT` | | 外部系統的課程 ID |
| **category** | `TEXT` | | 課程分類 |
| **duration** | `TEXT` | | 課程時長 (如: "4 weeks") |
| **difficulty** | `TEXT` | | 難度等級 (Beginner/Intermediate/Advanced) |
| **embedding** | `VECTOR(1536)` | | 課程向量，用於相似度搜尋 |
| **created_at** | `TIMESTAMP` | DEFAULT NOW() | 資料建立時間 |
| **updated_at** | `TIMESTAMP` | DEFAULT NOW() | 資料更新時間 |

### Course Type Mapping (course_type_standard)

標準化的課程類型對應：

| Standard Type | Original Types | Description | Bubble.io Display |
|--------------|----------------|-------------|-------------------|
| `course` | "COURSE", "Course" | 一般課程 | Course |
| `certification` | "PROFESSIONAL_CERTIFICATE", "Professional Certificate" | 專業證書 | Professional Certificate |
| `specialization` | "SPECIALIZATION", "Specialization" | 專項課程系列 | Specialization |
| `degree` | "DEGREE", "Degree" | 學位課程 | Degree |
| `project` | "GUIDED_PROJECT", "Guided Project" | 引導式專案 | Guided Project |

### Indexes

```sql
-- Primary key index
CREATE UNIQUE INDEX courses_pkey ON courses(id);

-- Platform index for filtering
CREATE INDEX idx_courses_platform ON courses(platform);

-- Course type index for filtering
CREATE INDEX idx_courses_type ON courses(course_type_standard);

-- Vector similarity search index (using ivfflat)
CREATE INDEX idx_courses_embedding ON courses 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Composite index for common queries
CREATE INDEX idx_courses_platform_type ON courses(platform, course_type_standard);
```

---

## 2. 🔮 Course_Embeddings Table

儲存課程的向量表示，用於進階的語意搜尋功能。

### Schema Structure

| Column Name | Data Type | Constraints | Description |
|-------------|-----------|-------------|-------------|
| **course_id** | `TEXT` | PRIMARY KEY, FK | 關聯到 courses.id |
| **embedding** | `VECTOR(1536)` | NOT NULL | 課程內容的向量表示 |
| **embedding_model** | `TEXT` | | 使用的 embedding 模型名稱 |
| **created_at** | `TIMESTAMP` | DEFAULT NOW() | 向量建立時間 |
| **updated_at** | `TIMESTAMP` | DEFAULT NOW() | 向量更新時間 |

### Foreign Key Constraint

```sql
ALTER TABLE course_embeddings 
ADD CONSTRAINT fk_course_embeddings_course 
FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE;
```

---

## 3. 🔍 Common Queries

### Search Courses by Vector Similarity

```sql
-- 使用 pgvector 進行相似度搜尋
SELECT 
    c.id,
    c.name,
    c.description,
    c.provider_standardized,
    c.course_type_standard,
    1 - (c.embedding <=> $1::vector) as similarity_score
FROM courses c
WHERE c.platform = 'coursera'
    AND c.embedding IS NOT NULL
    AND 1 - (c.embedding <=> $1::vector) >= $2  -- similarity threshold
ORDER BY c.embedding <=> $1::vector
LIMIT $3;
```

### Get Course by IDs (for Bubble.io integration)

```sql
-- 根據 available_course_ids 列表查詢課程詳情
SELECT 
    id,
    name,
    description,
    provider_standardized as provider,
    provider_logo_url,
    price,
    currency,
    image_url,
    affiliate_url,
    course_type_standard as course_type
FROM courses
WHERE id = ANY($1::text[]);  -- $1 is array of course IDs
```

### Course Statistics

```sql
-- 統計各類型課程數量
SELECT 
    course_type_standard,
    COUNT(*) as count,
    AVG(price) as avg_price
FROM courses
WHERE platform = 'coursera'
GROUP BY course_type_standard
ORDER BY count DESC;
```

---

## 4. 🔗 Integration with Bubble.io

### API Response Mapping

當 API 回傳 `SkillSearchQueries` 時，每個技能的 `available_course_ids` 對應到資料庫的課程 ID：

```json
{
  "SkillSearchQueries": [
    {
      "skill_name": "React",
      "available_course_ids": [
        "coursera_crse:v1-2598",  // 對應 courses.id
        "coursera_crse:v1-2599",
        "coursera_spzn:react-basics"
      ]
    }
  ]
}
```

### Bubble.io Data Type Suggestion

建議在 Bubble.io 建立以下 Data Types：

#### Course Data Type
- `course_id` (text) - Primary identifier
- `name` (text)
- `description` (text)
- `provider` (text)
- `provider_logo_url` (text)
- `price` (number)
- `currency` (text)
- `image_url` (text)
- `affiliate_url` (text)
- `course_type` (text)
- `similarity_score` (number) - 0-100 percentage

#### SkillQuery Data Type
- `skill_name` (text)
- `skill_category` (text) - "SKILL" or "FIELD"
- `description` (text)
- `has_available_courses` (yes/no)
- `course_count` (number)
- `available_course_ids` (list of texts)
- `courses` (list of Course) - Populated when needed

---

## 5. 📈 Performance Considerations

### Connection Pooling

應用程式使用連線池管理資料庫連線：

```python
# 連線池配置
min_size = 10  # 最小連線數
max_size = 20  # 最大連線數
max_queries = 50000  # 每個連線的最大查詢數
max_inactive_connection_lifetime = 300.0  # 5 分鐘
```

### Vector Search Optimization

- **Index Type**: IVFFlat with 100 lists
- **Vector Dimension**: 1536 (OpenAI text-embedding-3-large)
- **Distance Metric**: Cosine similarity (`<=>` operator)
- **Warm-up**: 系統啟動時會預熱 pgvector 索引

### Caching Strategy

- **Search Results**: 快取 15 分鐘
- **Course Details**: 快取 1 小時
- **Cache Key Format**: `{skill_name}_{search_context}_{threshold}`

---

## 6. 🚀 Database Migrations

### Initial Setup

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create courses table
CREATE TABLE courses (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    -- ... (see full schema above)
    embedding VECTOR(1536)
);

-- Create course_embeddings table
CREATE TABLE course_embeddings (
    course_id TEXT PRIMARY KEY REFERENCES courses(id),
    embedding VECTOR(1536) NOT NULL,
    embedding_model TEXT
);
```

### Recent Migrations

- **2025-08-10**: Added `course_type_standard` column for normalized course types
- **2025-08-11**: Added pgvector indexes for similarity search
- **2025-08-15**: Optimized connection pooling configuration

---

## 7. 🔒 Security Considerations

1. **Connection Security**: 使用 SSL 連線到 Azure PostgreSQL
2. **Query Parameterization**: 所有查詢使用參數化防止 SQL injection
3. **Access Control**: 應用程式使用受限的資料庫使用者
4. **Sensitive Data**: 不儲存使用者個人資料在課程表格中

---

## 8. 📞 Contact & Support

- **Database Admin**: Azure PostgreSQL Flexible Server
- **Region**: Japan East
- **Backup**: Daily automated backups with 7-day retention
- **Monitoring**: Azure Monitor + Application Insights

---

**Document Version**: 1.0.0  
**Last Review**: 2025-08-17  
**Next Review**: 2025-09-17