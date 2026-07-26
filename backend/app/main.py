"""BenefitPulse Engine — FastAPI entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import BASE_DIR, get_settings
from app.rag.vector_store import get_vector_store
from app.routers import (
    assistant_router,
    auth_router,
    benefits_router,
    claims_router,
    dashboard_router,
)
from app.services.store import get_store, get_store_kind, system_status

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(
        "Starting %s (demo_mode=%s, use_supabase_primary=%s)",
        settings.app_name,
        settings.demo_mode,
        settings.use_supabase_primary,
    )

    # Operational store
    store = get_store()
    logger.info("Operational store: %s", get_store_kind())
    if get_store_kind() == "demo" and hasattr(store, "data"):
        logger.info(
            "Demo store ready – users=%d, benefits=%d",
            len(store.data.get("users", [])),
            len(store.data.get("detected_benefits", [])),
        )

    # RAG knowledge base (ChromaDB + Gemini embeddings when available)
    try:
        vs = get_vector_store()
        st = vs.status()
        logger.info(
            "RAG ready backend=%s chunks=%d embeddings=%s",
            st.get("backend"),
            st.get("chunk_count"),
            st.get("embedding_mode"),
        )
    except Exception as e:
        logger.warning("Vector store init issue: %s", e)

    yield
    logger.info("Shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description="Detect unused card protections, pre-fill claims, and answer policy questions",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list + ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router, prefix="/api")
    app.include_router(dashboard_router, prefix="/api")
    app.include_router(benefits_router, prefix="/api")
    app.include_router(claims_router, prefix="/api")
    app.include_router(assistant_router, prefix="/api")

    # Static uploads
    upload_dir = BASE_DIR / "data" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")

    @app.get("/health")
    def health():
        status = system_status()
        return {
            "status": "ok",
            "app": settings.app_name,
            "demo_mode": settings.demo_mode,
            "data_backend": status.get("data_backend"),
            "gemini_configured": settings.has_gemini,
            "gemini_model": settings.gemini_model if settings.has_gemini else None,
            "supabase_configured": settings.has_supabase,
            "rag": status.get("rag"),
            "agents": "gemini_live" if settings.has_gemini else "rule_fallback",
        }

    @app.get("/api/system/status")
    def api_system_status():
        """Full stack status for the live demo UI (architecture checklist)."""
        return system_status()

    @app.post("/api/system/reindex-rag")
    def reindex_rag():
        """Rebuild ChromaDB index from knowledge_base/*.md (admin/dev helper)."""
        from app.rag.vector_store import reset_vector_store

        vs = reset_vector_store(force_reindex=True)
        return {"ok": True, "rag": vs.status()}

    @app.get("/")
    def root():
        return {
            "message": "BenefitPulse Engine API",
            "docs": "/docs",
            "health": "/health",
            "system": "/api/system/status",
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
