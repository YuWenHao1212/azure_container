"""
Course Batch Query Models
批次查詢課程詳情的資料模型
"""

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


class CourseDetail(BaseModel):
    """課程詳細資訊"""
    id: str = Field(..., description="課程唯一識別碼")
    name: str = Field(..., description="課程名稱")
    description: str = Field(..., description="課程描述(可截斷)")
    provider: str = Field(..., description="提供者名稱")
    provider_standardized: str = Field(..., description="標準化提供者名稱")
    provider_logo_url: str | None = Field(None, description="提供者 Logo URL")
    price: float = Field(..., description="課程價格")
    currency: str = Field(..., description="貨幣代碼")
    image_url: str | None = Field(None, description="課程圖片 URL")
    affiliate_url: str | None = Field(None, description="聯盟行銷連結")
    course_type: str = Field(..., description="標準化課程類型")
    duration: str | None = Field(None, description="課程時長")
    difficulty: str | None = Field(None, description="難度等級")
    rating: float | None = Field(None, description="評分")
    enrollment_count: int | None = Field(None, description="註冊人數")


class QueryInfo(BaseModel):
    """查詢資訊統計"""
    requested_count: int = Field(..., description="原始請求的 ID 數量")
    processed_count: int = Field(..., description="實際處理的 ID 數量")
    found_count: int = Field(..., description="找到的課程數量")
    not_found_count: int = Field(..., description="查詢但未找到的數量")
    skipped_count: int = Field(..., description="因限制跳過的數量")
    all_not_found: bool = Field(..., description="是否全部都找不到")
    cache_hit_rate: float = Field(..., description="快取命中率")


class TimelineTask(BaseModel):
    """時間線任務"""
    task: str = Field(..., description="任務名稱")
    start_ms: float = Field(..., description="開始時間(毫秒)")
    end_ms: float = Field(..., description="結束時間(毫秒)")
    duration_ms: float = Field(..., description="持續時間(毫秒)")
    description: str = Field(..., description="任務描述")
    skipped: bool = Field(False, description="是否跳過")


class TimeTracking(BaseModel):
    """時間追蹤資訊"""
    enabled: bool = Field(..., description="是否啟用時間追蹤")
    total_ms: float = Field(..., description="總執行時間(毫秒)")
    timeline: list[TimelineTask] = Field(..., description="執行時間線")
    summary: dict[str, float] = Field(..., description="時間分配摘要(百分比)")


class CourseDetailsBatchData(BaseModel):
    """課程批次查詢資料"""
    courses: list[CourseDetail] = Field(
        default_factory=list,
        description="課程列表"
    )
    total_found: int = Field(0, description="找到的總數")
    not_found_ids: list[str] = Field(
        default_factory=list,
        description="未找到的課程 ID"
    )
    query_info: QueryInfo | None = Field(None, description="查詢資訊")


class CourseDetailsBatchMetadata(BaseModel):
    """課程批次查詢元數據"""
    query_time_ms: float = Field(..., description="查詢時間(毫秒)")
    from_cache_count: int = Field(0, description="從快取取得的數量")
    from_db_count: int = Field(0, description="從資料庫取得的數量")
    fallback_url: str | None = Field(None, description="查無課程時的備用連結")
    time_tracking: TimeTracking | None = Field(None, description="時間追蹤資訊")


class ErrorModel(BaseModel):
    """錯誤資訊模型"""
    has_error: bool = Field(False, description="是否有錯誤")
    code: str = Field("", description="錯誤代碼")
    message: str = Field("", description="錯誤訊息")
    details: str = Field("", description="錯誤詳情")


class CourseDetailsBatchResponse(BaseModel):
    """批次查詢課程詳情回應"""
    success: bool = Field(..., description="是否成功")
    data: CourseDetailsBatchData = Field(..., description="回應資料")
    error: ErrorModel = Field(
        default_factory=ErrorModel,
        description="錯誤資訊"
    )
    metadata: CourseDetailsBatchMetadata | None = Field(
        None,
        description="元數據"
    )
    timestamp: str = Field(..., description="時間戳記")
