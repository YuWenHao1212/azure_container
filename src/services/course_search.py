"""
Course Vector Search Service
使用 pgvector 進行相似課程搜尋
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Any

import asyncpg
from pgvector.asyncpg import register_vector

from src.core.monitoring_service import monitoring_service
from src.services.embedding_client import get_course_embedding_client

logger = logging.getLogger(__name__)


class CourseSearchService:
    """課程向量搜尋服務"""

    def __init__(self):
        self.embedding_client = None
        self._conn_info = None
        self._connection_pool = None

    async def initialize(self):
        """初始化服務"""
        if not self.embedding_client:
            self.embedding_client = get_course_embedding_client()

        # 載入資料庫連線資訊
        if not self._conn_info:
            try:
                # 優先使用 tools 目錄的配置
                with open('tools/coursera_db_manager/config/postgres_connection.json') as f:
                    self._conn_info = json.load(f)
            except FileNotFoundError:
                # 備用路徑
                with open('temp/postgres_connection.json') as f:
                    self._conn_info = json.load(f)

        # 建立連線池
        if not self._connection_pool:
            self._connection_pool = await asyncpg.create_pool(
                host=self._conn_info['host'],
                database=self._conn_info['database'],
                user=self._conn_info['user'],
                password=self._conn_info['password'],
                ssl='require',
                min_size=1,
                max_size=5,
                command_timeout=30
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

    async def close(self):
        """關閉服務"""
        if self.embedding_client:
            await self.embedding_client.close()
        if self._connection_pool:
            await self._connection_pool.close()
