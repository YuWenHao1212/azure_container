#!/usr/bin/env python3
"""
查詢課程資料庫 schema
"""
import asyncio
import os
import asyncpg
from dotenv import load_dotenv
import json

async def check_course_schema():
    # 載入環境變數
    load_dotenv()
    
    # 取得資料庫連線字串
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ 找不到 DATABASE_URL 環境變數")
        return
    
    print("🔗 連接到課程資料庫...")
    print(f"   URL: {database_url[:30]}...")
    
    try:
        # 建立連線
        conn = await asyncpg.connect(database_url)
        
        print("\n📊 查詢 courses 表格 schema...")
        
        # 1. 查詢所有欄位資訊
        schema_query = """
        SELECT 
            column_name,
            data_type,
            character_maximum_length,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_name = 'courses'
        ORDER BY ordinal_position;
        """
        
        columns = await conn.fetch(schema_query)
        
        print("\n🗂️ Courses 表格結構：")
        print("-" * 80)
        for col in columns:
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            max_len = f"({col['character_maximum_length']})" if col['character_maximum_length'] else ""
            default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
            print(f"  {col['column_name']:30} {col['data_type']:15}{max_len:10} {nullable:10}{default}")
        
        # 2. 查詢索引
        print("\n🔍 索引：")
        index_query = """
        SELECT 
            indexname,
            indexdef
        FROM pg_indexes
        WHERE tablename = 'courses';
        """
        
        indexes = await conn.fetch(index_query)
        for idx in indexes:
            print(f"  - {idx['indexname']}")
            print(f"    {idx['indexdef'][:100]}...")
        
        # 3. 查詢資料統計
        print("\n📈 資料統計：")
        stats_query = """
        SELECT 
            COUNT(*) as total_courses,
            COUNT(DISTINCT platform) as platforms,
            COUNT(DISTINCT provider) as providers,
            COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as with_embeddings
        FROM courses;
        """
        
        stats = await conn.fetchrow(stats_query)
        print(f"  總課程數: {stats['total_courses']:,}")
        print(f"  平台數: {stats['platforms']}")
        print(f"  提供者數: {stats['providers']}")
        print(f"  有 embedding 的課程: {stats['with_embeddings']:,}")
        
        # 4. 查詢課程類型分布
        print("\n📚 課程類型分布：")
        type_query = """
        SELECT 
            course_type_standard,
            COUNT(*) as count
        FROM courses
        WHERE course_type_standard IS NOT NULL
        GROUP BY course_type_standard
        ORDER BY count DESC;
        """
        
        types = await conn.fetch(type_query)
        for t in types:
            print(f"  {t['course_type_standard']:20} {t['count']:,}")
        
        # 5. 查詢前 5 筆資料範例
        print("\n📝 資料範例（前 5 筆）：")
        sample_query = """
        SELECT 
            id,
            name,
            provider,
            course_type_standard,
            price,
            currency
        FROM courses
        LIMIT 5;
        """
        
        samples = await conn.fetch(sample_query)
        for s in samples:
            print(f"\n  ID: {s['id']}")
            print(f"  名稱: {s['name'][:50]}...")
            print(f"  提供者: {s['provider']}")
            print(f"  類型: {s['course_type_standard']}")
            print(f"  價格: {s['currency']} {s['price']}")
        
        # 6. 檢查 course_embeddings 表格
        print("\n\n📊 查詢 course_embeddings 表格 schema...")
        embedding_schema_query = """
        SELECT 
            column_name,
            data_type,
            is_nullable
        FROM information_schema.columns
        WHERE table_name = 'course_embeddings'
        ORDER BY ordinal_position;
        """
        
        embedding_columns = await conn.fetch(embedding_schema_query)
        if embedding_columns:
            print("\n🗂️ Course_embeddings 表格結構：")
            print("-" * 80)
            for col in embedding_columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                print(f"  {col['column_name']:30} {col['data_type']:15} {nullable:10}")
        
        await conn.close()
        print("\n✅ 查詢完成")
        
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_course_schema())