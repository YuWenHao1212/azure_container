"""
Resume Format Models.
Defines request/response models for resume formatting functionality.
"""

from pydantic import BaseModel, Field, validator


class SupplementInfo(BaseModel):
    """補充資訊模型"""
    name: str | None = None
    email: str | None = None
    linkedin: str | None = None
    phone: str | None = None
    location: str | None = None


class ResumeFormatRequest(BaseModel):
    """履歷格式化請求模型"""
    ocr_text: str = Field(
        ..., 
        min_length=100, 
        description="OCR extracted text in format: types line, then content line"
    )
    supplement_info: SupplementInfo | None = Field(
        None,
        description="Optional supplementary information to fill gaps"
    )
    
    @validator('ocr_text')
    def validate_ocr_text(cls, v):
        """驗證 OCR 文字長度和基本格式"""
        if len(v.strip()) < 100:
            raise ValueError("OCR text too short, minimum 100 characters required")
        
        # 檢查是否至少有兩行（types 和 content）
        lines = v.strip().split('\n')
        if len(lines) < 2:
            raise ValueError("OCR text must contain at least 2 lines (types and content)")
            
        return v


class SectionsDetected(BaseModel):
    """檢測到的履歷區段"""
    contact: bool = False
    summary: bool = False
    skills: bool = False
    experience: bool = False
    education: bool = False
    projects: bool = False
    certifications: bool = False


class CorrectionsMade(BaseModel):
    """修正統計"""
    ocr_errors: int = 0
    date_standardization: int = 0
    email_fixes: int = 0
    phone_fixes: int = 0


class ResumeFormatData(BaseModel):
    """履歷格式化回應資料"""
    formatted_resume: str = Field(
        ...,
        description="Formatted HTML resume content"
    )
    sections_detected: SectionsDetected = Field(
        ...,
        description="Detected resume sections"
    )
    corrections_made: CorrectionsMade = Field(
        ...,
        description="Statistics of corrections made"
    )
    supplement_info_used: list[str] = Field(
        default_factory=list,
        description="List of supplement info fields that were used"
    )