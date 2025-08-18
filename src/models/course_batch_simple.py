"""
Simplified Course Batch Query Models
簡化的批次查詢課程詳情資料模型
"""

from typing import Any

from pydantic import BaseModel, Field


class CourseDetailsBatchRequest(BaseModel):
    """批次查詢課程詳情請求"""
    course_ids: list[str] = Field(
        ...,
        description="課程 ID 列表",
        min_length=1,
        max_length=100,
        example=["coursera_crse:v1-2598", "coursera_crse:v1-2599"]
    )
    max_courses: int | None = Field(
        None,
        description="最多查詢幾個課程(只處理前 N 個 ID)",
        ge=1,
        le=100,
        example=20
    )
    full_description: bool = Field(
        True,
        description="是否返回完整描述",
        example=False
    )
    description_max_length: int = Field(
        500,
        description="描述截斷長度(字元數)",
        ge=50,
        le=2000,
        example=200
    )
    enable_time_tracking: bool = Field(
        True,
        description="啟用時間追蹤",
        example=True
    )


class CourseDetailsBatchResponse(BaseModel):
    """批次查詢課程詳情回應 - 簡化版本"""
    success: bool = Field(..., description="是否成功")
    courses: list[dict[str, Any]] = Field(
        default_factory=list,
        description="課程列表"
    )
    total_found: int = Field(0, description="找到的總數")
    requested_count: int = Field(..., description="請求的 ID 數量")
    processed_count: int = Field(..., description="實際處理的 ID 數量")
    skipped_count: int = Field(0, description="因限制跳過的數量")
    not_found_ids: list[str] = Field(
        default_factory=list,
        description="未找到的課程 ID"
    )
    cache_hit_rate: float = Field(0.0, description="快取命中率")
    from_cache_count: int = Field(0, description="從快取取得的數量")
    all_not_found: bool = Field(False, description="是否全部都找不到")
    fallback_url: str | None = Field(None, description="查無課程時的備用連結")
    time_tracking: dict[str, Any] | None = Field(None, description="時間追蹤資訊")
    error: dict[str, str] = Field(
        default_factory=lambda: {"code": "", "message": "", "details": ""},
        description="錯誤資訊"
    )
