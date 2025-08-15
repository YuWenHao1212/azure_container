"""
Global singleton for CourseSearchService to avoid repeated initialization
"""
import asyncio

from src.services.course_search import CourseSearchService


class CourseSearchSingleton:
    """全域課程搜尋服務單例"""
    _instance: CourseSearchService | None = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls) -> CourseSearchService:
        """取得全域單例實例"""
        import logging
        logger = logging.getLogger(__name__)

        # 診斷日誌: 追蹤實例狀態
        if cls._instance is None:
            logger.info("🔍 [Singleton] Instance is None, will create new instance")
        else:
            logger.debug(f"🔍 [Singleton] Existing instance found: {id(cls._instance)}")

        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    logger.info("🔧 [Singleton] Creating new CourseSearchService instance...")
                    cls._instance = CourseSearchService()
                    await cls._instance.initialize()
                    logger.info(f"✅ [Singleton] Created new instance with ID: {id(cls._instance)}")

                    # 診斷: 檢查連接池狀態
                    if cls._instance._connection_pool:
                        logger.info(f"🗄️ [Singleton] Connection pool initialized: {id(cls._instance._connection_pool)}")
                    else:
                        logger.warning("⚠️ [Singleton] Connection pool is None after initialization")

        return cls._instance

    @classmethod
    async def close(cls):
        """關閉單例"""
        if cls._instance:
            await cls._instance.close()
            cls._instance = None

# 便捷函數
async def get_course_search_service() -> CourseSearchService:
    """取得課程搜尋服務實例"""
    return await CourseSearchSingleton.get_instance()
