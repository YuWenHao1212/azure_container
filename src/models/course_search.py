"""Course Search Models for Bubble.io compatibility"""
from typing import Any, ClassVar

from pydantic import BaseModel, validator


class CourseSearchRequest(BaseModel):
    """課程搜尋請求模型"""
    skill_name: str
    search_context: str = ""
    limit: int = 5
    similarity_threshold: float = 0.3

    @validator('skill_name')
    def validate_skill_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("skill_name cannot be empty")
        if len(v) > 100:
            raise ValueError("skill_name too long (max 100 chars)")
        return v

    @validator('search_context')
    def validate_search_context(cls, v):
        if len(v) > 500:
            raise ValueError("search_context too long (max 500 chars)")
        return v

    @validator('limit')
    def validate_limit(cls, v):
        return max(1, min(v, 10))

    @validator('similarity_threshold')
    def validate_threshold(cls, v):
        return max(0.1, min(v, 1.0))

    class Config:
        schema_extra: ClassVar[dict] = {
            "example": {
                "skill_name": "Python",
                "search_context": "for data analysis and machine learning",
                "limit": 5,
                "similarity_threshold": 0.3
            }
        }

class CourseResult(BaseModel):
    """單一課程結果"""
    id: str = ""
    name: str = ""
    description: str = ""
    provider: str = ""
    provider_standardized: str = ""
    provider_logo_url: str = ""
    price: float = 0.0
    currency: str = "USD"
    image_url: str = ""
    affiliate_url: str = ""
    course_type: str = ""
    similarity_score: int = 0

class CourseTypeCount(BaseModel):
    """課程類型數量統計"""
    course: int = 0
    certification: int = 0  # 原 professional_certificate
    specialization: int = 0
    degree: int = 0
    project: int = 0  # 原 guided_project

class CourseSearchData(BaseModel):
    """搜尋結果資料"""
    results: list[CourseResult] = []
    total_count: int = 0
    returned_count: int = 0
    query: str = ""
    search_time_ms: int = 0
    filters_applied: dict[str, Any] = {}
    type_counts: CourseTypeCount = CourseTypeCount()

class ErrorModel(BaseModel):
    """錯誤模型"""
    code: str = ""
    message: str = ""
    details: str = ""

class CourseSearchResponse(BaseModel):
    """課程搜尋回應 (Bubble.io 相容)"""
    success: bool
    data: CourseSearchData
    error: ErrorModel
