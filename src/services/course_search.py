"""
Course Vector Search Service
使用 pgvector 進行相似課程搜尋
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

import asyncpg
from pgvector.asyncpg import register_vector

from src.core.monitoring_service import monitoring_service
from src.services.embedding_client import get_course_embedding_client

# Conditional import for course batch functionality
if TYPE_CHECKING:
    from src.models.course_batch_simple import (
        CourseDetailsBatchRequest,
        CourseDetailsBatchResponse,
    )

logger = logging.getLogger(__name__)


class CourseSearchService:
    """課程向量搜尋服務"""

    def __init__(self):
        self.embedding_client = None
        self._conn_info = None
        self._connection_pool = None

    async def initialize(self):
        """初始化服務"""
        import logging
        import os

        logger = logging.getLogger(__name__)

        if not self.embedding_client:
            self.embedding_client = get_course_embedding_client()

        # 載入資料庫連線資訊
        if not self._conn_info:
            # 優先從環境變數讀取
            if all(os.getenv(k) for k in ['POSTGRES_HOST', 'POSTGRES_DATABASE', 'POSTGRES_USER', 'POSTGRES_PASSWORD']):
                self._conn_info = {
                    'host': os.getenv('POSTGRES_HOST'),
                    'database': os.getenv('POSTGRES_DATABASE'),
                    'user': os.getenv('POSTGRES_USER'),
                    'password': os.getenv('POSTGRES_PASSWORD')
                }
                logger.info("✅ [CourseSearch] Database config loaded from environment variables")
            else:
                # 嘗試從檔案讀取 (用於本地開發)
                try:
                    # 優先使用 tools 目錄的配置
                    with open('tools/coursera_db_manager/config/postgres_connection.json') as f:
                        self._conn_info = json.load(f)
                        logger.info("✅ [CourseSearch] Database config loaded from tools/coursera_db_manager/config/")
                except FileNotFoundError:
                    try:
                        # 備用路徑
                        with open('temp/postgres_connection.json') as f:
                            self._conn_info = json.load(f)
                            logger.info("✅ [CourseSearch] Database config loaded from temp/")
                    except FileNotFoundError as e:
                        logger.error("❌ [CourseSearch] No database configuration found (neither env vars nor files)")
                        msg = "Database configuration not found. Please set POSTGRES_* environment variables"
                        raise ValueError(msg) from e

        # 建立連線池
        if not self._connection_pool:
            import logging
            import time

            from pgvector.asyncpg import register_vector

            logger = logging.getLogger(__name__)
            start_time = time.time()
            logger.info("🔧 [CourseSearch] Creating connection pool with pgvector registration...")

            # 定義連接初始化函數
            async def init_connection(conn):
                """初始化每個連接: 註冊 pgvector 類型"""
                await register_vector(conn)
                logger.debug(f"✅ [CourseSearch] Registered pgvector for connection {id(conn)}")

            # 建立連線池, 每個連接創建時自動註冊 pgvector
            self._connection_pool = await asyncpg.create_pool(
                host=self._conn_info['host'],
                database=self._conn_info['database'],
                user=self._conn_info['user'],
                password=self._conn_info['password'],
                ssl='require',
                min_size=2,  # Increased for better concurrency
                max_size=20,  # Support up to 20 parallel queries
                command_timeout=30,
                init=init_connection  # 🚀 連接初始化時自動註冊 pgvector
            )
            elapsed = (time.time() - start_time) * 1000
            logger.info(
                f"✅ [CourseSearch] Connection pool created with pgvector "
                f"pre-registered in {elapsed:.1f}ms, ID: {id(self._connection_pool)}"
            )

    async def search_courses(
        self,
        query: str,
        limit: int = 10,
        similarity_threshold: float = 0.3,
        filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        搜尋相似課程

        Args:
            query: 搜尋查詢文字
            limit: 回傳結果數量上限
            similarity_threshold: 相似度門檻 (0-1)
            filters: 額外過濾條件 (例如: {"manufacturer": "Google"})

        Returns:
            相似課程列表, 包含相似度分數
        """
        start_time = datetime.now()

        try:
            # 初始化
            await self.initialize()

            # 產生查詢 embedding
            logger.debug(f"[CourseSearch] Generating embedding for query: {query[:50]}...")
            query_embeddings = await self.embedding_client.create_embeddings([query])

            if not query_embeddings or len(query_embeddings) == 0:
                logger.error("[CourseSearch] Failed to generate query embedding")
                return []

            query_embedding = query_embeddings[0]

            # 從連線池取得連線
            async with self._connection_pool.acquire() as conn:
                # 註冊 vector 類型
                await register_vector(conn)
                # 建立基本查詢
                base_query = """
                    SELECT
                        c.id,
                        c.name,
                        c.description,
                        COALESCE(c.provider_standardized, c.provider) as provider,
                        c.provider_standardized,
                        c.provider_logo_url,
                        c.price as current_price,
                        c.currency,
                        c.image_url,
                        c.affiliate_url,
                        c.course_type_standard as course_type,
                        1 - (c.embedding <=> $1::vector) as similarity
                    FROM courses c
                    WHERE c.platform = 'coursera'
                    AND c.embedding IS NOT NULL
                    AND 1 - (c.embedding <=> $1::vector) >= $2
                """

                params = [query_embedding, similarity_threshold]

                # 加入額外過濾條件
                if filters:
                    filter_conditions = []
                    param_index = 3

                    if 'provider' in filters:
                        filter_conditions.append(f"COALESCE(c.provider_standardized, c.provider) = ${param_index}")
                        params.append(filters['provider'])
                        param_index += 1

                    if 'max_price' in filters:
                        filter_conditions.append(f"c.current_price <= ${param_index}")
                        params.append(filters['max_price'])
                        param_index += 1

                    if 'category' in filters:
                        filter_conditions.append(f"c.category = ${param_index}")
                        params.append(filters['category'])
                        param_index += 1

                    # 支援 category_list 過濾 (多個分類)
                    if 'category_list' in filters:
                        placeholders = ','.join([f'${param_index + i}' for i in range(len(filters['category_list']))])
                        filter_conditions.append(f"c.category IN ({placeholders})")
                        params.extend(filters['category_list'])
                        param_index += len(filters['category_list'])

                    if filter_conditions:
                        base_query += " AND " + " AND ".join(filter_conditions)

                # 加入排序和限制
                base_query += f"""
                    ORDER BY similarity DESC
                    LIMIT ${len(params) + 1}
                """
                params.append(limit)

                # 執行查詢
                logger.debug(
                    f"[CourseSearch] Executing vector search with threshold={similarity_threshold}, "
                    f"limit={limit}"
                )
                results = await conn.fetch(base_query, *params)

                # 格式化結果
                courses = []
                for row in results:
                    course = {
                        "id": row['id'],
                        "name": row['name'],
                        "description": (
                            row['description'][:500] + "..."
                            if len(row['description']) > 500 else row['description']
                        ),
                        "provider": row['provider'],
                        "provider_standardized": row['provider_standardized'] or '',
                        "provider_logo_url": row['provider_logo_url'] or '',
                        "price": float(row['current_price']),
                        "currency": row['currency'],
                        "image_url": row['image_url'],
                        "affiliate_url": row.get('affiliate_url') or '',
                        "course_type": row.get('course_type', 'course'),
                        "similarity_score": round(float(row['similarity']), 4)
                    }
                    courses.append(course)

                duration = (datetime.now() - start_time).total_seconds()

                # 記錄監控資訊
                monitoring_service.track_event("CourseSearchCompleted", {
                    "query": query[:100],
                    "results_count": len(courses),
                    "duration_seconds": duration,
                    "similarity_threshold": similarity_threshold,
                    "has_filters": bool(filters)
                })

                logger.info(f"[CourseSearch] Found {len(courses)} courses in {duration:.2f}s")

                return courses

        except Exception as e:
            logger.error(f"[CourseSearch] Error: {e}")
            monitoring_service.track_event("CourseSearchError", {
                "query": query[:100],
                "error": str(e)
            })
            raise

    async def find_similar_courses(
        self,
        course_id: str,
        limit: int = 5
    ) -> list[dict[str, Any]]:
        """
        找出與指定課程相似的其他課程

        Args:
            course_id: 課程 ID
            limit: 回傳結果數量上限

        Returns:
            相似課程列表
        """
        await self.initialize()

        # 建立資料庫連線
        conn = await asyncpg.connect(
            host=self._conn_info['host'],
            database=self._conn_info['database'],
            user=self._conn_info['user'],
            password=self._conn_info['password'],
            ssl='require'
        )

        # 註冊 vector 類型
        await register_vector(conn)

        try:
            # 取得目標課程的 embedding
            target_embedding = await conn.fetchval("""
                SELECT embedding
                FROM courses
                WHERE id = $1
            """, course_id)

            if target_embedding is None:
                return []

            # 搜尋相似課程 (排除自己)
            results = await conn.fetch("""
                SELECT
                    c.id,
                    c.name,
                    c.description,
                    COALESCE(c.provider_standardized, c.provider) as provider,
                    c.provider_standardized,
                    c.provider_logo_url,
                    c.price as current_price,
                    c.currency,
                    c.image_url,
                    c.affiliate_url,
                    c.course_type,
                    1 - (c.embedding <=> $1::vector) as similarity
                FROM courses c
                WHERE c.id != $2
                AND c.platform = 'coursera'
                AND c.embedding IS NOT NULL
                ORDER BY c.embedding <=> $1::vector
                LIMIT $3
            """, target_embedding, course_id, limit)

            # 不再需要映射, 直接使用 course_type_standard

            # 格式化結果
            similar_courses = []
            for row in results:
                # 直接使用 course_type_standard
                course_type = row.get('course_type', 'course')

                # 將 similarity 轉換為整數百分比
                similarity_percentage = int(float(row['similarity']) * 100)

                course = {
                    "id": row['id'],
                    "name": row['name'],
                    "description": (
                        row['description'][:300] + "..."
                        if len(row['description']) > 300 else row['description']
                    ),
                    "provider": row['provider'],
                    "provider_standardized": row['provider_standardized'] or '',
                    "provider_logo_url": row['provider_logo_url'] or '',
                    "price": float(row['current_price']),
                    "currency": row.get('currency', 'USD'),
                    "image_url": row['image_url'],
                    "affiliate_url": row.get('affiliate_url', ''),
                    "course_type": course_type,
                    "similarity_score": similarity_percentage
                }
                similar_courses.append(course)

            return similar_courses

        finally:
            await conn.close()

    async def get_popular_categories(self) -> list[dict[str, Any]]:
        """取得熱門課程分類"""
        await self.initialize()

        conn = await asyncpg.connect(
            host=self._conn_info['host'],
            database=self._conn_info['database'],
            user=self._conn_info['user'],
            password=self._conn_info['password'],
            ssl='require'
        )

        try:
            results = await conn.fetch("""
                SELECT
                    category,
                    COUNT(*) as course_count
                FROM courses
                WHERE platform = 'coursera'
                AND category IS NOT NULL
                AND category != ''
                GROUP BY category
                ORDER BY course_count DESC
                LIMIT 20
            """)

            categories = [
                {
                    "name": row['category'],
                    "course_count": row['course_count']
                }
                for row in results
            ]

            return categories

        finally:
            await conn.close()

    async def search_courses_v2(
        self,
        skill_name: str,
        search_context: str = "",
        limit: int = 5,
        similarity_threshold: float = 0.3
    ) -> dict[str, Any]:
        """
        改進版課程搜尋 (第二版)

        Args:
            skill_name: 技能名稱
            search_context: 搜尋情境描述
            limit: 回傳結果數量 (預設 5, 最大 10)
            similarity_threshold: 相似度門檻 (預設 0.3)

        Returns:
            CourseSearchResponse 格式的字典
        """
        from src.models.course_search import (
            CourseResult,
            CourseSearchData,
            CourseSearchResponse,
            CourseTypeCount,
            ErrorModel,
        )
        from src.services.course_cache import CourseSearchCache

        start_time = datetime.now()

        # 初始化快取
        if not hasattr(self, 'cache'):
            self.cache = CourseSearchCache()

        # 建立快取鍵值
        cache_key = self.cache.get_cache_key(
            skill_name, search_context, "", similarity_threshold
        )

        # 檢查快取
        cached_result = self.cache.get(cache_key)
        if cached_result:
            monitoring_service.track_event("CourseSearchCacheHit", {
                "skill_name": skill_name,
                "cache_key": cache_key
            })
            return CourseSearchResponse(**cached_result)

        try:
            # 建立查詢文本
            query_text = f"{skill_name} {search_context}".strip()

            # 向量搜尋 (含重試)
            courses = await self._search_with_retry(
                query_text=query_text,
                limit=limit,
                threshold=similarity_threshold
            )

            # 建立回應
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # 格式化課程結果並統計類型
            course_results = []
            type_counts = {
                'course': 0,
                'certification': 0,
                'specialization': 0,
                'degree': 0,
                'project': 0
            }

            for course in courses:
                # 將 similarity_score 轉換為整數百分比
                similarity_percentage = int(float(course.get('similarity_score', 0)) * 100)

                # 取得課程類型
                course_type = course.get('course_type', 'course')

                # 統計課程類型 (直接使用 course_type_standard 的值)
                if course_type in type_counts:
                    type_counts[course_type] += 1

                course_result = CourseResult(
                    id=course['id'],
                    name=course['name'],
                    description=course['description'][:500] + "..."
                               if len(course.get('description', '')) > 500
                               else course.get('description', ''),
                    provider=course.get('provider', ''),
                    provider_standardized=course.get('provider_standardized', ''),
                    provider_logo_url=course.get('provider_logo_url', ''),
                    price=float(course.get('price', 0)),
                    currency=course.get('currency', 'USD'),
                    image_url=course.get('image_url', ''),
                    affiliate_url=course.get('affiliate_url', ''),
                    course_type=course_type,
                    similarity_score=similarity_percentage
                )
                course_results.append(course_result)

            response = CourseSearchResponse(
                success=True,
                data=CourseSearchData(
                    results=course_results,
                    total_count=len(course_results),
                    returned_count=len(course_results),
                    query=query_text,
                    search_time_ms=duration_ms,
                    filters_applied={
                        "similarity_threshold": similarity_threshold
                    },
                    type_counts=CourseTypeCount(**type_counts)
                ),
                error=ErrorModel()
            )

            # 存入快取
            self.cache.set(cache_key, response.model_dump())

            # 記錄監控
            self._track_search_success(skill_name, search_context, courses, duration_ms)

            return response

        except Exception as e:
            # 記錄錯誤
            self._track_search_error(e, skill_name, search_context)

            # 回傳錯誤 (Bubble.io 相容)
            return CourseSearchResponse(
                success=False,
                data=CourseSearchData(),
                error=ErrorModel(
                    code=self._get_error_code(e),
                    message="Search failed",
                    details=str(e)
                )
            )

    async def _search_with_retry(
        self,
        query_text: str,
        limit: int,
        threshold: float,
        max_retries: int = 3
    ) -> list[dict]:
        """含重試機制的搜尋"""
        retry_delays = [1.0, 2.0, 4.0]

        for attempt in range(max_retries):
            try:
                # 初始化服務
                await self.initialize()

                # 產生 embedding
                logger.debug(f"[CourseSearch] Generating embedding for: {query_text[:50]}...")
                embeddings = await self.embedding_client.create_embeddings([query_text])

                if not embeddings or len(embeddings) == 0:
                    raise Exception("Failed to generate embeddings")

                query_embedding = embeddings[0]

                # 執行向量搜尋
                courses = await self._execute_vector_search_v2(
                    embedding=query_embedding,
                    filters={},
                    limit=limit,
                    threshold=threshold
                )

                return courses

            except Exception as e:
                logger.warning(f"[CourseSearch] Attempt {attempt + 1} failed: {e}")

                if attempt == max_retries - 1:
                    raise Exception(f"Search failed after {max_retries} attempts: {e!s}") from e

                await asyncio.sleep(retry_delays[attempt])

    async def _execute_vector_search_v2(
        self,
        embedding: list[float],
        filters: dict[str, Any],
        limit: int,
        threshold: float
    ) -> list[dict[str, Any]]:
        """執行向量搜尋 (第二版)"""
        # 從連線池取得連線
        async with self._connection_pool.acquire() as conn:
            # 註冊 vector 類型
            await register_vector(conn)
            # 建立基本查詢
            base_query = """
                SELECT
                    c.id,
                    c.name,
                    c.description,
                    COALESCE(c.provider_standardized, c.provider) as provider,
                    c.provider_standardized,
                    c.provider_logo_url,
                    c.price as current_price,
                    c.currency,
                    c.image_url,
                    c.affiliate_url as tracking_url,
                    c.course_type_standard as course_type,
                    1 - (c.embedding <=> $1::vector) as similarity_score
                FROM courses c
                WHERE c.platform = 'coursera'
                AND c.embedding IS NOT NULL
                AND 1 - (c.embedding <=> $1::vector) >= $2
            """

            params = [embedding, threshold]

            # 加入分類過濾
            if 'category_list' in filters:
                placeholders = ','.join([f'${i+3}' for i in range(len(filters['category_list']))])
                base_query += f" AND c.category IN ({placeholders})"
                params.extend(filters['category_list'])

            # 加入排序和限制
            base_query += f"""
                ORDER BY c.embedding <=> $1::vector
                LIMIT ${len(params) + 1}
            """
            params.append(limit)

            # 執行查詢
            logger.debug(f"[CourseSearch] Executing vector search with threshold={threshold}, limit={limit}")
            results = await conn.fetch(base_query, *params)

            # 不再需要映射, 直接使用 course_type_standard

            # 格式化結果
            courses = []
            for row in results:
                # 直接使用 course_type_standard
                course_type = row.get('course_type', 'course')

                course = {
                    "id": row['id'],
                    "name": row['name'],
                    "description": row['description'],
                    "provider": row['provider'],
                    "provider_standardized": row['provider_standardized'] or '',
                    "provider_logo_url": row['provider_logo_url'] or '',
                    "price": float(row['current_price']),
                    "currency": row['currency'],
                    "image_url": row['image_url'],
                    "affiliate_url": row['tracking_url'] or '',
                    "course_type": course_type,
                    "similarity_score": float(row['similarity_score'])
                }
                courses.append(course)

            logger.info(f"[CourseSearch] Found {len(courses)} courses")
            return courses

    def _track_search_success(self, skill_name: str, search_context: str,
                             courses: list, duration_ms: int):
        """記錄成功的搜尋"""
        course_ids = [c['id'] for c in courses[:5]]
        similarity_scores = [c.get('similarity_score', 0) for c in courses[:5]]

        monitoring_service.track_event("CourseSearchExecuted", {
            "skill_name": skill_name,
            "search_context": search_context,
            "result_count": len(courses),
            "course_ids": course_ids,
            "similarity_scores": similarity_scores,
            "search_duration_ms": duration_ms,
            "success": True
        })

    def _track_search_error(self, error: Exception, skill_name: str,
                           search_context: str):
        """記錄搜尋錯誤"""
        monitoring_service.track_event("CourseSearchError", {
            "error_code": self._get_error_code(error),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "skill_name": skill_name,
            "search_context": search_context
        })

    def _get_error_code(self, error: Exception) -> str:
        """取得錯誤代碼"""
        error_type = type(error).__name__

        if "embedding" in str(error).lower():
            return "EMBEDDING_GENERATION_FAILED"
        elif "connection" in str(error).lower():
            return "DATABASE_CONNECTION_ERROR"
        elif "timeout" in str(error).lower():
            return "QUERY_TIMEOUT"
        else:
            return f"UNKNOWN_ERROR_{error_type.upper()}"

    def format_description_to_html(self, description: str) -> str:
        """
        將課程描述轉換為 HTML 格式, 供 Bubble.io HTML 元件直接顯示

        處理項目:
        1. HTML 特殊字元轉義 (必須)
        2. 換行符號處理 (必須)
        3. URL 自動轉連結 (建議)
        4. Markdown 粗體/斜體 (建議)
        5. Bullet points (建議)

        Args:
            description: 原始課程描述文字

        Returns:
            HTML 格式化的描述
        """
        import html
        import re

        if not description:
            return ""

        # 0. 先處理字面字符串的 \n (從資料庫讀取的)
        # 資料庫中儲存的是兩個字元: 反斜線和n, 不是真正的換行符
        description = description.replace('\\n', '\n')


        # 1. HTML 特殊字元轉義 (最重要, 防止破壞 HTML 結構)
        description = html.escape(description)

        # 2. 處理 Markdown 粗體 **text** → <strong>text</strong>
        # 使用 <strong> 而非 <b> 更符合語義化 HTML
        description = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', description)

        # 3. 處理 Markdown 斜體 *text* → <em>text</em>
        # 避免與分隔線衝突, 確保前後都不是 *
        description = re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)', r'<em>\1</em>', description)

        # 4. 處理 URL 自動轉換為可點擊連結
        # 使用 target="_blank" 在新視窗開啟, rel="noopener" 提高安全性
        description = re.sub(
            r'(https?://[^\s<>)"\']+)',
            r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>',
            description
        )

        # 5. 處理段落和換行
        # 先分割成段落 (連續兩個換行)
        paragraphs = description.split('\n\n')
        formatted_paragraphs = []

        for para in paragraphs:
            if not para.strip():
                continue

            # 檢查是否包含 bullet points
            lines = para.split('\n')
            has_bullets = any(line.strip().startswith(('•', '●', '■', '▪')) for line in lines)

            if has_bullets:
                # 處理 bullet list
                list_items = []
                non_list_content = []

                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    # 檢查是否是 bullet point
                    is_bullet = False
                    for bullet in ['•', '●', '■', '▪']:
                        if line.startswith(bullet):
                            # 移除 bullet 符號並加入列表
                            content = line[len(bullet):].strip()
                            list_items.append(f'<li>{content}</li>')
                            is_bullet = True
                            break

                    # 檢查 - 或 * 作為 bullet (需要後面有空格)
                    if not is_bullet and len(line) > 2 and line[0] in ['-', '*'] and line[1] == ' ':
                        content = line[2:].strip()
                        list_items.append(f'<li>{content}</li>')
                        is_bullet = True

                    if not is_bullet and not list_items:
                        # 還沒開始列表的內容
                        non_list_content.append(line)

                # 組合結果
                if non_list_content:
                    # 列表前的文字, 單換行轉為 <br>
                    text = '<br>'.join(non_list_content)
                    formatted_paragraphs.append(f'<p>{text}</p>')

                if list_items:
                    # 添加無序列表
                    formatted_paragraphs.append(f'<ul>{"".join(list_items)}</ul>')
            else:
                # 普通段落, 將單換行轉為 <br>
                para_html = para.replace('\n', '<br>')
                formatted_paragraphs.append(f'<p>{para_html}</p>')

        # 組合所有段落
        return ''.join(formatted_paragraphs)

    async def get_courses_by_ids(
        self,
        request: "CourseDetailsBatchRequest"
    ) -> "CourseDetailsBatchResponse":
        """
        批次查詢課程詳情 by IDs

        Args:
            request: 批次查詢請求物件

        Returns:
            CourseDetailsBatchResponse: 課程詳情回應
        """
        from datetime import datetime

        from src.models.course_batch_simple import CourseDetailsBatchResponse
        from src.services.course_cache import CourseSearchCache

        start_time = datetime.now()
        timeline = []

        def track_time(task: str, description: str, start: datetime) -> dict:
            """追蹤任務時間"""
            duration_ms = int((datetime.now() - start).total_seconds() * 1000)
            if request.enable_time_tracking and duration_ms > 50:  # 只記錄超過 50ms 的操作
                timeline.append({
                    "task": task,
                    "duration_ms": duration_ms,
                    "description": description
                })
            return {"duration": duration_ms}

        try:
            # 1. 準備階段
            prep_start = datetime.now()

            # 處理 max_courses 限制
            course_ids = request.course_ids[:request.max_courses] if request.max_courses else request.course_ids
            skipped_count = len(request.course_ids) - len(course_ids)

            track_time("preparation", "Input validation and limits", prep_start)

            # 2. 快取操作
            cache_start = datetime.now()

            # 初始化快取
            if not hasattr(self, 'cache'):
                self.cache = CourseSearchCache()

            # 檢查快取
            cached_courses = []
            uncached_ids = []

            for course_id in course_ids:
                cache_key = f"course_detail:{course_id}:{request.full_description}:{request.description_max_length}"
                cached = self.cache.get(cache_key)
                if cached:
                    cached_courses.append(cached)
                else:
                    uncached_ids.append(course_id)

            track_time("cache_operations", "Check cached courses", cache_start)

            # 3. 資料庫操作
            db_courses = []
            if uncached_ids:
                db_start = datetime.now()

                # 初始化連線
                await self.initialize()

                # 批次查詢
                async with self._connection_pool.acquire() as conn:
                    # 使用 array_position 保持順序
                    query = """
                        SELECT
                            id,
                            name,
                            description,
                            COALESCE(provider_standardized, provider) as provider,
                            provider_standardized,
                            provider_logo_url,
                            price as current_price,
                            currency,
                            image_url,
                            affiliate_url,
                            course_type_standard as course_type,
                            array_position($1::text[], id) as sort_order
                        FROM courses
                        WHERE id = ANY($1::text[])
                        AND platform = 'coursera'
                        ORDER BY array_position($1::text[], id)
                    """

                    results = await conn.fetch(query, uncached_ids)

                    for row in results:
                        # 處理描述
                        description = row['description'] or ''

                        # 根據 format_description_html 決定是否格式化
                        if request.format_description_html:
                            # HTML 格式化處理
                            description_field = self.format_description_to_html(description)
                        else:
                            # 標準描述處理 (可能截斷)
                            if not request.full_description and len(description) > request.description_max_length:
                                description_field = description[:request.description_max_length] + "..."
                            else:
                                description_field = description

                        course = {
                            "id": row['id'],
                            "name": row['name'],
                            "description": description_field,  # 固定使用 description 欄位
                            "provider": row['provider'],
                            "provider_standardized": row['provider_standardized'] or '',
                            "provider_logo_url": row['provider_logo_url'] or '',
                            "price": float(row['current_price'] or 0),
                            "currency": row['currency'] or 'USD',
                            "image_url": row['image_url'] or '',
                            "affiliate_url": row['affiliate_url'] or '',
                            "course_type": row['course_type'] or 'course'
                        }

                        db_courses.append(course)

                        # 快取結果
                        cache_key = (
                            f"course_detail:{row['id']}:"
                            f"{request.full_description}:{request.description_max_length}"
                        )
                        self.cache.set(cache_key, course)

                track_time("db_operations", "Query uncached courses", db_start)

            # 4. 處理與組合結果
            process_start = datetime.now()

            # 合併結果並保持原始順序
            all_courses = cached_courses + db_courses
            courses_dict = {c['id']: c for c in all_courses}

            # 按原始順序排序
            ordered_courses = []
            not_found_ids = []

            for course_id in course_ids:
                if course_id in courses_dict:
                    ordered_courses.append(courses_dict[course_id])
                else:
                    not_found_ids.append(course_id)

            track_time("processing", "Format and build response", process_start)

            # 計算統計
            total_found = len(ordered_courses)
            cache_hit_rate = len(cached_courses) / len(course_ids) if course_ids else 0
            all_not_found = total_found == 0

            # 建立時間追蹤摘要
            time_tracking = None
            if request.enable_time_tracking:
                total_ms = int((datetime.now() - start_time).total_seconds() * 1000)

                # 計算百分比
                summary = {}
                for item in timeline:
                    key = f"{item['task']}_pct"
                    summary[key] = round((item['duration_ms'] / total_ms) * 100, 1) if total_ms > 0 else 0

                time_tracking = {
                    "enabled": True,
                    "total_ms": total_ms,
                    "timeline": timeline,
                    "summary": summary
                }

            # 返回結果
            return CourseDetailsBatchResponse(
                success=True,
                courses=ordered_courses,
                total_found=total_found,
                requested_count=len(request.course_ids),
                processed_count=len(course_ids),
                skipped_count=skipped_count,
                not_found_ids=not_found_ids,
                cache_hit_rate=round(cache_hit_rate, 2),
                from_cache_count=len(cached_courses),
                all_not_found=all_not_found,
                fallback_url="https://imp.i384100.net/mOkdyq" if all_not_found else None,
                time_tracking=time_tracking,
                error={"code": "", "message": "", "details": ""}
            )

        except Exception as e:
            logger.error(f"[CourseBatch] Error in get_courses_by_ids: {e}")

            # 返回錯誤回應
            return CourseDetailsBatchResponse(
                success=False,
                courses=[],
                total_found=0,
                requested_count=len(request.course_ids),
                processed_count=0,
                skipped_count=0,
                not_found_ids=request.course_ids,
                cache_hit_rate=0.0,
                from_cache_count=0,
                all_not_found=True,
                fallback_url="https://imp.i384100.net/mOkdyq",
                time_tracking=None,
                error={
                    "code": "BATCH_QUERY_ERROR",
                    "message": "Failed to query courses",
                    "details": str(e)
                }
            )
