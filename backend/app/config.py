"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # App info
    version: str = "0.1.0"

    # LLM provider: "gemini" or "groq"
    llm_provider: str = "gemini"

    # API keys (loaded from env)
    gemini_api_key: str = ""
    groq_api_key: str = ""

    # Auth
    admin_key: str = "change_me"

    # Rate limits (for regular users)
    rate_limit_per_day: int = 10
    max_payload_kb: int = 500
    max_console_logs: int = 100
    max_network_errors: int = 10
    max_screenshot_kb: int = 500
    max_recorded_requests: int = 50

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
