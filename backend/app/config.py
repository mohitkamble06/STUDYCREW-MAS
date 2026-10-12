"""Application configuration using Pydantic Settings."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Ollama LLM
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "llama3.1:8b"
    llm_temperature: float = 0.1
    llm_num_ctx: int = 8192

    # Embeddings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Database
    database_url: str = "sqlite:///./studycrew.db"

    # ChromaDB
    chroma_path: str = "./chroma_data"

    # Backend
    backend_port: int = 8000
    backend_host: str = "0.0.0.0"

    # Railway provides PORT env var
    @property
    def port(self) -> int:
        """Get port from PORT env var (Railway) or fallback to backend_port."""
        import os
        return int(os.environ.get("PORT", self.backend_port))

    # Frontend
    frontend_origin: str = "http://localhost:5173"

    # RAG
    chunk_size: int = 500
    chunk_overlap: int = 50

    # LLM Provider (ollama or anthropic)
    llm_provider: str = "ollama"

    # Anthropic (for cloud deployment)
    anthropic_api_key: str = ""

    @property
    def chroma_path_resolved(self) -> Path:
        """Return resolved absolute path for ChromaDB."""
        return Path(self.chroma_path).resolve()

    @property
    def database_path_resolved(self) -> Path:
        """Return resolved absolute path for SQLite database."""
        # Extract path from sqlite:///./studycrew.db
        if self.database_url.startswith("sqlite:///"):
            db_path = self.database_url.replace("sqlite:///", "")
            return Path(db_path).resolve()
        return Path("./studycrew.db").resolve()


settings = Settings()