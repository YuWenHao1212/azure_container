"""Find Course API Endpoints"""
from fastapi import APIRouter

from src.core.monitoring_service import monitoring_service
from src.models.course_search import (
    CourseSearchData,
    CourseSearchRequest,
    CourseSearchResponse,
    ErrorModel,
)
from src.services.course_search_singleton import get_course_search_service

router = APIRouter()

@router.post("/search", response_model=CourseSearchResponse)
async def search_courses(request: CourseSearchRequest) -> CourseSearchResponse:
    """
    搜尋相關課程

    根據技能名稱和搜尋情境, 使用向量相似度搜尋最相關的課程。
    支援 Tech/Non-Tech 分類過濾。
    """
    try:
        # 取得服務實例
        search_service = await get_course_search_service()

        # 執行搜尋
        result = await search_service.search_courses_v2(
            skill_name=request.skill_name,
            search_context=request.search_context,
            limit=request.limit,
            similarity_threshold=request.similarity_threshold
        )

        return result

    except Exception as e:
        # 記錄錯誤
        monitoring_service.track_event("CourseSearchError", {
            "error": str(e),
            "skill_name": request.skill_name,
            "search_context": request.search_context
        })

        # Bubble.io 相容: 總是回傳 200 狀態碼
        return CourseSearchResponse(
            success=False,
            data=CourseSearchData(),
            error=ErrorModel(
                code="SEARCH_ERROR",
                message="Course search failed",
                details=str(e)
            )
        )

# Health check endpoint removed - using unified /health endpoint in main.py
# Course search health status is included in the main health endpoint
