#!/usr/bin/env python3
"""
診斷腳本：檢查特定課程 ID 在資料庫中的狀況
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

async def check_courses():
    """檢查課程存在性和狀態"""
    
    # 要檢查的課程 ID
    course_ids = [
        'coursera_spzn:deep-learning',
        'coursera_crse:v1-2702',
        'coursera_crse:v1-2703',
        'coursera_crse:v1-2704',
        'coursera_crse:v1-2705',
        'coursera_crse:v1-2706',
        'coursera_crse:v1-2707',
        'coursera_crse:v1-2708',
        'coursera_crse:v1-2709',
        'coursera_crse:v1-2710'
    ]
    
    # 資料庫連線資訊
    conn_info = {
        'host': os.getenv('POSTGRES_HOST', 'airesumeadvisor-courses-db-eastasia.postgres.database.azure.com'),
        'port': int(os.getenv('POSTGRES_PORT', '5432')),
        'database': os.getenv('POSTGRES_DATABASE', 'coursesdb'),
        'user': os.getenv('POSTGRES_USER', 'coursesadmin'),
        'password': os.getenv('POSTGRES_PASSWORD')
    }
    
    if not conn_info['password']:
        print("錯誤：未設定 POSTGRES_PASSWORD 環境變數")
        return
    
    try:
        # 建立連線
        conn = await asyncpg.connect(
            host=conn_info['host'],
            port=conn_info['port'],
            database=conn_info['database'],
            user=conn_info['user'],
            password=conn_info['password'],
            ssl='require'
        )
        
        print("=" * 80)
        print("課程檢查報告")
        print("=" * 80)
        
        # 1. 檢查每個課程的存在性和詳細資訊
        for course_id in course_ids:
            print(f"\n檢查課程: {course_id}")
            print("-" * 40)
            
            # 查詢課程（不加 platform 條件）
            result = await conn.fetchrow("""
                SELECT 
                    id,
                    name,
                    platform,
                    provider,
                    provider_standardized,
                    course_type_standard,
                    price,
                    currency,
                    embedding IS NOT NULL as has_embedding,
                    created_at,
                    updated_at
                FROM courses
                WHERE id = $1
            """, course_id)
            
            if result:
                print(f"  ✅ 找到課程")
                print(f"  名稱: {result['name'][:50]}...")
                print(f"  平台: {result['platform']}")
                print(f"  提供者: {result['provider']}")
                print(f"  標準化提供者: {result['provider_standardized']}")
                print(f"  課程類型: {result['course_type_standard']}")
                print(f"  價格: {result['currency']} {result['price']}")
                print(f"  有 embedding: {'是' if result['has_embedding'] else '否'}")
                print(f"  建立時間: {result['created_at']}")
                print(f"  更新時間: {result['updated_at']}")
                
                # 檢查為什麼可能查不到
                if result['platform'] != 'coursera':
                    print(f"  ⚠️  警告: platform 欄位是 '{result['platform']}' 而不是 'coursera'")
            else:
                print(f"  ❌ 資料庫中找不到此課程")
        
        # 2. 統計不同 platform 的課程數量
        print("\n" + "=" * 80)
        print("Platform 統計")
        print("=" * 80)
        
        platform_stats = await conn.fetch("""
            SELECT 
                platform,
                COUNT(*) as count
            FROM courses
            GROUP BY platform
            ORDER BY count DESC
        """)
        
        for row in platform_stats:
            print(f"  {row['platform']}: {row['count']} 課程")
        
        # 3. 檢查類似 ID 模式的課程
        print("\n" + "=" * 80)
        print("類似 ID 模式的課程（前 20 筆）")
        print("=" * 80)
        
        similar_courses = await conn.fetch("""
            SELECT 
                id,
                name,
                platform,
                provider
            FROM courses
            WHERE id LIKE 'coursera_spzn:%'
               OR id LIKE 'coursera_crse:%'
            LIMIT 20
        """)
        
        if similar_courses:
            for row in similar_courses:
                print(f"  {row['id']}: {row['name'][:40]}... (platform: {row['platform']})")
        else:
            print("  沒有找到類似 ID 模式的課程")
        
        # 4. 檢查可能的 ID 變化
        print("\n" + "=" * 80)
        print("檢查可能的課程名稱匹配")
        print("=" * 80)
        
        # 搜尋 deep learning 相關課程
        deep_learning_courses = await conn.fetch("""
            SELECT 
                id,
                name,
                platform,
                provider
            FROM courses
            WHERE LOWER(name) LIKE '%deep learning%'
            AND platform = 'coursera'
            LIMIT 10
        """)
        
        if deep_learning_courses:
            print("\nDeep Learning 相關課程:")
            for row in deep_learning_courses:
                print(f"  {row['id']}: {row['name'][:50]}...")
        
        await conn.close()
        print("\n" + "=" * 80)
        print("檢查完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"錯誤: {e}")

if __name__ == "__main__":
    asyncio.run(check_courses())