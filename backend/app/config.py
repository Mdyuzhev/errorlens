"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # App info
    version: str = "0.1.0"

    # LLM provider: "gemini", "groq", or "ollama"
    llm_provider: str = "gemini"

    # API keys (loaded from env)
    gemini_api_key: str = ""
    groq_api_key: str = ""

    # Ollama settings (local LLM)
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:3b"

    # Wave 4.0: LLM Provider API Keys
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GIGACHAT_CREDENTIALS: str = ""
    OLLAMA_HOST: str = "http://localhost:11434"
    DEFAULT_LLM_PROVIDER: str = "anthropic"
    DEFAULT_LLM_MODEL: str = "claude-sonnet-4-20250514"
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth (legacy X-Admin-Key)
    admin_key: str = "change_me"

    # JWT Authentication
    jwt_secret_key: str = "your-secret-key-change-in-production-min-32-chars"
    admin_password: str = "change_me_in_env"

    # Rate limits (for regular users)
    rate_limit_per_day: int = 10
    max_payload_kb: int = 500
    max_console_logs: int = 100
    max_network_errors: int = 10
    max_screenshot_kb: int = 500
    max_recorded_requests: int = 50

    # MinIO / S3 Storage
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "errorlens"
    minio_secret_key: str = "errorlens_secret"
    minio_bucket: str = "article-images"
    minio_use_ssl: bool = False
    minio_public_url: str = ""
    max_image_size_mb: int = 10
    allowed_image_types: list[str] = [
        "image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml"
    ]
    image_max_dimension: int = 2048

    # TestIt Integration (configure in .env)
    testit_url: str = ""
    testit_token: str = ""
    testit_project_id: str = ""
    testit_enabled: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
