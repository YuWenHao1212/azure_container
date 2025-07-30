"""
Language handler for multi-language support in resume tailoring.
"""



class LanguageHandler:
    """Handles language-related operations for resume tailoring"""
    
    SUPPORTED_LANGUAGES = ["en", "zh-TW"]
    DEFAULT_LANGUAGE = "en"
    
    # Language name mapping for LLM
    LANGUAGE_NAMES = {
        "en": "English",
        "zh-TW": "Traditional Chinese (繁體中文)"
    }
    
    # Section name mappings for different languages
    SECTION_MAPPINGS = {
        "en": {
            "summary": ["summary", "objective", "profile", "about"],
            "experience": ["experience", "work experience", "employment", "work"],
            "education": ["education", "academic", "academic background"],
            "skills": ["skills", "expertise", "competencies", "technical skills"],
            "projects": ["projects", "portfolio", "personal projects"],
            "certifications": ["certifications", "certificates", "licenses"]
        },
        "zh-TW": {
            "summary": ["摘要", "簡介", "個人簡介", "自我介紹", "summary"],
            "experience": ["工作經驗", "工作經歷", "經歷", "experience"],
            "education": ["教育背景", "學歷", "教育", "education"],
            "skills": ["技能", "專長", "專業技能", "skills"],
            "projects": ["專案", "項目", "作品集", "projects"],
            "certifications": ["證照", "認證", "資格", "certifications"]
        }
    }
    
    @classmethod
    def get_prompt_version(cls, language: str) -> str:
        """Get prompt version for the language"""
        # Using single YAML file with language parameter
        return "v1.1.0"
    
    @classmethod
    def get_output_language(cls, language_code: str) -> str:
        """Convert language code to LLM-understandable language name"""
        return cls.LANGUAGE_NAMES.get(language_code, cls.LANGUAGE_NAMES[cls.DEFAULT_LANGUAGE])
    
    @classmethod
    def is_supported_language(cls, language: str) -> bool:
        """Check if language is supported"""
        return language in cls.SUPPORTED_LANGUAGES
    
    @classmethod
    def normalize_section_name(cls, section_name: str, language: str) -> str:
        """Normalize section name to standard format"""
        section_lower = section_name.lower().strip()
        
        mappings = cls.SECTION_MAPPINGS.get(language, cls.SECTION_MAPPINGS[cls.DEFAULT_LANGUAGE])
        
        for standard_name, variations in mappings.items():
            if section_lower in [v.lower() for v in variations]:
                return standard_name
                
        # If not found in mappings, return original
        return section_name
    
    @classmethod
    def get_section_variations(cls, standard_name: str, language: str) -> list:
        """Get all variations of a section name in the specified language"""
        mappings = cls.SECTION_MAPPINGS.get(language, cls.SECTION_MAPPINGS[cls.DEFAULT_LANGUAGE])
        return mappings.get(standard_name, [standard_name])
    
    @classmethod
    def get_placeholder_descriptions(cls, language: str) -> dict[str, str]:
        """Get placeholder descriptions in the specified language"""
        if language == "zh-TW":
            return {
                "[TEAM SIZE]": "團隊人數",
                "[PERCENTAGE]": "百分比",
                "[AMOUNT]": "金額",
                "[NUMBER]": "數量",
                "[TIME PERIOD]": "時間週期",
                "[USER COUNT]": "用戶數量"
            }
        else:
            return {
                "[TEAM SIZE]": "team size",
                "[PERCENTAGE]": "percentage",
                "[AMOUNT]": "amount",
                "[NUMBER]": "number",
                "[TIME PERIOD]": "time period",
                "[USER COUNT]": "user count"
            }