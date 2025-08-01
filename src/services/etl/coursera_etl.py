# flake8: noqa
"""
Coursera ETL - 從 Impact.com API 匯入課程資料
ETL script with CLI output - print statements are intentional
"""
import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Any
from urllib.parse import parse_qs, urlparse

import aiohttp
import asyncpg


class CourseraETL:
    """Coursera 課程資料 ETL"""
    
    def __init__(self):
        # Impact.com API 設定
        self.base_url = "https://api.impact.com"
        self.account_sid = "IR5reNPSapi65901857xTcusvceeZxhuj1"
        self.auth_token = os.getenv("IMPACT_API_TOKEN", "fqCf-KbEjMdGzihWtHURf2~mnTCNb9jd")
        self.catalog_id = "9419"
        
        # 統計資訊
        self.stats = {
            "total_fetched": 0,
            "new_courses": 0,
            "updated_courses": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None
        }
        
    async def run(self):
        """執行 ETL 流程"""
        print(f"🚀 開始 Coursera ETL - {datetime.now()}")
        print("=" * 60)
        
        self.stats["start_time"] = datetime.now()
        sync_log_id = str(uuid.uuid4())
        
        try:
            # 1. 建立同步記錄
            await self._create_sync_log(sync_log_id)
            
            # 2. 從 API 抓取資料
            courses = await self._fetch_all_courses()
            
            # 3. 轉換資料格式
            transformed_courses = self._transform_courses(courses)
            
            # 4. 儲存到資料庫
            await self._save_to_database(transformed_courses)
            
            # 5. 更新同步記錄
            await self._update_sync_log(sync_log_id, "completed")
            
            self.stats["end_time"] = datetime.now()
            duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
            
            print("\n✅ ETL 完成!")
            print(f"   總時間: {duration:.2f} 秒")
            print(f"   抓取課程: {self.stats['total_fetched']}")
            print(f"   新增課程: {self.stats['new_courses']}")
            print(f"   更新課程: {self.stats['updated_courses']}")
            print(f"   錯誤數量: {self.stats['errors']}")
            
        except Exception as e:
            print(f"\n❌ ETL 失敗: {e}")
            await self._update_sync_log(sync_log_id, "failed", str(e))
            raise
    
    async def _fetch_all_courses(self) -> list[dict[str, Any]]:
        """從 Impact.com API 抓取所有課程"""
        print("\n📥 從 Impact.com API 抓取課程...")
        
        courses = []
        page = 1
        total_pages = None
        
        async with aiohttp.ClientSession() as session:
            while True:
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
                        
                        # 第一次取得總頁數
                        if total_pages is None:
                            total_pages = int(data.get("@numpages", 1))
                            total_items = int(data.get("@total", 0))
                            print(f"\n   總共 {total_items} 個課程, {total_pages} 頁")
                        
                        items = data.get("Items", [])
                        courses.extend(items)
                        print(f" ✓ ({len(items)} 個)")
                        
                        # 檢查是否還有更多頁面
                        if page >= total_pages:
                            break
                        
                        page += 1
                        
                        # 速率限制
                        await asyncio.sleep(0.5)
                        
                except Exception as e:
                    print(f" ❌ 錯誤: {e}")
                    self.stats["errors"] += 1
                    break
        
        self.stats["total_fetched"] = len(courses)
        print(f"\n✅ 成功抓取 {len(courses)} 個課程")
        return courses
    
    def _transform_courses(self, raw_courses: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """轉換課程資料格式"""
        print("\n🔄 轉換課程資料...")
        
        transformed = []
        
        for raw in raw_courses:
            try:
                # 擷取關鍵欄位
                course = {
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
                
                # 處理追蹤 URL
                if course["original_url"]:
                    course["tracking_params"] = self._extract_tracking_params(course["original_url"])
                
                transformed.append(course)
                
            except Exception as e:
                print(f"   ⚠️  轉換錯誤: {raw.get('Name', 'Unknown')} - {e}")
                self.stats["errors"] += 1
        
        print(f"✅ 成功轉換 {len(transformed)} 個課程")
        return transformed
    
    def _clean_description(self, desc: str) -> str:
        """清理描述文字"""
        # 移除多餘的反斜線和換行
        desc = desc.replace("\\n", "\n")
        desc = desc.replace("\\r", "")
        desc = desc.replace("\\'", "'")
        desc = desc.replace('\\"', '"')
        
        # 限制長度
        if len(desc) > 5000:
            desc = desc[:4997] + "..."
        
        return desc.strip()
    
    def _parse_price(self, price_str: str) -> float:
        """解析價格字串"""
        try:
            # 移除貨幣符號和空格
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
    
    def _extract_tracking_params(self, url: str) -> dict[str, str]:
        """從 URL 擷取追蹤參數"""
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            # 擷取重要參數
            return {
                "prodsku": params.get("prodsku", [""])[0],
                "intsrc": params.get("intsrc", [""])[0],
                "publisher_id": parsed.path.split("/")[2] if len(parsed.path.split("/")) > 2 else "",
                "offer_id": parsed.path.split("/")[3] if len(parsed.path.split("/")) > 3 else "",
                "campaign_id": parsed.path.split("/")[4] if len(parsed.path.split("/")) > 4 else ""
            }
        except (KeyError, IndexError, ValueError):
            return {}
    
    async def _save_to_database(self, courses: list[dict[str, Any]]):
        """儲存課程到資料庫"""
        print("\n💾 儲存到資料庫...")
        
        # 讀取連線資訊
        with open('temp/postgres_connection.json') as f:
            conn_info = json.load(f)
        
        # 連線到資料庫
        conn = await asyncpg.connect(
            host=conn_info['host'],
            database=conn_info['database'],
            user=conn_info['user'],
            password=conn_info['password'],
            ssl='require'
        )
        
        try:
            # 批次處理
            batch_size = 100
            for i in range(0, len(courses), batch_size):
                batch = courses[i:i + batch_size]
                await self._save_batch(conn, batch)
                
                progress = (i + len(batch)) / len(courses) * 100
                print(f"   進度: {progress:.1f}%")
                
        finally:
            await conn.close()
    
    async def _save_batch(self, conn: asyncpg.Connection, batch: list[dict[str, Any]]):
        """儲存一批課程"""
        async with conn.transaction():
            for course in batch:
                try:
                    # 檢查課程是否存在
                    course_id = f"{course['platform_id']}_{course['external_id']}"
                    
                    existing = await conn.fetchval(
                        "SELECT id FROM courses WHERE id = $1",
                        course_id
                    )
                    
                    if existing:
                        # 更新現有課程
                        await conn.execute("""
                            UPDATE courses SET
                                name = $2,
                                description = $3,
                                manufacturer = $4,
                                current_price = $5,
                                original_price = $6,
                                currency = $7,
                                image_url = $8,
                                stock_status = $9,
                                metadata = $10,
                                last_synced = CURRENT_TIMESTAMP,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = $1
                        """,
                        course_id,
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
                        self.stats["updated_courses"] += 1
                        
                    else:
                        # 插入新課程
                        await conn.execute("""
                            INSERT INTO courses (
                                id, platform_id, external_id, name, description,
                                manufacturer, current_price, original_price,
                                currency, image_url, stock_status, metadata
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
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
                        self.stats["new_courses"] += 1
                    
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
                        course['original_url'],  # 暫時相同, 之後可加入自訂參數
                        json.dumps(course.get('tracking_params', {}))
                        )
                        
                except Exception as e:
                    print(f"   ⚠️  儲存錯誤: {course['name']} - {e}")
                    self.stats["errors"] += 1
    
    async def _create_sync_log(self, sync_log_id: str):
        """建立同步記錄"""
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
            await conn.execute("""
                INSERT INTO sync_logs (id, platform_id, sync_type, status)
                VALUES ($1, $2, $3, $4)
            """, sync_log_id, "coursera", "full", "started")
        finally:
            await conn.close()
    
    async def _update_sync_log(self, sync_log_id: str, status: str, error: str = None):
        """更新同步記錄"""
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
            if status == "completed":
                await conn.execute("""
                    UPDATE sync_logs SET
                        status = $2,
                        completed_at = CURRENT_TIMESTAMP,
                        total_courses = $3,
                        new_courses = $4,
                        updated_courses = $5,
                        failed_courses = $6
                    WHERE id = $1
                """,
                sync_log_id,
                status,
                self.stats["total_fetched"],
                self.stats["new_courses"],
                self.stats["updated_courses"],
                self.stats["errors"]
                )
            else:
                await conn.execute("""
                    UPDATE sync_logs SET
                        status = $2,
                        completed_at = CURRENT_TIMESTAMP,
                        error_details = $3
                    WHERE id = $1
                """,
                sync_log_id,
                status,
                json.dumps({"error": error}) if error else None
                )
        finally:
            await conn.close()


async def main():
    """主程式"""
    etl = CourseraETL()
    await etl.run()


if __name__ == "__main__":
    asyncio.run(main())