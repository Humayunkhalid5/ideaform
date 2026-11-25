from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # repo-root .env first, then backend/.env (later files win)
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    # core
    environment: str = "development"  # development | test | production
    database_url: str = "postgresql+psycopg://ideaform:ideaform@db:5432/ideaform"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str = "change-me-in-production"
    jwt_access_token_minutes: int = 60
    log_level: str = "INFO"
    # true: run extraction jobs inside the API request instead of Celery
    # (handy on Windows without Redis/a worker; the compose stack leaves it false)
    jobs_inline: bool = False

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
    tavily_daily_credit_cap: int = 200  # hard stop on paid calls per UTC day
    tavily_base_url: str = "https://api.tavily.com"

    # knowledge engine (Phase 2)
    embedding_backend: str = "sentence-transformers"  # sentence-transformers | hashing (tests)
    hf_home: str | None = None  # where Hugging Face models are cached (default ~/.cache)
    reranker_enabled: bool = True
    chunk_words: int = 300
    chunk_overlap_words: int = 40
    retrieval_semantic_k: int = 30
    retrieval_keyword_k: int = 30
    retrieval_rerank_k: int = 20
    retrieval_final_k: int = 8
    retrieval_max_per_source: int = 3
    research_min_queries: int = 4
    research_max_queries: int = 8
    research_max_seconds: int = 600
    max_upload_bytes: int = 10_000_000
    sec_contact_email: str | None = None  # SEC EDGAR requires a real contact in the User-Agent

    # scraper
    scraper_user_agent: str = "IdeaformBot/1.0 (educational research crawler; respects robots.txt)"
    scraper_respect_robots: bool = True
    scraper_min_delay_seconds: float = 2.0
    scraper_max_pages_per_run: int = 40
    scraper_max_bytes_per_page: int = 2_000_000
    scraper_playwright_enabled: bool = True  # used only when playwright is installed
    scraper_min_words: int = 120
    # contact (email or URL) appended to the User-Agent; Wikimedia and SEC require one
    scraper_contact: str | None = None

    @property
    def crawler_user_agent(self) -> str:
        if self.scraper_contact and self.scraper_contact not in self.scraper_user_agent:
            return f"{self.scraper_user_agent} contact: {self.scraper_contact}"
        return self.scraper_user_agent
    scraper_timeout_seconds: int = 20

    # limits
    daily_token_limit_per_user: int = 200_000
    auth_rate_limit_attempts: int = 10  # per client IP per window, login and register
    auth_rate_limit_window_seconds: int = 60


INSECURE_JWT_SECRETS = {"", "change-me-in-production", "changeme", "secret"}
MIN_JWT_SECRET_LENGTH = 32


def check_jwt_secret(settings: Settings) -> None:
    """Refuse to start with a placeholder or short JWT secret.

    Only ``ENVIRONMENT=test`` is exempt, so the test suite can use a fixed key.
    """
    if settings.environment == "test":
        return
    secret = settings.jwt_secret or ""
    if secret in INSECURE_JWT_SECRETS or len(secret) < MIN_JWT_SECRET_LENGTH:
        raise RuntimeError(
            "JWT_SECRET is missing, a placeholder, or shorter than "
            f"{MIN_JWT_SECRET_LENGTH} characters. Generate one with "
            '`python -c "import secrets; print(secrets.token_urlsafe(48))"` '
            "and put it in .env."
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
