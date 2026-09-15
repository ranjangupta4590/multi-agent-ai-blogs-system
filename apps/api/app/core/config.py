"""Application configuration settings."""
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # General
    PROJECT_NAME: str = "Multi-Agent AI Blog Generation Platform"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Security
    SECRET_KEY: str = Field(default="dev-super-secret-key-change-in-production-min-32-chars-long", min_length=32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ALGORITHM: str = "HS256"
    SESSION_COOKIE_NAME: str = "ai_blog_session"
    SECURE_COOKIES: bool = False  # Set to True in production with HTTPS
    SAME_SITE_POLICY: str = "lax"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./blogs_platform.db"
    # Initial administrator (server-side only; never returned by an API)
    INITIAL_ADMIN_EMAIL: Optional[str] = None
    INITIAL_ADMIN_PASSWORD: Optional[str] = Field(default=None, min_length=12)
    RESET_INITIAL_ADMIN_PASSWORD: bool = False


    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    ALLOWED_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    # LLM Provider Credentials (NEVER returned to frontend)
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    XAI_API_KEY: Optional[str] = None

    # LLM Provider Default Models

    # Active Provider Strategy
    ACTIVE_PROVIDER: Optional[str] = None  # If None, automatically detected
    ACTIVE_MODEL: Optional[str] = None
    FALLBACK_ENABLED: bool = False
    FALLBACK_PROVIDER: Optional[str] = None

    # Budget & Token Caps
    MAX_COST_PER_ARTICLE_USD: float = 5.00
    MAX_COST_PER_PROJECT_USD: float = 100.00
    MAX_COST_PER_USER_USD: float = 250.00
    MAX_REVISION_CYCLES: int = 2
    CRITIC_PASSING_SCORE: float = 8.0

    # Rate Limiting
    RATE_LIMIT_LOGIN_PER_MIN: int = 10
    RATE_LIMIT_AI_PER_MIN: int = 5
    RATE_LIMIT_RESEARCH_PER_MIN: int = 10

    # SSRF Protection
    SSRF_BLOCKED_RANGES: List[str] = [
        "127.0.0.0/8",       # Loopback
        "10.0.0.0/8",        # Private Class A
        "172.16.0.0/12",     # Private Class B
        "192.168.0.0/16",    # Private Class C
        "169.254.0.0/16",    # Link-local / AWS & GCP metadata (169.254.169.254)
        "0.0.0.0/8",         # Broadcast
        "::1/128",           # IPv6 Loopback
        "fc00::/7",          # IPv6 Unique Local
        "fe80::/10",         # IPv6 Link-local
    ]


settings = Settings()
