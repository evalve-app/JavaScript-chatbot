"""App configuration, read from environment variables (and backend/.env)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Secrets (each teammate uses their own OpenAI key; the team shares one Neon database)
    openai_api_key: str = ""
    database_url: str = "postgresql+psycopg://localhost/studybot"

    # Signs the cookie that remembers your display name. Optional for local use.
    session_secret: str = "studybot-local"

    # Models
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # Behaviour
    history_limit: int = 10  # max previous messages sent to the LLMs
    rag_top_k: int = 3

    session_max_age_days: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
