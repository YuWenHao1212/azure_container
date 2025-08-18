"""Course Batch Query API Endpoints"""
from fastapi import APIRouter, status

from src.core.monitoring_service import monitoring_service
from src.decorators.error_handler import handle_api_errors
from src.models.course_batch_simple import (
    CourseDetailsBatchRequest,
    CourseDetailsBatchResponse,
)
from src.services.course_search_singleton import get_course_search_service

router = APIRouter()


@router.post(
    "/get-by-ids",
    response_model=CourseDetailsBatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch Query Course Details",
    description=(
        "Query multiple course details by their IDs. Supports caching, "
        "description truncation, and time tracking for performance monitoring."
    ),
    responses={
        200: {
            "description": "Courses retrieved successfully",
            "model": CourseDetailsBatchResponse
        },
        401: {"description": "Missing or invalid API key"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
        503: {"description": "Database service unavailable"}
    },
    tags=["Courses"]
)
@handle_api_errors(api_name="course_batch_query")
async def get_courses_by_ids(request: CourseDetailsBatchRequest) -> CourseDetailsBatchResponse:
    """
    批次查詢課程詳情

    根據課程 ID 列表批次查詢課程詳細資訊, 支援 Bubble.io 前端展示。
    包含快取機制、描述截斷、時間追蹤等功能。

    Args:
        request: 批次查詢請求, 包含課程 ID 列表和查詢選項

    Returns:
        CourseDetailsBatchResponse: 包含課程詳情、查詢統計和時間追蹤資訊
    """
    try:
        # 取得服務實例
        search_service = await get_course_search_service()

        # 執行批次查詢(直接傳遞 request 物件)
        result = await search_service.get_courses_by_ids(request)

        # 直接返回結果(已經是 CourseDetailsBatchResponse 物件)
        return result

    except Exception as e:
        # 記錄錯誤
        monitoring_service.track_event("CourseBatchQueryError", {
            "error": str(e),
            "course_count": len(request.course_ids),
            "max_courses": request.max_courses
        })

        # 建立錯誤回應
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
