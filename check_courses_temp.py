#!/usr/bin/env python3
"""
臨時腳本：查詢資料庫中真實存在的課程 IDs
"""
import asyncio
import os
from dotenv import load_dotenv

async def check_courses():
    # 載入環境變數
    load_dotenv()
    
    # 使用 CourseSearchService 來查詢
    from src.services.course_search import CourseSearchService
    
    try:
        # 初始化服務
        service = CourseSearchService()
        await service.initialize()
        
        print("✅ 成功連接到資料庫")
        
        # 查詢一些課程範例
        async with service._connection_pool.acquire() as conn:
            # 1. 查詢總數
            count_query = "SELECT COUNT(*) FROM courses"
            count = await conn.fetchval(count_query)
            print(f"\n📊 資料庫中總共有 {count:,} 個課程")
            
            # 2. 查詢前 10 個課程的 ID
            sample_query = """
                SELECT id, name, provider, course_type_standard
                FROM courses
                WHERE id LIKE 'coursera_%'
                ORDER BY id
                LIMIT 10
            """
            
            rows = await conn.fetch(sample_query)
            print("\n📚 前 10 個 Coursera 課程 IDs：")
            print("-" * 80)
            for row in rows:
                print(f"ID: {row['id']}")
                print(f"   名稱: {row['name'][:60]}...")
                print(f"   提供者: {row['provider']}")
                print(f"   類型: {row['course_type_standard']}")
                print()
            
            # 3. 查詢特定類型的課程
            type_query = """
                SELECT id, name
                FROM courses
                WHERE course_type_standard = 'specialization'
                LIMIT 5
            """
            
            spec_rows = await conn.fetch(type_query)
            print("\n🎓 Specialization 類型課程範例：")
            print("-" * 80)
            for row in spec_rows:
                print(f"ID: {row['id']}")
                print(f"   名稱: {row['name'][:60]}...")
            
            # 4. 查詢包含 React 的課程
            react_query = """
                SELECT id, name
                FROM courses
                WHERE name ILIKE '%react%'
                LIMIT 5
            """
            
            react_rows = await conn.fetch(react_query)
            print("\n⚛️ React 相關課程範例：")
            print("-" * 80)
            for row in react_rows:
                print(f"ID: {row['id']}")
                print(f"   名稱: {row['name'][:60]}...")
            
            # 5. 檢查那些找不到的 IDs
            problematic_ids = [
                "coursera_spzn.wtAqsotBEeybigqXI4404Q",
                "coursera_spzn:JcMOEQqFEeuwvRJ&DmwdUQ",
                "coursera_spzn:4VFz07iKEemoiA7BQCKbMA"
            ]
            
            print("\n🔍 檢查問題 IDs：")
            print("-" * 80)
            for pid in problematic_ids:
                check_query = "SELECT COUNT(*) FROM courses WHERE id = $1"
                exists = await conn.fetchval(check_query, pid)
                print(f"{pid}: {'✅ 存在' if exists else '❌ 不存在'}")
            
            # 6. 查詢正確格式的 specialization IDs
            correct_format_query = """
                SELECT id, name
                FROM courses
                WHERE id LIKE 'coursera_spzn:%'
                LIMIT 5
            """
            
            correct_rows = await conn.fetch(correct_format_query)
            print("\n✅ 正確格式的 Specialization IDs：")
            print("-" * 80)
            for row in correct_rows:
                print(f"ID: {row['id']}")
                print(f"   名稱: {row['name'][:60]}...")
        
        await service.close()
        print("\n✅ 查詢完成")
        
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_courses())