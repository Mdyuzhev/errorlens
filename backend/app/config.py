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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
