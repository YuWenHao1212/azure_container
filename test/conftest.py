"""
Pytest configuration for unit tests.
"""

import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))

# Set test environment variables before any imports
os.environ['TESTING'] = 'true'
os.environ['MONITORING_ENABLED'] = 'false'
os.environ['LIGHTWEIGHT_MONITORING'] = 'false'
os.environ['ERROR_CAPTURE_ENABLED'] = 'false'
os.environ['AZURE_OPENAI_ENDPOINT'] = 'https://test.openai.azure.com'
os.environ['AZURE_OPENAI_API_KEY'] = 'test-key'
os.environ['LLM2_ENDPOINT'] = 'https://test.openai.azure.com'
os.environ['LLM2_DEPLOYMENT'] = 'test-deployment'
os.environ['LLM2_API_KEY'] = 'test-key'
os.environ['GPT41_MINI_JAPANEAST_ENDPOINT'] = 'https://test.openai.azure.com'
os.environ['GPT41_MINI_JAPANEAST_API_KEY'] = 'test-key'
os.environ['GPT41_MINI_JAPANEAST_DEPLOYMENT'] = 'test-deployment'
os.environ['EMBEDDING_ENDPOINT'] = 'https://test.embedding.com'
os.environ['EMBEDDING_API_KEY'] = 'test-key'
os.environ['JWT_SECRET_KEY'] = 'test-secret'

# Configure pytest-asyncio
pytest_plugins = ['pytest_asyncio']

@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for asyncio tests."""
    import asyncio
    return asyncio.get_event_loop_policy()

@pytest.fixture
def mock_monitoring_service():
    """Mock monitoring service for all tests."""
    service = Mock()
    service.track_event = Mock()
    service.track_error = Mock()
    service.track_metric = Mock()
    return service

@pytest.fixture(autouse=True)
def mock_openai_clients():
    """Automatically mock all Azure OpenAI clients for all tests."""
    # Skip mocking for E2E tests
    if os.environ.get('PYTEST_CURRENT_TEST_TYPE') == 'e2e':
        yield
        return
    # Mock all possible OpenAI client imports and services
    with (
        # Core OpenAI clients
        patch('src.services.openai_client.get_azure_openai_client') as mock_openai,
        patch('src.services.openai_client_gpt41.get_gpt41_mini_client') as mock_gpt41,
        patch('src.services.embedding_client.get_azure_embedding_client') as mock_embedding,

        # Service-level mocks
        patch('src.services.keyword_extraction.get_keyword_extraction_service') as mock_keyword_service,

        # LLM Factory for Gap Analysis V2
        patch('src.services.llm_factory.get_llm_client') as mock_llm_factory,

        # Resource pool manager
        patch('src.services.resource_pool_manager.ResourcePoolManager') as mock_resource_pool,

        # HTTP clients that might bypass mocks
        patch('httpx.AsyncClient') as mock_httpx,
        patch('aiohttp.ClientSession') as mock_aiohttp
    ):
        # Configure OpenAI client mock
        mock_openai_instance = AsyncMock()
        mock_openai_instance.chat_completion = AsyncMock(return_value={
            "choices": [{
                "message": {
                    "content": '{"CoreStrengths": "<ol><li>Test strength</li></ol>", "KeyGaps": "<ol><li>Test gap</li></ol>", "QuickImprovements": "<ol><li>Test improvement</li></ol>", "OverallAssessment": "<p>Test assessment</p>", "SkillSearchQueries": ["Python", "Docker"]}'
                }
            }],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        })
        mock_openai_instance.close = AsyncMock()
        mock_openai.return_value = mock_openai_instance

        # Configure GPT-4.1 mini client mock
        mock_gpt41_instance = AsyncMock()
        mock_gpt41_instance.chat_completion = AsyncMock(return_value={
            "choices": [{
                "message": {
                    "content": '{"keywords": ["Python", "FastAPI", "Docker"], "keyword_count": 3, "confidence_score": 0.9, "extraction_method": "llm_based", "processing_time_ms": 250}'
                }
            }],
            "usage": {"prompt_tokens": 80, "completion_tokens": 30, "total_tokens": 110}
        })
        mock_gpt41_instance.close = AsyncMock()
        mock_gpt41.return_value = mock_gpt41_instance

        # Configure embedding client mock
        mock_embedding_instance = AsyncMock()
        mock_embedding_instance.create_embeddings = AsyncMock(return_value=[[0.1] * 1536, [0.2] * 1536])
        mock_embedding_instance.close = AsyncMock()
        mock_embedding.return_value = mock_embedding_instance

        # Configure keyword extraction service mock
        mock_keyword_instance = AsyncMock()
        mock_keyword_instance.validate_input = AsyncMock(return_value={
            "job_description": "test job description with sufficient length to pass validation requirements for testing purposes",
            "max_keywords": 15
        })
        mock_keyword_instance.process = AsyncMock(return_value={
            "keywords": ["Python", "FastAPI", "Docker", "AWS", "Git"],
            "keyword_count": 5,
            "confidence_score": 0.85,
            "extraction_method": "llm_based",
            "processing_time_ms": 200
        })
        mock_keyword_instance.close = AsyncMock()
        mock_keyword_service.return_value = mock_keyword_instance

        # Configure LLM Factory mock for Gap Analysis V2
        mock_llm_client = AsyncMock()
        mock_llm_client.chat_completion = AsyncMock(return_value={
            "choices": [{
                "message": {
                    "content": '{"CoreStrengths": "<ol><li>Strong technical skills</li></ol>", "KeyGaps": "<ol><li>Limited cloud experience</li></ol>", "QuickImprovements": "<ol><li>Get AWS certification</li></ol>", "OverallAssessment": "<p>Good technical foundation with room for cloud skills improvement.</p>", "SkillSearchQueries": ["AWS", "Cloud Computing"]}'
                }
            }],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        })
        mock_llm_client.close = AsyncMock()
        mock_llm_factory.return_value = mock_llm_client

        # Configure resource pool manager mock
        mock_pool_instance = Mock()
        mock_pool_instance.get_client = Mock()
        mock_pool_instance.get_client.__enter__ = Mock(return_value=mock_openai_instance)
        mock_pool_instance.get_client.__exit__ = Mock(return_value=None)
        mock_pool_instance.get_stats = Mock(return_value={
            "clients_created": 1,
            "clients_reused": 0,
            "current_pool_size": 1
        })
        mock_resource_pool.return_value = mock_pool_instance

        # Configure HTTP client mocks to prevent any real network calls
        mock_httpx_instance = Mock()
        mock_httpx_instance.post = Mock(side_effect=Exception("HTTP calls should be mocked"))
        mock_httpx_instance.close = Mock()
        mock_httpx.return_value = mock_httpx_instance

        mock_aiohttp_instance = Mock()
        mock_aiohttp_instance.post = Mock(side_effect=Exception("HTTP calls should be mocked"))
        mock_aiohttp_instance.close = Mock()
        mock_aiohttp.return_value = mock_aiohttp_instance

        # Azure OpenAI direct mock removed to avoid importing openai module

        yield


# ==================== SHARED TEST DATA FIXTURES ====================
# These fixtures provide common test data used across multiple test files

@pytest.fixture
def sample_english_jd():
    """Standard English job description for testing (>200 chars)."""
    return (
        "We are looking for a Senior Python Developer with experience in FastAPI, "
        "Docker, and Azure cloud services. The ideal candidate should have strong "
        "knowledge of microservices architecture and RESTful APIs. Experience with "
        "CI/CD pipelines and test-driven development is highly desired. Must have "
        "5+ years of experience in backend development and distributed systems."
    )

@pytest.fixture
def sample_chinese_jd():
    """Standard Traditional Chinese job description for testing (>200 chars)."""
    return (
        "我們正在尋找一位資深的Python開發工程師，需要具備FastAPI框架經驗，"
        "熟悉Docker容器技術和Azure雲端服務。理想的候選人應該對微服務架構有深入理解，"
        "並且有RESTful API開發經驗。具備CI/CD流程和測試驅動開發經驗者優先。"
        "同時需要熟悉分散式系統設計，具備系統架構規劃能力和團隊合作精神。"
        "需要至少五年以上的後端開發經驗，能夠在快節奏環境中獨立工作。"
        "此外還需要具備良好的問題解決能力、優秀的溝通技巧，以及持續學習新技術的熱忱。"
    )

@pytest.fixture
def sample_mixed_jd():
    """Mixed language job description with Chinese and English."""
    return (
        "We are seeking a 資深Python開發工程師 with expertise in 微服務架構 and 雲端服務. "
        "The candidate should have experience with FastAPI框架, Docker容器技術, and Azure服務. "
        "Must be skilled in 分散式系統設計 and 測試驅動開發 methodologies. "
        "Strong background in 後端開發 with 5+ years experience in 軟體工程 is required."
    )

@pytest.fixture
def sample_short_jd():
    """Job description that is too short (<200 chars) for validation testing."""
    return "This job description is too short and under 200 characters limit."

@pytest.fixture
def sample_long_jd():
    """Very long job description for performance testing."""
    base = (
        "Senior Python Developer position with extensive experience required. "
        "Must have strong technical skills and leadership abilities. "
    )
    return base * 50  # Creates a very long text

@pytest.fixture
def sample_html_resume():
    """Sample HTML resume for testing."""
    return """
    <html>
    <body>
        <h1>John Doe</h1>
        <h2>Senior Software Engineer</h2>
        <section>
            <h3>Skills</h3>
            <ul>
                <li>Python (5+ years)</li>
                <li>FastAPI, Django</li>
                <li>Docker, Kubernetes</li>
                <li>Azure, AWS</li>
                <li>Microservices Architecture</li>
                <li>RESTful APIs</li>
                <li>CI/CD Pipelines</li>
            </ul>
        </section>
        <section>
            <h3>Experience</h3>
            <p>Senior Python Developer at Tech Corp (2020-Present)</p>
            <ul>
                <li>Developed scalable microservices using FastAPI</li>
                <li>Implemented CI/CD pipelines with Azure DevOps</li>
                <li>Led team of 5 developers</li>
            </ul>
        </section>
    </body>
    </html>
    """.strip()

@pytest.fixture
def sample_text_resume():
    """Sample plain text resume for testing."""
    return """
    John Doe
    Senior Software Engineer

    Skills:
    - Python (5+ years)
    - FastAPI, Django
    - Docker, Kubernetes
    - Azure, AWS
    - Microservices Architecture
    - RESTful APIs
    - CI/CD Pipelines

    Experience:
    Senior Python Developer at Tech Corp (2020-Present)
    - Developed scalable microservices using FastAPI
    - Implemented CI/CD pipelines with Azure DevOps
    - Led team of 5 developers
    """.strip()

@pytest.fixture
def sample_keywords():
    """Sample keyword list for testing."""
    return [
        "Python", "FastAPI", "Docker", "Kubernetes", "Azure",
        "Microservices", "RESTful APIs", "CI/CD", "Backend Development",
        "Distributed Systems", "Test-Driven Development", "Agile"
    ]

@pytest.fixture
def expected_extraction_result():
    """Expected keyword extraction result structure."""
    return {
        "keywords": [
            "Python", "Senior Developer", "FastAPI", "Docker", "Azure",
            "Microservices", "RESTful APIs", "CI/CD", "Backend Development"
        ],
        "keyword_count": 9,
        "confidence_score": 0.85,
        "extraction_method": "llm_extraction",
        "detected_language": "en",
        "prompt_version_used": "v1.4.0-en",
        "processing_time_ms": 2500.0
    }
