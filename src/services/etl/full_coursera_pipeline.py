# flake8: noqa
"""
完整的 Coursera ETL + Embedding Pipeline
包含測試模式 (3個課程) 和完整模式 (所有課程)
ETL script with CLI output - print statements are intentional
"""
import asyncio
import json
import os
import signal
import sys
from datetime import datetime
from typing import Any

import aiohttp
import asyncpg
from pgvector.asyncpg import register_vector

sys.path.append('.')
from src.services.embedding_client import get_azure_embedding_client


class CourseraFullPipeline:
    """完整的 Coursera 資料處理 Pipeline"""
    
    def __init__(self, test_mode: bool = False):
        # Impact.com API 設定
        self.base_url = "https://api.impact.com"
        self.account_sid = "IR5reNPSapi65901857xTcusvceeZxhuj1"
        self.auth_token = os.getenv("IMPACT_API_TOKEN", "fqCf-KbEjMdGzihWtHURf2~mnTCNb9jd")
        self.catalog_id = "9419"
        
        # 模式設定
        self.test_mode = test_mode
        self.max_courses = 3 if test_mode else None  # 測試模式只處理 3 個
        
        # 統計資訊
        self.stats = {
            "start_time": None,
            "end_time": None,
            "courses_fetched": 0,
            "courses_saved": 0,
            "embeddings_created": 0,
            "errors": []
        }
        
        # 中斷處理
        self.should_stop = False
        
        # 進度檔案
        self.progress_file = "temp/etl_progress.json"
        
    def handle_interrupt(self, signum, frame):
        """處理中斷信號"""
        print("\n\n⚠️  收到中斷信號, 正在優雅地停止...")
        self.should_stop = True
        self._save_progress()
        
    def _save_progress(self):
        """儲存進度"""
        # 轉換 datetime 為字串
        stats_copy = self.stats.copy()
        if stats_copy.get("start_time"):
            stats_copy["start_time"] = stats_copy["start_time"].isoformat()
        if stats_copy.get("end_time"):
            stats_copy["end_time"] = stats_copy["end_time"].isoformat()
        
        progress = {
            "timestamp": datetime.now().isoformat(),
            "mode": "test" if self.test_mode else "full",
            "stats": stats_copy,
            "status": "interrupted" if self.should_stop else "running"
        }
        
        with open(self.progress_file, 'w') as f:
            json.dump(progress, f, indent=2)
        
        print(f"💾 進度已儲存到 {self.progress_file}")
    
    async def run(self):
        """執行完整 Pipeline"""
        print("🚀 Coursera ETL + Embedding Pipeline")
        print(f"   模式: {'測試 (3個課程)' if self.test_mode else '完整 (所有課程)'}")
        print(f"   時間: {datetime.now()}")
        print("=" * 60)
        
        self.stats["start_time"] = datetime.now()
        
        # 設定中斷處理
        signal.signal(signal.SIGINT, self.handle_interrupt)
        
        try:
            # 步驟 1: 檢查現有資料
            await self._check_existing_data()
            
            if self.should_stop:
                return
            
            # 步驟 2: 從 API 抓取課程
            courses = await self._fetch_courses()
            
            if self.should_stop or not courses:
                return
            
            # 步驟 3: 儲存課程到資料庫
            await self._save_courses(courses)
            
            if self.should_stop:
                return
            
            # 步驟 4: 產生 embeddings
            await self._generate_embeddings()
            
            # 完成
            self.stats["end_time"] = datetime.now()
            self._print_summary()
            
        except Exception as e:
            print(f"\n❌ Pipeline 錯誤: {e}")
            self.stats["errors"].append(str(e))
            import traceback
            traceback.print_exc()
        
        finally:
            self._save_progress()
    
    async def _check_existing_data(self):
        """檢查現有資料"""
        print("\n📊 檢查現有資料...")
        
        conn = await self._get_db_connection()
        try:
            # 檢查課程數量
            course_count = await conn.fetchval(
                "SELECT COUNT(*) FROM courses WHERE platform_id = 'coursera'"
            )
            
            # 檢查 embeddings
            embedding_count = await conn.fetchval("""
                SELECT COUNT(*) FROM courses c
                JOIN course_embeddings ce ON c.id = ce.course_id
                WHERE c.platform_id = 'coursera'
            """)
            
            print(f"   現有課程: {course_count}")
            print(f"   已有 embeddings: {embedding_count}")
            
            if self.test_mode:
                print("   ⚠️  測試模式: 將只處理前 3 個新課程")
            elif course_count >= 8760:
                print("   ✅ 資料已完整!")
                response = input("\n要重新執行嗎?(y/N): ")
                if response.lower() != 'y':
                    self.should_stop = True
                    
        finally:
            await conn.close()
    
    async def _fetch_courses(self) -> list[dict[str, Any]]:
        """從 Impact.com API 抓取課程"""
        print("\n📥 從 Impact.com API 抓取課程...")
        
        courses = []
        page = 1
        fetched_count = 0
        
        async with aiohttp.ClientSession() as session:
            while not self.should_stop:
                if self.test_mode and fetched_count >= self.max_courses:
                    break
                
                url = f"{self.base_url}/Mediapartners/{self.account_sid}/Catalogs/{self.catalog_id}/Items"
                params = {
                    "PageSize": 100,
                    "Page": page
                }
                
                print(f"   抓取第 {page} 頁...", end="", flush=True)
                
                try:
                    async with session.get(
                        url,
                        params=params,
                        auth=aiohttp.BasicAuth(self.account_sid, self.auth_token),
                        headers={"Accept": "application/json"},
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as response:
                        if response.status != 200:
                            print(f" ❌ 錯誤 {response.status}")
                            break
                        
                        data = await response.json()
                        items = data.get("Items", [])
                        
                        # 測試模式下只取需要的數量
                        if self.test_mode:
                            items = items[:self.max_courses - fetched_count]
                        
                        courses.extend(items)
                        fetched_count += len(items)
                        
                        print(f" ✓ ({len(items)} 個) - 累計: {fetched_count}")
                        
                        # 檢查是否還有更多頁面
                        total_pages = int(data.get("@numpages", 1))
                        if page >= total_pages:
                            break
                        
                        page += 1
                        
                        # 每 10 頁儲存進度
                        if page % 10 == 0:
                            self.stats["courses_fetched"] = fetched_count
                            self._save_progress()
                        
                        # 速率限制和 API 限制檢查
                        await asyncio.sleep(1.0)  # 增加延遲, 更保守
                        
                        # 檢查 rate limit (從 response headers)
                        remaining = response.headers.get('x-ratelimit-remaining-hour')
                        if remaining and int(remaining) < 100:
                            print(f"\n⚠️  API 速率限制接近上限, 剩餘: {remaining}/1000")
                            print("   暫停 60 秒...")
                            await asyncio.sleep(60)
                        
                except Exception as e:
                    print(f" ❌ 錯誤: {e}")
                    self.stats["errors"].append(f"API fetch error: {e}")
                    break
        
        self.stats["courses_fetched"] = len(courses)
        print(f"\n✅ 成功抓取 {len(courses)} 個課程")
        return courses
    
    async def _save_courses(self, courses: list[dict[str, Any]]):
        """儲存課程到資料庫"""
        print(f"\n💾 儲存 {len(courses)} 個課程到資料庫...")
        
        conn = await self._get_db_connection()
        
        try:
            saved_count = 0
            
            for i, raw_course in enumerate(courses):
                if self.should_stop:
                    break
                
                try:
                    # 轉換課程資料
                    course = self._transform_course(raw_course)
                    
                    # 儲存到資料庫
                    await self._save_single_course(conn, course)
                    saved_count += 1
                    
                    # 顯示進度
                    if (i + 1) % 10 == 0 or i == len(courses) - 1:
                        progress = (i + 1) / len(courses) * 100
                        print(f"   進度: {progress:.1f}% ({i + 1}/{len(courses)})")
                        
                except Exception as e:
                    print(f"   ⚠️  儲存錯誤: {raw_course.get('Name', 'Unknown')} - {e}")
                    self.stats["errors"].append(f"Save error: {e}")
            
            self.stats["courses_saved"] = saved_count
            print(f"✅ 成功儲存 {saved_count} 個課程")
            
        finally:
            await conn.close()
    
    def _transform_course(self, raw: dict[str, Any]) -> dict[str, Any]:
        """轉換課程資料格式"""
        return {
            "platform_id": "coursera",
            "external_id": raw.get("CatalogItemId", ""),
            "name": raw.get("Name", ""),
            "description": self._clean_description(raw.get("Description", "")),
            "manufacturer": raw.get("Manufacturer", ""),
            "current_price": self._parse_price(raw.get("CurrentPrice", "0")),
            "original_price": self._parse_price(raw.get("OriginalPrice", "0")),
            "currency": raw.get("Currency", "USD"),
            "image_url": raw.get("ImageUrl", ""),
            "stock_status": self._normalize_stock_status(raw.get("StockAvailability", "")),
            "original_url": raw.get("Url", ""),
            "metadata": {
                "category": raw.get("Category", ""),
                "sub_category": raw.get("SubCategory", ""),
                "mpn": raw.get("Mpn", ""),
                "catalog_id": raw.get("CatalogId", ""),
                "campaign_id": raw.get("CampaignId", ""),
                "id": raw.get("Id", "")
            }
        }
    
    def _clean_description(self, desc: str) -> str:
        """清理描述文字"""
        desc = desc.replace("\\n", "\n").replace("\\r", "")
        desc = desc.replace("\\'", "'").replace('\\"', '"')
        if len(desc) > 5000:
            desc = desc[:4997] + "..."
        return desc.strip()
    
    def _parse_price(self, price_str: str) -> float:
        """解析價格"""
        try:
            price_str = price_str.replace("$", "").replace(",", "").strip()
            return float(price_str) if price_str else 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def _normalize_stock_status(self, status: str) -> str:
        """標準化庫存狀態"""
        status_map = {
            "InStock": "in_stock",
            "OutOfStock": "out_of_stock",
            "Limited": "limited"
        }
        return status_map.get(status, "unknown")
    
    async def _save_single_course(self, conn: asyncpg.Connection, course: dict[str, Any]):
        """儲存單一課程"""
        course_id = f"{course['platform_id']}_{course['external_id']}"
        
        # 使用 UPSERT
        await conn.execute("""
            INSERT INTO courses (
                id, platform_id, external_id, name, description,
                manufacturer, current_price, original_price,
                currency, image_url, stock_status, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                manufacturer = EXCLUDED.manufacturer,
                current_price = EXCLUDED.current_price,
                original_price = EXCLUDED.original_price,
                currency = EXCLUDED.currency,
                image_url = EXCLUDED.image_url,
                stock_status = EXCLUDED.stock_status,
                metadata = EXCLUDED.metadata,
                last_synced = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
        """,
        course_id,
        course['platform_id'],
        course['external_id'],
        course['name'],
        course['description'],
        course['manufacturer'],
        course['current_price'],
        course['original_price'],
        course['currency'],
        course['image_url'],
        course['stock_status'],
        json.dumps(course['metadata'])
        )
        
        # 儲存追蹤 URL
        if course.get('original_url'):
            await conn.execute("""
                INSERT INTO course_tracking_urls 
                (course_id, original_url, tracking_url, tracking_params)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT DO NOTHING
            """,
            course_id,
            course['original_url'],
            course['original_url'],
            json.dumps({})
            )
    
    async def _generate_embeddings(self):
        """產生 embeddings"""
        print("\n🧮 產生課程 Embeddings...")
        
        conn = await self._get_db_connection()
        await register_vector(conn)
        
        try:
            # 取得需要產生 embedding 的課程
            courses = await conn.fetch("""
                SELECT c.id, c.name, c.description, c.manufacturer,
                       c.metadata->>'category' as category
                FROM courses c
                LEFT JOIN course_embeddings ce ON c.id = ce.course_id
                WHERE ce.course_id IS NULL
                AND c.platform_id = 'coursera'
                ORDER BY c.created_at
                LIMIT $1
            """, self.max_courses if self.test_mode else 10000)
            
            if not courses:
                print("   ✅ 所有課程都已有 embeddings")
                return
            
            print(f"   找到 {len(courses)} 個需要產生 embedding 的課程")
            
            # 初始化 embedding client
            embedding_client = get_azure_embedding_client()
            
            try:
                # 批次處理
                batch_size = 5
                for i in range(0, len(courses), batch_size):
                    if self.should_stop:
                        break
                    
                    batch = courses[i:i + batch_size]
                    await self._process_embedding_batch(conn, embedding_client, batch)
                    
                    # 顯示進度
                    progress = min((i + batch_size) / len(courses) * 100, 100)
                    processed = min(i + batch_size, len(courses))
                    print(f"   Embedding 進度: {progress:.1f}% ({processed}/{len(courses)})")
                    
                    # 速率限制
                    await asyncio.sleep(1)
                    
            finally:
                await embedding_client.close()
                
        finally:
            await conn.close()
    
    async def _process_embedding_batch(self, conn: asyncpg.Connection, 
                                     embedding_client, batch: list[Any]):
        """處理一批 embeddings"""
        texts = []
        valid_courses = []
        
        for course in batch:
            # 建立 embedding 文本
            text = f"Course Title: {course['name']} | Provider: {course['manufacturer']}"
            if course['category']:
                text += f" | Category: {course['category']}"
            if course['description']:
                text += f" | Description: {course['description'][:1500]}"
            
            texts.append(text)
            valid_courses.append(course)
        
        try:
            # 產生 embeddings
            embeddings = await embedding_client.create_embeddings(texts)
            
            # 儲存到資料庫
            for course, embedding in zip(valid_courses, embeddings, strict=False):
                await conn.execute("""
                    INSERT INTO course_embeddings 
                    (course_id, embedding, embedding_model)
                    VALUES ($1, $2::vector, $3)
                    ON CONFLICT (course_id) DO UPDATE
                    SET embedding = EXCLUDED.embedding,
                        created_at = CURRENT_TIMESTAMP
                """,
                course['id'],
                embedding,
                'text-embedding-3-large'
                )
                
            self.stats["embeddings_created"] += len(valid_courses)
            
        except Exception as e:
            print(f"   ⚠️  Embedding 批次錯誤: {e}")
            self.stats["errors"].append(f"Embedding error: {e}")
    
    async def _get_db_connection(self) -> asyncpg.Connection:
        """取得資料庫連線"""
        with open('temp/postgres_connection.json') as f:
            conn_info = json.load(f)
        
        return await asyncpg.connect(
            host=conn_info['host'],
            database=conn_info['database'],
            user=conn_info['user'],
            password=conn_info['password'],
            ssl='require'
        )
    
    def _print_summary(self):
        """列印執行摘要"""
        duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
        
        print("\n" + "=" * 60)
        print("📊 執行摘要")
        print("=" * 60)
        print(f"模式: {'測試' if self.test_mode else '完整'}")
        print(f"執行時間: {duration:.2f} 秒")
        print(f"抓取課程: {self.stats['courses_fetched']}")
        print(f"儲存課程: {self.stats['courses_saved']}")
        print(f"產生 Embeddings: {self.stats['embeddings_created']}")
        print(f"錯誤數量: {len(self.stats['errors'])}")
        
        if self.stats['errors']:
            print("\n錯誤詳情:")
            for i, error in enumerate(self.stats['errors'][:5], 1):
                print(f"  {i}. {error}")
            if len(self.stats['errors']) > 5:
                print(f"  ... 還有 {len(self.stats['errors']) - 5} 個錯誤")


async def main():
    """主程式"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Coursera ETL + Embedding Pipeline')
    parser.add_argument('--test', action='store_true', help='測試模式 (只處理3個課程)')
    parser.add_argument('--full', action='store_true', help='完整模式 (處理所有課程)')
    
    args = parser.parse_args()
    
    if not args.test and not args.full:
        print("請指定模式:")
        print("  --test  測試模式 (3個課程)")
        print("  --full  完整模式 (所有課程)")
        return
    
    # 執行 pipeline
    pipeline = CourseraFullPipeline(test_mode=args.test)
    await pipeline.run()


if __name__ == "__main__":
    asyncio.run(main())