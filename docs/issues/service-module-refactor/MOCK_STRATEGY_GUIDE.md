# Mock 策略指南

## 文檔資訊
- **版本**: 1.0.0
- **建立日期**: 2025-08-07
- **維護者**: 測試團隊
- **參考範例**: `test/integration/test_keyword_extraction_language.py`

## 1. Mock 策略總覽

### 1.1 核心原則
1. **完全隔離** - 所有外部依賴必須被 Mock
2. **一致性** - 使用統一的 Mock 模式和命名規範
3. **可維護性** - Mock 設定集中管理在 fixtures 中
4. **真實性** - Mock 回應應模擬真實 API 的結構

### 1.2 Mock 範圍
| 依賴類型 | Mock 方法 | 範例 |
|---------|----------|------|
| Azure OpenAI API | AsyncMock | `mock_azure_openai_client` |
| LLM Factory | patch + Mock | `mock_llm_factory` |
| 檔案系統 | tmp_path + Mock | `mock_prompt_files` |
| 網路請求 | AsyncMock | `mock_http_client` |
| 資料庫 | Mock | `mock_db_connection` |
| 監控服務 | Mock | `mock_monitoring_service` |

## 2. 標準 Mock Fixtures

### 2.1 Azure OpenAI Client Mock
```python
import pytest
from unittest.mock import Mock, AsyncMock, patch

@pytest.fixture
def mock_azure_openai_client():
    """
    Mock Azure OpenAI client for service tests.
    完整模擬 Azure OpenAI SDK 的結構。
    """
    client = Mock()
    
    # Chat completions 結構
    client.chat = Mock()
    client.chat.completions = Mock()
    
    # 模擬成功的回應
    client.chat.completions.create = AsyncMock(
        return_value=Mock(
            id="chatcmpl-test",
            object="chat.completion",
            created=1234567890,
            model="gpt-4",
            choices=[
                Mock(
                    index=0,
                    message=Mock(
                        role="assistant",
                        content='{"keywords": ["Python", "FastAPI", "Docker", "Azure", "Microservices"]}'
                    ),
                    finish_reason="stop"
                )
            ],
            usage=Mock(
                prompt_tokens=150,
                completion_tokens=50,
                total_tokens=200
            )
        )
    )
    
    # 模擬錯誤情況的方法
    client.chat.completions.create_with_error = AsyncMock(
        side_effect=Exception("Azure OpenAI API Error")
    )
    
    return client
```

### 2.2 LLM Factory Mock
```python
@pytest.fixture
def mock_llm_factory():
    """
    Mock LLM Factory for dynamic model selection.
    模擬 get_llm_client 和相關功能。
    """
    with patch('src.services.llm_factory.get_llm_client') as mock_get_client, \
         patch('src.services.llm_factory.get_llm_client_smart') as mock_get_smart, \
         patch('src.services.llm_factory.get_llm_info') as mock_get_info:
        
        # 設定預設返回值
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_get_smart.return_value = mock_client
        mock_get_info.return_value = {
            'model': 'gpt-4.1-mini',
            'region': 'japaneast',
            'deployment': 'gpt-41-mini-japaneast'
        }
        
        yield {
            'get_client': mock_get_client,
            'get_smart': mock_get_smart,
            'get_info': mock_get_info,
            'client': mock_client
        }
```

### 2.3 檔案系統 Mock
```python
@pytest.fixture
def mock_prompt_files(tmp_path):
    """
    Mock prompt YAML files for testing.
    使用 pytest 的 tmp_path 建立臨時檔案結構。
    """
    # 建立目錄結構
    prompts_dir = tmp_path / "prompts" / "keyword_extraction"
    prompts_dir.mkdir(parents=True)
    
    # 建立英文 prompt 檔案
    en_prompt = prompts_dir / "v1.4.0-en.yaml"
    en_prompt.write_text("""
version: 1.4.0
language: en
status: active
metadata:
  created_at: "2024-01-01"
  author: "Test Team"
system_prompt: |
  You are a keyword extraction expert.
  Extract relevant keywords from job descriptions.
user_prompt: |
  Extract keywords from the following job description:
  {job_description}
  
  Return as JSON list.
llm_config:
  temperature: 0.3
  max_tokens: 500
  top_p: 0.9
  frequency_penalty: 0.0
  presence_penalty: 0.0
    """)
    
    # 建立繁中 prompt 檔案
    zh_prompt = prompts_dir / "v1.4.0-zh-TW.yaml"
    zh_prompt.write_text("""
version: 1.4.0
language: zh-TW
status: active
metadata:
  created_at: "2024-01-01"
  author: "測試團隊"
system_prompt: |
  您是關鍵字提取專家。
  從職缺描述中提取相關關鍵字。
user_prompt: |
  從以下職缺描述提取關鍵字：
  {job_description}
  
  以JSON列表格式返回。
llm_config:
  temperature: 0.3
  max_tokens: 500
  top_p: 0.9
  frequency_penalty: 0.0
  presence_penalty: 0.0
    """)
    
    return prompts_dir
```

### 2.4 服務層 Mock
```python
@pytest.fixture
def mock_keyword_service():
    """
    Mock KeywordExtractionService for integration tests.
    模擬完整的服務介面。
    """
    service = AsyncMock()
    
    # 基本方法
    service.validate_input = AsyncMock()
    service.process = AsyncMock()
    service.close = AsyncMock()
    
    # 設定預設返回值
    service.process.return_value = {
        "keywords": ["Python", "FastAPI", "Docker", "Azure", "Microservices"],
        "keyword_count": 5,
        "confidence_score": 0.88,
        "extraction_method": "2_round_intersection",
        "detected_language": "en",
        "prompt_version_used": "v1.4.0-en",
        "processing_time_ms": 2400.0
    }
    
    # 錯誤處理
    service.process_with_error = AsyncMock(
        side_effect=UnsupportedLanguageError(
            detected_language="zh-CN",
            supported_languages=["en", "zh-TW"],
            confidence=0.95
        )
    )
    
    return service
```

## 3. Mock 使用模式

### 3.1 單元測試模式
```python
class TestLanguageDetectionService:
    """語言檢測服務單元測試"""
    
    @pytest.fixture(autouse=True)
    def setup_mocks(self, mock_llm_factory):
        """自動應用所有必要的 mocks"""
        self.llm_factory = mock_llm_factory
    
    @pytest.mark.asyncio
    async def test_detect_language_english(self, valid_english_jd):
        """測試英文檢測"""
        from src.services.language_detection.simple_language_detector import SimplifiedLanguageDetector
        
        detector = SimplifiedLanguageDetector()
        result = await detector.detect_language(valid_english_jd)
        
        assert result.language == "en"
        assert result.confidence > 0.9
```

### 3.2 整合測試模式
```python
class TestKeywordExtractionIntegration:
    """關鍵字提取整合測試"""
    
    def test_api_endpoint_with_mocks(
        self, 
        test_client,
        mock_keyword_service,
        mock_llm_factory,
        valid_english_jd_request
    ):
        """測試 API 端點與服務整合"""
        # 設定 mock 行為
        mock_keyword_service.validate_input.return_value = valid_english_jd_request
        mock_keyword_service.process.return_value = {
            "keywords": ["Python", "FastAPI"],
            "detected_language": "en"
        }
        
        # Patch 服務
        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2',
                  return_value=mock_keyword_service):
            response = test_client.post(
                "/api/v1/extract-jd-keywords",
                json=valid_english_jd_request
            )
        
        assert response.status_code == 200
        assert response.json()["success"] is True
```

## 4. Mock 資料生成

### 4.1 測試資料 Fixtures
```python
@pytest.fixture
def valid_test_data():
    """
    生成符合 API 要求的測試資料 (>200字元)
    """
    return {
        "english_jd": """
        We are looking for a Senior Python Developer with 5+ years of experience 
        in building scalable web applications using FastAPI and Django frameworks. 
        Strong knowledge of Docker, Kubernetes, and AWS cloud services is required. 
        The ideal candidate must have excellent problem-solving skills and ability 
        to work independently in a fast-paced agile environment.
        """.strip(),  # 約 350 字元
        
        "chinese_jd": """
        我們正在尋找一位資深的Python開發工程師，需要具備FastAPI框架經驗，
        熟悉Docker容器技術和Azure雲端服務。理想的候選人應該對微服務架構有深入理解，
        並且有RESTful API開發經驗。需要至少五年以上的後端開發經驗。
        """.strip(),  # 約 250 字元
        
        "invalid_short": "Python Developer",  # < 200 字元
    }
```

### 4.2 動態資料生成
```python
@pytest.fixture
def generate_test_jd():
    """動態生成測試職缺描述"""
    def _generate(language="en", length=300):
        if language == "en":
            base = "Looking for experienced developer. "
            skills = ["Python", "FastAPI", "Docker", "Azure", "Kubernetes", "PostgreSQL"]
            requirements = [
                "5+ years experience required.",
                "Strong problem-solving skills.",
                "Excellent communication abilities.",
                "Team collaboration essential."
            ]
            
            # 組合至指定長度
            jd = base
            while len(jd) < length:
                jd += f"Must have {random.choice(skills)} experience. "
                jd += random.choice(requirements) + " "
            
            return jd[:length]
        
        elif language == "zh-TW":
            base = "尋找資深開發工程師。"
            skills = ["Python", "FastAPI", "Docker", "Azure", "微服務", "資料庫"]
            requirements = [
                "需要五年以上經驗。",
                "具備問題解決能力。",
                "良好溝通協調能力。",
                "團隊合作精神。"
            ]
            
            jd = base
            while len(jd.encode('utf-8')) < length:
                jd += f"需要{random.choice(skills)}經驗。"
                jd += random.choice(requirements)
            
            return jd
    
    return _generate
```

## 5. Mock 錯誤場景

### 5.1 網路錯誤模擬
```python
@pytest.fixture
def mock_network_errors():
    """模擬各種網路錯誤"""
    return {
        "timeout": asyncio.TimeoutError("Request timeout"),
        "connection": ConnectionError("Connection refused"),
        "rate_limit": Exception("Rate limit exceeded"),
        "server_error": Exception("500 Internal Server Error")
    }

@pytest.mark.asyncio
async def test_handle_timeout(mock_azure_openai_client, mock_network_errors):
    """測試超時處理"""
    mock_azure_openai_client.chat.completions.create.side_effect = \
        mock_network_errors["timeout"]
    
    service = KeywordExtractionService(mock_azure_openai_client)
    
    with pytest.raises(asyncio.TimeoutError):
        await service.process({"job_description": "test"})
```

### 5.2 API 錯誤模擬
```python
@pytest.fixture
def mock_api_errors():
    """模擬 API 錯誤回應"""
    return {
        "validation_error": {
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Job description must be at least 200 characters"
            }
        },
        "unsupported_language": {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_LANGUAGE",
                "message": "Detected language 'zh-CN' is not supported"
            }
        },
        "rate_limit": {
            "success": False,
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "API rate limit exceeded"
            }
        }
    }
```

## 6. Mock 最佳實踐

### 6.1 DO's ✅
1. **使用 fixtures 管理 mocks** - 提高重用性和維護性
2. **Mock 在最外層** - 避免深層 patch
3. **驗證 mock 調用** - 使用 `assert_called_with` 等方法
4. **提供真實的資料結構** - Mock 回應應符合真實 API
5. **測試錯誤路徑** - 包含各種錯誤場景

### 6.2 DON'Ts ❌
1. **避免過度 mock** - 保持適當的測試真實性
2. **不要 mock 被測試的程式碼** - 只 mock 外部依賴
3. **避免複雜的 mock 鏈** - 保持簡單直接
4. **不要忽略 mock 清理** - 使用 context manager 或 fixture
5. **避免硬編碼 mock 資料** - 使用 fixtures 和生成器

## 7. Mock 驗證

### 7.1 調用驗證
```python
def test_service_calls_llm_correctly(mock_azure_openai_client):
    """驗證服務正確調用 LLM"""
    service = KeywordExtractionService(mock_azure_openai_client)
    
    # 執行測試
    result = await service.process({"job_description": "test"})
    
    # 驗證調用
    mock_azure_openai_client.chat.completions.create.assert_called_once()
    
    # 驗證參數
    call_args = mock_azure_openai_client.chat.completions.create.call_args
    assert call_args.kwargs["temperature"] == 0.3
    assert call_args.kwargs["max_tokens"] == 500
```

### 7.2 多次調用驗證
```python
def test_retry_mechanism(mock_azure_openai_client):
    """驗證重試機制"""
    # 第一次失敗，第二次成功
    mock_azure_openai_client.chat.completions.create.side_effect = [
        Exception("Temporary error"),
        Mock(choices=[Mock(message=Mock(content="success"))])
    ]
    
    service = KeywordExtractionService(mock_azure_openai_client)
    result = await service.process_with_retry({"job_description": "test"})
    
    # 驗證調用了兩次
    assert mock_azure_openai_client.chat.completions.create.call_count == 2
```

## 8. 疑難排解

### 8.1 常見問題

| 問題 | 原因 | 解決方案 |
|------|------|---------|
| Mock 未生效 | Patch 路徑錯誤 | 使用完整的模組路徑 |
| AsyncMock 錯誤 | 異步調用問題 | 確保使用 AsyncMock 而非 Mock |
| 資料不一致 | Mock 狀態污染 | 使用 fixture scope 控制 |
| 測試不穩定 | Mock 設定不完整 | 完整模擬所有必要屬性 |

### 8.2 除錯技巧
```python
# 1. 列印 mock 調用記錄
print(mock_object.mock_calls)

# 2. 檢查 mock 配置
print(mock_object._mock_methods)

# 3. 使用 spec 參數確保介面一致
mock = Mock(spec=RealClass)

# 4. 啟用自動 spec
with patch('module.Class', autospec=True) as mock:
    pass
```

## 9. 參考資源

- [pytest-mock 文檔](https://pytest-mock.readthedocs.io/)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- 專案範例：`test/integration/test_keyword_extraction_language.py`

---

**文檔維護**:
- 最後更新：2025-08-07
- 審查週期：每個Sprint
- 負責人：測試團隊