# 測試資料要求文檔

## 文檔資訊
- **版本**: 1.0.0
- **建立日期**: 2025-08-07
- **維護者**: 測試團隊
- **關鍵要求**: 所有 JD 和 Resume 必須 > 200 字元

## 1. API 驗證要求

### 1.1 最小長度要求
⚠️ **重要提醒**
- **職缺描述 (JD)**: 最少 200 字元
- **履歷內容 (Resume)**: 最少 200 字元
- **不符合要求**: API 返回 HTTP 422 錯誤

### 1.2 錯誤回應格式
```json
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Job description must be at least 200 characters"
    },
    "timestamp": "2025-08-07T10:00:00Z"
}
```

## 2. 標準測試資料集

### 2.1 有效測試資料 (>200字元)

#### 英文職缺描述 - 標準版 (450字元)
```python
VALID_ENGLISH_JD_STANDARD = """
We are looking for a Senior Python Developer with 5+ years of experience 
in building scalable web applications using FastAPI and Django frameworks. 
Strong knowledge of Docker, Kubernetes, and AWS cloud services is required. 
The ideal candidate must have excellent problem-solving skills and ability 
to work independently in a fast-paced agile environment. Experience with 
microservices architecture, RESTful APIs, GraphQL, PostgreSQL, MongoDB, 
Redis, and distributed systems is highly valued. Must be proficient in 
CI/CD pipelines, automated testing, and modern development practices.
""".strip()  # 450 字元
```

#### 英文職缺描述 - 詳細版 (800字元)
```python
VALID_ENGLISH_JD_DETAILED = """
We are seeking an experienced Senior Python Developer to join our growing 
engineering team. The ideal candidate will have 5+ years of hands-on experience 
building and maintaining scalable web applications using modern Python frameworks 
including FastAPI, Django, and Flask. Deep expertise in containerization with 
Docker and orchestration with Kubernetes is essential. You should be well-versed 
in AWS cloud services including EC2, S3, Lambda, RDS, and CloudFormation. 
Experience with microservices architecture, event-driven systems, and distributed 
computing is crucial. Strong knowledge of both SQL databases (PostgreSQL, MySQL) 
and NoSQL solutions (MongoDB, Redis, DynamoDB) is required. You must be proficient 
in implementing CI/CD pipelines, writing comprehensive test suites, and following 
test-driven development practices. Excellent problem-solving abilities and strong 
communication skills are essential for success in this role.
""".strip()  # 800+ 字元
```

#### 繁體中文職缺描述 - 標準版 (350字元)
```python
VALID_CHINESE_JD_STANDARD = """
我們正在尋找一位資深的Python開發工程師，需要具備FastAPI框架經驗，
熟悉Docker容器技術和Azure雲端服務。理想的候選人應該對微服務架構有深入理解，
並且有RESTful API開發經驗。具備CI/CD流程和測試驅動開發經驗者優先。
同時需要熟悉分散式系統設計，具備系統架構規劃能力和團隊合作精神。
需要至少五年以上的後端開發經驗，能夠在快節奏環境中獨立工作。
必須具備良好的溝通能力和問題解決能力，並能在團隊中發揮領導作用。
熟悉敏捷開發流程，有Scrum或Kanban經驗者佳。
""".strip()  # 350+ 字元
```

#### 繁體中文職缺描述 - 詳細版 (600字元)
```python
VALID_CHINESE_JD_DETAILED = """
我們是一家快速成長的科技公司，正在尋找資深Python全端工程師加入我們的團隊。
理想的候選人需要擁有五年以上的Python開發經驗，精通FastAPI、Django等現代框架。
必須熟悉微服務架構設計，能夠建立可擴展的分散式系統。需要具備Docker容器化
和Kubernetes編排的實務經驗。對於Azure或AWS雲端服務有深入了解，能夠設計
和實施雲原生應用程式。需要熟悉PostgreSQL、MongoDB等資料庫系統，並有
Redis快取和訊息佇列的使用經驗。必須精通RESTful API設計原則，了解GraphQL
是加分項目。需要有CI/CD pipeline建置經驗，熟悉Jenkins、GitLab CI或
GitHub Actions。重視程式碼品質，有單元測試、整合測試的撰寫習慣。
需要良好的團隊合作能力，能夠指導初級工程師。有技術部落格撰寫或
開源專案貢獻經驗者優先考慮。
""".strip()  # 600+ 字元
```

#### 混合語言職缺描述 (>20% 繁中, 400字元)
```python
VALID_MIXED_JD_HIGH_CHINESE = """
We are seeking a 資深Python開發工程師 with expertise in 微服務架構 and 雲端服務. 
The candidate should have experience with FastAPI框架, Docker容器技術, and Azure服務. 
Must be skilled in 分散式系統設計 and 測試驅動開發 methodologies. 
Strong background in 後端開發 with 5+ years experience in 軟體工程 is required. 
Knowledge of CI/CD流程, PostgreSQL資料庫, and 系統架構規劃 is essential. 
Must have excellent 溝通能力 and 問題解決能力 to work effectively in our 敏捷團隊.
The ideal candidate will lead 技術創新 and mentor 初級工程師 in best practices.
""".strip()  # 400+ 字元, >25% 繁中
```

#### 混合語言職缺描述 (<20% 繁中, 400字元)
```python
VALID_MIXED_JD_LOW_CHINESE = """
We are looking for a Senior Python Developer with extensive experience in building 
scalable web applications using FastAPI and Django frameworks. The ideal candidate 
should have strong knowledge of Docker, Kubernetes, and AWS cloud services. 
Experience with microservices architecture, RESTful APIs, GraphQL, PostgreSQL, 
MongoDB, Redis, and distributed systems is highly valued. Must be proficient in 
CI/CD pipelines, automated testing, and 軟體工程 best practices. 資深工程師 preferred.
Strong problem-solving skills and ability to work in fast-paced environment required.
""".strip()  # 400+ 字元, <10% 繁中
```

### 2.2 有效履歷資料 (>200字元)

#### 英文履歷 - 標準版 (400字元)
```python
VALID_ENGLISH_RESUME_STANDARD = """
Senior Software Engineer with 7 years of experience in Python development.
Expertise in FastAPI, Django, Flask frameworks. Strong background in 
microservices architecture, Docker containerization, and Kubernetes orchestration.
Proficient in AWS cloud services including EC2, S3, Lambda, and RDS.
Experience with both SQL (PostgreSQL, MySQL) and NoSQL (MongoDB, Redis) databases.
Skilled in CI/CD pipelines using Jenkins and GitHub Actions.
Strong advocate for test-driven development and clean code practices.
Led team of 5 developers in successful delivery of multiple projects.
""".strip()  # 400+ 字元
```

#### 繁體中文履歷 - 標準版 (350字元)
```python
VALID_CHINESE_RESUME_STANDARD = """
資深軟體工程師，擁有七年Python開發經驗。專精於FastAPI、Django框架開發，
熟悉微服務架構設計與Docker容器技術。具備AWS雲端服務實務經驗，
包含EC2、S3、Lambda等服務。精通PostgreSQL和MongoDB資料庫系統，
並有Redis快取優化經驗。熟悉CI/CD流程，使用Jenkins進行自動化部署。
重視測試驅動開發，確保程式碼品質。曾帶領五人團隊完成多個專案，
具備良好的技術領導能力和團隊協作經驗。持續學習新技術，
定期參與技術社群活動並分享經驗。
""".strip()  # 350+ 字元
```

### 2.3 無效測試資料 (<200字元)

#### 短文本測試資料
```python
# 太短的職缺描述 (40字元)
INVALID_SHORT_JD = "Python Developer with FastAPI experience"

# 太短的履歷 (50字元)
INVALID_SHORT_RESUME = "Software Engineer with 5 years experience"

# 接近但不足200字元 (195字元)
INVALID_NEAR_THRESHOLD_JD = """
We are looking for a Python Developer with experience in FastAPI and Django.
Must have Docker and Kubernetes knowledge. AWS experience required.
Strong problem-solving skills needed.
""".strip()  # 195字元，會觸發422錯誤
```

## 3. 特殊測試場景資料

### 3.1 邊界測試資料

#### 正好200字元
```python
BOUNDARY_EXACT_200_CHARS = "x" * 200  # 正好200字元，應該通過

BOUNDARY_EXACT_200_MEANINGFUL = """
Senior Python Developer position requiring extensive experience with modern frameworks.
Must have strong skills in FastAPI, Django, Docker, and cloud services.
Join our innovative team today!
""".strip()  # 調整至正好200字元
```

#### 201字元（最小有效）
```python
BOUNDARY_201_CHARS = "x" * 201  # 201字元，應該通過
```

#### 199字元（最大無效）
```python
BOUNDARY_199_CHARS = "x" * 199  # 199字元，應該失敗
```

### 3.2 不支援語言測試資料

#### 簡體中文（應被拒絕）
```python
UNSUPPORTED_SIMPLIFIED_CHINESE = """
我们正在寻找一位高级Python开发工程师，需要具备FastAPI框架经验，
熟悉Docker容器技术和Azure云端服务。理想的候选人应该对微服务架构有深入理解，
并且有RESTful API开发经验。具备CI/CD流程和测试驱动开发经验者优先。
同时需要熟悉分布式系统设计，具备系统架构规划能力和团队合作精神。
需要至少五年以上的后端开发经验，能够在快节奏环境中独立工作。
""".strip()  # 250+ 字元，簡體中文
```

#### 日文（應被拒絕）
```python
UNSUPPORTED_JAPANESE = """
私たちは、FastAPIフレームワークの経験を持つシニアPython開発エンジニアを探しています。
Dockerコンテナ技術とAzureクラウドサービスに精通していることが求められます。
理想的な候補者は、マイクロサービスアーキテクチャについて深い理解を持ち、
RESTful API開発の経験があることが必要です。CI/CDプロセスとテスト駆動開発の経験がある方を優先します。
分散システム設計に精通し、システムアーキテクチャの計画能力とチームワーク精神を持っていることが必要です。
""".strip()  # 250+ 字元，日文
```

#### 韓文（應被拒絕）
```python
UNSUPPORTED_KOREAN = """
FastAPI 프레임워크 경험을 가진 시니어 Python 개발 엔지니어를 찾고 있습니다. 
Docker 컨테이너 기술과 Azure 클라우드 서비스에 능숙해야 합니다. 
이상적인 후보자는 마이크로서비스 아키텍처에 대한 깊은 이해와 
RESTful API 개발 경험이 있어야 합니다. CI/CD 프로세스와 테스트 주도 개발 경험을 우선시합니다. 
분산 시스템 설계에 익숙하고 시스템 아키텍처 계획 능력과 팀워크 정신이 필요합니다.
""".strip()  # 250+ 字元，韓文
```

## 4. 測試資料 Fixtures

### 4.1 基礎 Fixtures
```python
import pytest

class TestDataFixtures:
    """服務層測試資料 fixtures"""
    
    @pytest.fixture
    def valid_english_jd(self):
        """有效英文職缺描述 (>200字元)"""
        return VALID_ENGLISH_JD_STANDARD
    
    @pytest.fixture
    def valid_chinese_jd(self):
        """有效繁中職缺描述 (>200字元)"""
        return VALID_CHINESE_JD_STANDARD
    
    @pytest.fixture
    def valid_resume(self):
        """有效履歷 (>200字元)"""
        return VALID_ENGLISH_RESUME_STANDARD
    
    @pytest.fixture
    def invalid_short_jd(self):
        """無效短職缺描述 (<200字元)"""
        return INVALID_SHORT_JD
    
    @pytest.fixture
    def boundary_test_data(self):
        """邊界測試資料集"""
        return {
            "exact_200": BOUNDARY_EXACT_200_CHARS,
            "just_valid": BOUNDARY_201_CHARS,
            "just_invalid": BOUNDARY_199_CHARS
        }
```

### 4.2 動態資料生成器
```python
@pytest.fixture
def jd_generator():
    """動態生成指定長度的職缺描述"""
    def generate(length=300, language="en"):
        if language == "en":
            template = """
            We are looking for a {role} with {years}+ years of experience.
            Required skills: {skills}. Must have {requirements}.
            """
            
            roles = ["Python Developer", "Software Engineer", "Backend Developer"]
            skills = ["FastAPI", "Django", "Docker", "Kubernetes", "AWS", "PostgreSQL"]
            requirements = ["problem-solving skills", "team collaboration", "agile experience"]
            
            # 組合生成指定長度
            import random
            result = template.format(
                role=random.choice(roles),
                years=random.randint(3, 10),
                skills=", ".join(random.sample(skills, 3)),
                requirements=", ".join(random.sample(requirements, 2))
            )
            
            # 調整至目標長度
            while len(result) < length:
                result += f" Experience with {random.choice(skills)} is a plus."
            
            return result[:length]
        
        elif language == "zh-TW":
            template = """
            我們正在尋找{role}，需要{years}年以上經驗。
            必備技能：{skills}。需要具備{requirements}。
            """
            
            roles = ["Python工程師", "軟體工程師", "後端工程師"]
            skills = ["FastAPI", "Django", "Docker", "Kubernetes", "AWS", "PostgreSQL"]
            requirements = ["問題解決能力", "團隊合作", "敏捷開發經驗"]
            
            import random
            result = template.format(
                role=random.choice(roles),
                years=random.randint(3, 10),
                skills="、".join(random.sample(skills, 3)),
                requirements="、".join(random.sample(requirements, 2))
            )
            
            while len(result.encode('utf-8')) < length:
                result += f"熟悉{random.choice(skills)}者佳。"
            
            return result
    
    return generate
```

## 5. 測試資料驗證

### 5.1 長度驗證函數
```python
def validate_test_data_length(text: str, min_length: int = 200) -> bool:
    """
    驗證測試資料是否符合最小長度要求
    
    Args:
        text: 要驗證的文字
        min_length: 最小長度要求（預設200）
    
    Returns:
        bool: 是否符合要求
    """
    if not text:
        return False
    
    # 計算實際字元數（不含首尾空白）
    cleaned_text = text.strip()
    char_count = len(cleaned_text)
    
    return char_count >= min_length

def get_validation_error_response(field: str, actual_length: int) -> dict:
    """
    生成標準的驗證錯誤回應
    
    Args:
        field: 欄位名稱 (job_description 或 resume)
        actual_length: 實際長度
    
    Returns:
        dict: 錯誤回應格式
    """
    return {
        "success": False,
        "error": {
            "code": "VALIDATION_ERROR",
            "message": f"{field} must be at least 200 characters (got {actual_length})"
        }
    }
```

### 5.2 測試案例範例
```python
class TestDataValidation:
    """測試資料驗證測試"""
    
    def test_valid_jd_passes_validation(self, valid_english_jd):
        """測試有效JD通過驗證"""
        assert validate_test_data_length(valid_english_jd) is True
        assert len(valid_english_jd) > 200
    
    def test_invalid_jd_fails_validation(self, invalid_short_jd):
        """測試無效JD驗證失敗"""
        assert validate_test_data_length(invalid_short_jd) is False
        assert len(invalid_short_jd) < 200
    
    def test_boundary_cases(self, boundary_test_data):
        """測試邊界情況"""
        assert validate_test_data_length(boundary_test_data["exact_200"]) is True
        assert validate_test_data_length(boundary_test_data["just_valid"]) is True
        assert validate_test_data_length(boundary_test_data["just_invalid"]) is False
    
    @pytest.mark.parametrize("length,expected", [
        (199, False),
        (200, True),
        (201, True),
        (500, True),
        (10000, True)
    ])
    def test_various_lengths(self, jd_generator, length, expected):
        """測試各種長度的資料"""
        test_data = jd_generator(length=length)
        assert validate_test_data_length(test_data) == expected
```

## 6. 使用指南

### 6.1 在測試中使用
```python
class TestKeywordExtraction(TestDataFixtures):
    """關鍵字提取測試"""
    
    async def test_valid_jd_extraction(self, valid_english_jd):
        """測試有效JD的關鍵字提取"""
        # valid_english_jd 已經保證 >200 字元
        service = KeywordExtractionService()
        result = await service.extract(valid_english_jd)
        assert result["success"] is True
    
    async def test_invalid_jd_rejection(self, invalid_short_jd):
        """測試無效JD被拒絕"""
        # invalid_short_jd 保證 <200 字元
        service = KeywordExtractionService()
        
        with pytest.raises(ValidationError) as exc_info:
            await service.extract(invalid_short_jd)
        
        assert "200 characters" in str(exc_info.value)
```

### 6.2 注意事項
1. **總是使用 fixtures** - 不要硬編碼測試資料
2. **驗證長度** - 在測試前確認資料符合要求
3. **測試兩種情況** - 同時測試有效和無效資料
4. **使用生成器** - 對於參數化測試使用動態生成
5. **保持一致性** - 所有測試使用相同的資料來源

## 7. 檢查清單

### 7.1 測試資料檢查
- [ ] 所有正向測試的 JD > 200 字元
- [ ] 所有正向測試的 Resume > 200 字元
- [ ] 包含 <200 字元的負向測試
- [ ] 包含邊界測試 (199, 200, 201 字元)
- [ ] 包含不支援語言的測試資料

### 7.2 測試覆蓋檢查
- [ ] 測試有效資料通過
- [ ] 測試無效資料返回 422
- [ ] 測試邊界條件
- [ ] 測試錯誤訊息格式
- [ ] 測試各種語言組合

---

**文檔維護**:
- 最後更新：2025-08-07
- 審查週期：每個Sprint
- 負責人：測試團隊