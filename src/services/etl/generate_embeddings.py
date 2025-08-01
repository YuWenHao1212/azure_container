# flake8: noqa
"""
產生課程 embeddings 並儲存到資料庫
ETL script with CLI output - print statements are intentional
"""
import asyncio
import json
from datetime import datetime
from typing import Any

import asyncpg
import numpy as np

from src.core.monitoring_service import monitoring_service
from src.services.embedding_client import get_azure_embedding_client


class CourseEmbeddingGenerator:
    """課程 Embedding 產生器"""
    
    def __init__(self, batch_size: int = 16):
        self.batch_size = batch_size
        self.embedding_client = None
        self.stats = {
            "total_courses": 0,
            "processed": 0,
            "skipped": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None
        }
    
    async def run(self):
        """執行 embedding 產生流程"""
        print(f"🚀 開始產生課程 Embeddings - {datetime.now()}")
        print("=" * 60)
        
        self.stats["start_time"] = datetime.now()
        
        try:
            # 取得需要產生 embedding 的課程
            courses = await self._get_courses_without_embeddings()
            self.stats["total_courses"] = len(courses)
            
            if not courses:
                print("✅ 所有課程都已有 embeddings!")
                return
            
            print(f"📚 找到 {len(courses)} 個需要產生 embedding 的課程")
            
            # 初始化 embedding client
            self.embedding_client = get_azure_embedding_client()
            
            # 批次處理
            for i in range(0, len(courses), self.batch_size):
                batch = courses[i:i + self.batch_size]
                await self._process_batch(batch)
                
                # 顯示進度
                progress = (i + len(batch)) / len(courses) * 100
                processed = i + len(batch)
                print(f"\n進度: {progress:.1f}% ({processed}/{len(courses)})")
                print(f"已處理: {self.stats['processed']} | 跳過: {self.stats['skipped']} | 錯誤: {self.stats['errors']}")
                
                # 速率限制
                await asyncio.sleep(1)
            
        finally:
            if self.embedding_client:
                await self.embedding_client.close()
            
            self.stats["end_time"] = datetime.now()
            duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
            
            print("\n" + "=" * 60)
            print("✅ Embedding 產生完成!")
            print(f"   總時間: {duration:.2f} 秒")
            print(f"   總課程數: {self.stats['total_courses']}")
            print(f"   已處理: {self.stats['processed']}")
            print(f"   跳過: {self.stats['skipped']}")
            print(f"   錯誤: {self.stats['errors']}")
    
    async def _get_courses_without_embeddings(self) -> list[dict[str, Any]]:
        """取得沒有 embeddings 的課程"""
        # 讀取連線資訊
        with open('temp/postgres_connection.json') as f:
            conn_info = json.load(f)
        
        conn = await asyncpg.connect(
            host=conn_info['host'],
            database=conn_info['database'],
            user=conn_info['user'],
            password=conn_info['password'],
            ssl='require'
        )
        
        try:
            # 查詢沒有 embedding 的課程
            rows = await conn.fetch("""
                SELECT c.id, c.name, c.description, c.manufacturer, 
                       c.metadata->>'category' as category
                FROM courses c
                LEFT JOIN course_embeddings ce ON c.id = ce.course_id
                WHERE ce.course_id IS NULL
                AND c.platform_id = 'coursera'
                ORDER BY c.created_at
                LIMIT 1000
            """)
            
            courses = []
            for row in rows:
                courses.append({
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "manufacturer": row["manufacturer"],
                    "category": row["category"] or ""
                })
            
            return courses
            
        finally:
            await conn.close()
    
    async def _process_batch(self, batch: list[dict[str, Any]]):
        """處理一批課程"""
        print(f"\n🔄 處理批次 ({len(batch)} 個課程)...")
        
        # 準備文本
        texts = []
        valid_courses = []
        
        for course in batch:
            # 建立用於 embedding 的文本
            text = self._create_embedding_text(course)
            
            if len(text) > 10:  # 確保有足夠的內容
                texts.append(text)
                valid_courses.append(course)
            else:
                print(f"   ⚠️  跳過: {course['name'][:50]} (內容不足)")
                self.stats["skipped"] += 1
        
        if not texts:
            return
        
        try:
            # 產生 embeddings
            print(f"   🧮 產生 {len(texts)} 個 embeddings...")
            start_time = datetime.now()
            
            embeddings = await self.embedding_client.create_embeddings(texts)
            
            duration = (datetime.now() - start_time).total_seconds()
            print(f"   ✅ 完成!耗時: {duration:.2f} 秒")
            
            # 儲存到資料庫
            await self._save_embeddings(valid_courses, embeddings)
            
            self.stats["processed"] += len(valid_courses)
            
            # 追蹤指標
            monitoring_service.track_event(
                "CourseEmbeddingGeneration",
                {
                    "batch_size": len(valid_courses),
                    "duration_seconds": duration,
                    "tokens_estimated": sum(len(text) // 4 for text in texts)
                }
            )
            
        except Exception as e:
            print(f"   ❌ 批次處理錯誤: {e}")
            self.stats["errors"] += len(batch)
            
            # 記錄錯誤的課程
            for course in batch:
                print(f"      - {course['name'][:50]}")
    
    def _create_embedding_text(self, course: dict[str, Any]) -> str:
        """建立用於 embedding 的文本"""
        # 組合相關欄位, 給予不同權重
        parts = []
        
        # 課程名稱 (最重要)
        if course.get('name'):
            parts.append(f"Course Title: {course['name']}")
        
        # 提供者
        if course.get('manufacturer'):
            parts.append(f"Provider: {course['manufacturer']}")
        
        # 類別
        if course.get('category'):
            parts.append(f"Category: {course['category']}")
        
        # 描述 (限制長度避免 token 過多)
        if course.get('description'):
            desc = course['description']
            # 清理描述
            desc = desc.replace('\n', ' ').strip()
            if len(desc) > 2000:
                desc = desc[:1997] + "..."
            if desc:
                parts.append(f"Description: {desc}")
        
        return " | ".join(parts)
    
    async def _save_embeddings(self, courses: list[dict[str, Any]], embeddings: list[list[float]]):
        """儲存 embeddings 到資料庫"""
        # 讀取連線資訊
        with open('temp/postgres_connection.json') as f:
            conn_info = json.load(f)
        
        # 需要先註冊 pgvector 類型
        from pgvector.asyncpg import register_vector
        
        conn = await asyncpg.connect(
            host=conn_info['host'],
            database=conn_info['database'],
            user=conn_info['user'],
            password=conn_info['password'],
            ssl='require'
        )
        
        try:
            # 註冊 vector 類型
            await register_vector(conn)
            
            # 批次插入
            async with conn.transaction():
                for course, embedding in zip(courses, embeddings, strict=False):
                    # 確保 embedding 是正確的格式
                    embedding_array = np.array(embedding, dtype=np.float32)
                    
                    await conn.execute("""
                        INSERT INTO course_embeddings 
                        (course_id, embedding, embedding_model)
                        VALUES ($1, $2::vector, $3)
                        ON CONFLICT (course_id) DO UPDATE
                        SET embedding = EXCLUDED.embedding,
                            created_at = CURRENT_TIMESTAMP
                    """,
                    course['id'],
                    embedding_array.tolist(),
                    'text-embedding-3-large'
                    )
                    
            print(f"   💾 已儲存 {len(courses)} 個 embeddings")
            
        finally:
            await conn.close()


async def check_embedding_status():
    """檢查 embedding 狀態"""
    with open('temp/postgres_connection.json') as f:
        conn_info = json.load(f)
    
    conn = await asyncpg.connect(
        host=conn_info['host'],
        database=conn_info['database'],
        user=conn_info['user'],
        password=conn_info['password'],
        ssl='require'
    )
    
    try:
        # 統計資訊
        total_courses = await conn.fetchval(
            "SELECT COUNT(*) FROM courses WHERE platform_id = 'coursera'"
        )
        
        courses_with_embeddings = await conn.fetchval("""
            SELECT COUNT(*) 
            FROM courses c
            JOIN course_embeddings ce ON c.id = ce.course_id
            WHERE c.platform_id = 'coursera'
        """)
        
        print("\n📊 Embedding 狀態:")
        print(f"   總課程數: {total_courses}")
        print(f"   已有 embedding: {courses_with_embeddings}")
        print(f"   待處理: {total_courses - courses_with_embeddings}")
        
        # 顯示範例
        if courses_with_embeddings > 0:
            sample = await conn.fetchrow("""
                SELECT c.name, c.manufacturer,
                       LENGTH(ce.embedding::text) as embedding_size
                FROM courses c
                JOIN course_embeddings ce ON c.id = ce.course_id
                WHERE c.platform_id = 'coursera'
                LIMIT 1
            """)
            
            print("\n📖 範例:")
            print(f"   課程: {sample['name']}")
            print(f"   提供者: {sample['manufacturer']}")
            print("   Embedding 大小: ~1536 維度")
        
    finally:
        await conn.close()


async def main():
    """主程式"""
    # 檢查目前狀態
    await check_embedding_status()
    
    # 詢問是否繼續
    response = input("\n要開始產生 embeddings 嗎?(y/N): ")
    if response.lower() != 'y':
        print("已取消。")
        return
    
    # 執行產生器
    generator = CourseEmbeddingGenerator(batch_size=10)  # 小批次避免超時
    await generator.run()
    
    # 顯示最終狀態
    await check_embedding_status()


if __name__ == "__main__":
    asyncio.run(main())