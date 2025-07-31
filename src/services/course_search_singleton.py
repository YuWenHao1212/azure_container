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
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = CourseSearchService()
                    await cls._instance.initialize()
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
