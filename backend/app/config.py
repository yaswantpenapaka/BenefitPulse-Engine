"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"
CHROMA_DIR = BASE_DIR / "data" / "chroma"
DEMO_DATA_PATH = BASE_DIR / "data" / "demo_store.json"


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
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Demo mode: local JSON store for auth/data (always works offline)
    demo_mode: bool = True

    # Data backend: auto | demo | supabase
    # auto = supabase when keys present AND demo_mode=false, else demo
    data_backend: str = "auto"

    # Supabase (cloud Postgres + Auth free tier)
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    # Google Gemini
    google_api_key: str = ""
    # Prefer 2.5-flash — free tier for gemini-2.0-flash is often exhausted/zero.
    gemini_model: str = "gemini-2.5-flash"
    embedding_model: str = "models/gemini-embedding-001"
    # Comma-separated fallbacks tried when the primary model returns 429/404
    gemini_fallback_models: str = "gemini-flash-latest,gemini-2.5-flash,gemini-2.0-flash"

    # RAG / ChromaDB
    chroma_reindex: bool = False  # set true once to force rebuild, then back to false

    # Dual-write: when using demo store, also mirror agent results to Supabase (if keys set)
    supabase_sync: bool = True

    @property
    def gemini_model_candidates(self) -> list[str]:
        ordered: list[str] = []
        for name in [self.gemini_model, *self.gemini_fallback_models.split(",")]:
            n = name.strip()
            if n and n not in ordered:
                ordered.append(n)
        return ordered

    # Paths
    knowledge_base_dir: str = str(KNOWLEDGE_BASE_DIR)
    chroma_dir: str = str(CHROMA_DIR)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def has_gemini(self) -> bool:
        return bool(self.google_api_key)

    @property
    def has_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)

    @property
    def use_supabase_primary(self) -> bool:
        """True when operational data should live in Supabase Postgres."""
        if not self.has_supabase:
            return False
        backend = (self.data_backend or "auto").lower().strip()
        if backend == "supabase":
            return True
        if backend == "demo":
            return False
        # auto
        return not self.demo_mode


@lru_cache
def get_settings() -> Settings:
    return Settings()
