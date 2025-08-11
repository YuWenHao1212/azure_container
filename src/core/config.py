"""
Core configuration module for Azure FastAPI application.
Following FHS architecture principles.
"""

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application settings
    app_name: str = "Azure FastAPI Resume API"
    app_version: str = "1.0.0"
    debug: bool = False

    # API settings
    api_v1_prefix: str = "/api/v1"

    # LLM settings for keyword extraction
    llm_temperature: float = 0.0
    llm_max_tokens: int = 1000
    llm_seed_round1: int = 42
    llm_seed_round2: int = 43

    # Embedding settings (for general embeddings)
    embedding_endpoint: str = Field(
        default="https://wenha-m7qan2zj-swedencentral.cognitiveservices.azure.com/openai/deployments/text-embedding-3-large/embeddings?api-version=2023-05-15",
        validation_alias=AliasChoices("EMBEDDING_ENDPOINT", "AZURE_OPENAI_EMBEDDING_ENDPOINT"),
        description="Embedding endpoint - supports both EMBEDDING_ENDPOINT and AZURE_OPENAI_EMBEDDING_ENDPOINT"
    )
    embedding_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("EMBEDDING_API_KEY", "AZURE_OPENAI_EMBEDDING_API_KEY"),
        description="Embedding API key - supports both EMBEDDING_API_KEY and AZURE_OPENAI_EMBEDDING_API_KEY"
    )
    embedding_model: str = "text-embedding-3-large"

    # Course embedding settings (for course search)
    course_embedding_endpoint: str = Field(
        default="https://ai-azureai700705952086.cognitiveservices.azure.com/openai/deployments/text-embedding-3-small/embeddings?api-version=2023-05-15",
        validation_alias=AliasChoices("COURSE_EMBEDDING_ENDPOINT", "AZURE_OPENAI_COURSE_EMBEDDING_ENDPOINT"),
        description=(
            "Course embedding endpoint - supports both COURSE_EMBEDDING_ENDPOINT "
            "and AZURE_OPENAI_COURSE_EMBEDDING_ENDPOINT"
        )
    )
    course_embedding_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("COURSE_EMBEDDING_API_KEY", "AZURE_OPENAI_COURSE_EMBEDDING_API_KEY"),
        description=(
            "Course embedding API key - supports both COURSE_EMBEDDING_API_KEY "
            "and AZURE_OPENAI_COURSE_EMBEDDING_API_KEY"
        )
    )
    course_embedding_model: str = "text-embedding-3-small"

    # Azure OpenAI settings (for GPT-4o-2 model)
    azure_openai_endpoint: str = Field(
        default="https://test.openai.azure.com",
        validation_alias=AliasChoices("AZURE_OPENAI_ENDPOINT", "LLM2_ENDPOINT"),
        description="Azure OpenAI endpoint - supports both AZURE_OPENAI_ENDPOINT and LLM2_ENDPOINT"
    )
    azure_openai_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("AZURE_OPENAI_API_KEY", "LLM2_API_KEY"),
        description="Azure OpenAI API key - supports both AZURE_OPENAI_API_KEY and LLM2_API_KEY"
    )

    # Similarity calculation settings
    sigmoid_x0: float = 0.373
    sigmoid_k: float = 15.0
    keyword_match_case_sensitive: bool = False
    enable_plural_matching: bool = True

    # Gap Analysis settings
    gap_analysis_temperature: float = 0.7
    gap_analysis_max_tokens: int = 2000

    # GPT-4.1 mini Japan East Configuration (High Performance)
    gpt41_mini_japaneast_endpoint: str = Field(
        default="https://airesumeadvisor.openai.azure.com/",
        validation_alias="GPT41_MINI_JAPANEAST_ENDPOINT",
        description="GPT-4.1 mini Japan East endpoint for optimized performance"
    )
    gpt41_mini_japaneast_api_key: str = Field(
        default="",
        validation_alias="GPT41_MINI_JAPANEAST_API_KEY",
        description="GPT-4.1 mini Japan East API key"
    )
    gpt41_mini_japaneast_deployment: str = Field(
        default="gpt-4-1-mini-japaneast",
        validation_alias="GPT41_MINI_JAPANEAST_DEPLOYMENT",
        description="GPT-4.1 mini Japan East deployment name"
    )
    gpt41_mini_japaneast_api_version: str = Field(
        default="2025-01-01-preview",
        validation_alias="GPT41_MINI_JAPANEAST_API_VERSION",
        description="GPT-4.1 mini Japan East API version"
    )

    # Feature flags for model selection
    use_gpt41_mini_for_keywords: bool = Field(
        default=True,
        description="Use GPT-4.1 mini Japan East for keyword extraction (better performance)"
    )

    # LLM Model Selection Configuration (NEW)
    llm_model_default: str = Field(
        default="gpt-4.1",
        description="Default LLM model to use when not specified"
    )
    llm_model_keywords: str = Field(
        default="",
        validation_alias="LLM_MODEL_KEYWORDS",
        description="LLM model for keyword extraction API (gpt-4.1 or gpt-4.1-mini)"
    )
    llm_model_gap_analysis: str = Field(
        default="",
        validation_alias="LLM_MODEL_GAP_ANALYSIS",
        description="LLM model for gap analysis API (gpt-4.1 or gpt-4.1-mini)"
    )
    llm_model_resume_format: str = Field(
        default="",
        validation_alias="LLM_MODEL_RESUME_FORMAT",
        description="LLM model for resume format API (gpt-4.1 or gpt-4.1-mini)"
    )
    llm_model_resume_tailor: str = Field(
        default="",
        validation_alias="LLM_MODEL_RESUME_TAILOR",
        description="LLM model for resume tailoring API (gpt-4.1 or gpt-4.1-mini)"
    )
    llm_model_instruction_compiler: str = Field(
        default="gpt-4.1-mini",
        validation_alias="LLM_MODEL_INSTRUCTION_COMPILER",
        description="LLM model for instruction compiler (default: gpt-4.1-mini for fast processing)"
    )
    llm_model_embedding_default: str = Field(
        default="embedding-3-large",
        validation_alias="LLM_MODEL_EMBEDDING_DEFAULT",
        description="Default embedding model (embedding-3-large or embedding-3-small)"
    )
    llm_model_course_embedding: str = Field(
        default="embedding-3-small",
        validation_alias="LLM_MODEL_COURSE_EMBEDDING",
        description="Embedding model for course search (default: embedding-3-small for efficiency)"
    )

    # Feature flags for LLM model selection
    enable_llm_model_override: bool = Field(
        default=True,
        validation_alias="ENABLE_LLM_MODEL_OVERRIDE",
        description="Allow request parameters to override LLM model selection"
    )
    enable_llm_model_header: bool = Field(
        default=True,
        validation_alias="ENABLE_LLM_MODEL_HEADER",
        description="Allow HTTP header (X-LLM-Model) to override LLM model selection"
    )

    # Security settings
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30

    # CORS settings - secured for production
    cors_origins: str = "https://airesumeadvisor.com,https://airesumeadvisor.bubbleapps.io,http://localhost:3000"
    cors_allow_credentials: bool = True
    cors_allow_methods: str = "GET,POST,PUT,DELETE,OPTIONS"
    cors_allow_headers: str = "Content-Type,Authorization,X-Requested-With"

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Monitoring Log File Configuration
    monitoring_log_file: str = Field(
        default="",
        validation_alias="MONITORING_LOG_FILE",
        description=(
            "Path to monitoring log file for local development. "
            "If empty, logs go to stdout (Azure Container Apps will auto-collect). "
            "Example: 'logs/monitoring.log'"
        )
    )
    monitoring_log_max_size: int = Field(
        default=10,
        validation_alias="MONITORING_LOG_MAX_SIZE_MB",
        description="Maximum size of monitoring log file in MB before rotation"
    )
    monitoring_log_backup_count: int = Field(
        default=5,
        validation_alias="MONITORING_LOG_BACKUP_COUNT",
        description="Number of backup log files to keep during rotation"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore unknown environment variables

    @property
    def cors_origins_list(self):
        """Convert CORS origins string to list for FastAPI."""
        if isinstance(self.cors_origins, str):
            return [origin.strip() for origin in self.cors_origins.split(",")]
        return ["*"]

    @property
    def cors_allow_methods_list(self):
        """Convert CORS methods string to list for FastAPI."""
        if isinstance(self.cors_allow_methods, str):
            return [method.strip() for method in self.cors_allow_methods.split(",")]
        return ["*"]

    @property
    def cors_allow_headers_list(self):
        """Convert CORS headers string to list for FastAPI."""
        if isinstance(self.cors_allow_headers, str):
            return [header.strip() for header in self.cors_allow_headers.split(",")]
        return ["*"]


# Create global settings instance
settings = Settings()


# Dependency injection functions
def get_settings() -> Settings:
    """
    Dependency injection for application settings.

    Returns:
        Settings: Application settings instance
    """
    return settings
