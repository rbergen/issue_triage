"""Configuration module for the Issue Triage API.

Loads environment-backed settings (database URL, OpenAI models/keys, and timeouts)
into a Pydantic BaseModel for easy access across the app.
"""
from pydantic import BaseModel
import os

class Settings(BaseModel):
    """Typed application settings sourced from environment variables.

    Attributes:
        database_url: SQLAlchemy/psycopg connection string for Postgres.
        openai_api_key: API key for OpenAI; if unset, AI features are disabled.
        embedding_model: Embedding model name used for vector search.
        embedding_dim: Dimension of the embedding vectors stored in the DB.
        generation_model: Chat/completions model used to draft replies/answers.
        openai_timeout: Timeout (seconds) for OpenAI API calls.
    """
    database_url: str = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@db:5432/triage")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    embedding_dim: int = int(os.getenv("EMBEDDING_DIM", "1536"))
    generation_model: str = os.getenv("GENERATION_MODEL", "gpt-4o-mini")
    openai_timeout: int = int(os.getenv("OPENAI_TIMEOUT", "30"))

settings = Settings()