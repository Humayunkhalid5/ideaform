from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # core
    database_url: str = "postgresql+psycopg://ideaform:ideaform@db:5432/ideaform"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str = "change-me-in-production"
    jwt_access_token_minutes: int = 60
    log_level: str = "INFO"

    # llm provider: hosted Groq API
    groq_api_key: str | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    llm_model_fast: str = "openai/gpt-oss-20b"
    llm_model_strong: str = "openai/gpt-oss-120b"
    llm_context_window: int = 8192
    llm_request_timeout: int = 180
    llm_temperature: float = 0.2
    llm_max_tokens: int = 4096
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # live discovery
    search_provider: str = "tavily"
    tavily_api_key: str | None = None
    tavily_max_results: int = 10
    tavily_results_per_run: int = 40
    tavily_search_depth: str = "basic"
    tavily_cache_ttl_hours: int = 168

    # scraper
    scraper_user_agent: str = "IdeaformBot/1.0 (+mailto:you@example.com)"
    scraper_respect_robots: bool = True
    scraper_min_delay_seconds: float = 2.0
    scraper_max_pages_per_run: int = 40
    scraper_max_bytes_per_page: int = 2_000_000
    scraper_playwright_enabled: bool = True
    scraper_timeout_seconds: int = 20

    # limits
    daily_token_limit_per_user: int = 200_000


@lru_cache
def get_settings() -> Settings:
    return Settings()
