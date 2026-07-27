"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"
CHROMA_DIR = BASE_DIR / "data" / "chroma"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Absolute path so keys load whether uvicorn is started from repo root or backend/
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "BenefitPulse Engine"
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    # Supabase (required — cloud Postgres + Auth)
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    # Google Gemini (required — agents, assistant, embeddings)
    google_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    embedding_model: str = "models/gemini-embedding-001"
    # Comma-separated alternatives when the primary model returns 429/404
    gemini_fallback_models: str = "gemini-flash-latest,gemini-2.5-flash,gemini-2.0-flash"

    # RAG / ChromaDB
    chroma_reindex: bool = False  # set true once to force rebuild, then back to false

    # Audit agent runs into Supabase agent_runs table
    supabase_sync: bool = True

    # Paths
    knowledge_base_dir: str = str(KNOWLEDGE_BASE_DIR)
    chroma_dir: str = str(CHROMA_DIR)

    @property
    def gemini_model_candidates(self) -> list[str]:
        ordered: list[str] = []
        for name in [self.gemini_model, *self.gemini_fallback_models.split(",")]:
            n = name.strip()
            if n and n not in ordered:
                ordered.append(n)
        return ordered

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def has_gemini(self) -> bool:
        return bool(self.google_api_key and self.google_api_key.strip())

    @property
    def has_supabase(self) -> bool:
        return bool(
            self.supabase_url
            and self.supabase_url.strip()
            and self.supabase_service_role_key
            and self.supabase_service_role_key.strip()
            and self.supabase_anon_key
            and self.supabase_anon_key.strip()
        )

    def required_missing(self) -> list[str]:
        """Return names of required env vars that are not set."""
        missing: list[str] = []
        if not self.has_gemini:
            missing.append("GOOGLE_API_KEY")
        if not (self.supabase_url and self.supabase_url.strip()):
            missing.append("SUPABASE_URL")
        if not (self.supabase_anon_key and self.supabase_anon_key.strip()):
            missing.append("SUPABASE_ANON_KEY")
        if not (self.supabase_service_role_key and self.supabase_service_role_key.strip()):
            missing.append("SUPABASE_SERVICE_ROLE_KEY")
        if not (self.supabase_jwt_secret and self.supabase_jwt_secret.strip()):
            missing.append("SUPABASE_JWT_SECRET")
        return missing

    def validate_required(self) -> None:
        """Raise if Supabase or Gemini credentials are missing."""
        missing = self.required_missing()
        if missing:
            raise RuntimeError(
                "BenefitPulse requires Supabase and Gemini credentials. "
                f"Missing or empty: {', '.join(missing)}. "
                "Copy backend/.env.example → backend/.env and fill in the values. "
                "See README.md for setup."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
