from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_NAME: str = "AI Customer Operations Automation"
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_customer_ops"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/ai_customer_ops"
    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_PRIVATE_KEY_PATH: str = ""
    JWT_PUBLIC_KEY_PATH: str = ""

    LLM_PROVIDER: str = "openai"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_FALLBACK_PROVIDER: str = ""
    LLM_FALLBACK_API_KEY: str = ""
    LLM_FALLBACK_MODEL: str = ""

    EMBEDDING_PROVIDER: str = "openai"
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536

    VECTOR_STORE_TYPE: str = "pgvector"
    VECTOR_TOP_K: int = 20
    VECTOR_RERANK_TOP_K: int = 5
    VECTOR_SIMILARITY_THRESHOLD: float = 0.75

    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 80

    CACHE_TTL_SECONDS: int = 3600
    CACHE_SIMILARITY_THRESHOLD: float = 0.95
    CACHE_ENABLED: bool = True

    HALLUCINATION_THRESHOLD_AUTO: float = 0.9
    HALLUCINATION_THRESHOLD_FLAG: float = 0.6
    HALLUCINATION_DETECTOR_TYPE: str = "llm_judge"

    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_TENANT_PER_MINUTE: int = 600

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    GROQ_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""


@lru_cache()
def get_settings() -> Settings:
    return Settings()
