"""
Unified data store facade — Supabase PostgreSQL only.

The app refuses to start without Supabase + Gemini credentials (see config.validate_required).
"""

from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

from app.config import get_settings
from app.services.supabase_client import log_agent_run

logger = logging.getLogger(__name__)


@runtime_checkable
class DataStore(Protocol):
    def authenticate(self, email: str, password: str): ...
    def signup(self, email: str, password: str, full_name: str): ...
    def user_id_from_token(self, token: str): ...
    def get_profile(self, user_id: str): ...
    def get_cards(self, user_id: str): ...
    def get_transactions(self, user_id: str): ...
    def get_transaction(self, txn_id: str): ...
    def get_benefits(self, user_id: str): ...
    def get_benefit(self, benefit_id: str, user_id: str | None = None): ...
    def get_claim_by_benefit(self, benefit_id: str): ...
    def get_claim(self, claim_id: str, user_id: str | None = None): ...
    def get_claims(self, user_id: str): ...
    def update_claim(self, claim_id: str, user_id: str, updates: dict): ...
    def submit_claim(
        self, claim_id: str, user_id: str, notes=None, prefilled=None
    ): ...
    def add_document(
        self, claim_id: str, file_url: str, file_name: str, doc_type: str = "receipt"
    ): ...
    def ensure_claim_for_benefit(self, benefit_id: str, user_id: str): ...
    def add_transaction(self, user_id: str, merchant_raw: str, amount: float, **kwargs): ...
    def apply_pipeline_result(self, user_id: str, transaction: dict, pipeline: dict): ...


_store: Any = None
_store_kind: str = "uninitialized"


def get_store_kind() -> str:
    return _store_kind


def get_store() -> Any:
    """Return the Supabase operational store. Raises if not configured."""
    global _store, _store_kind
    if _store is not None:
        return _store

    settings = get_settings()
    settings.validate_required()

    try:
        from app.services.supabase_store import get_supabase_store

        _store = get_supabase_store()
        _store_kind = "supabase"
        logger.info("Data backend: Supabase (PostgreSQL + Auth)")
        return _store
    except Exception as e:
        logger.error("Supabase store failed to initialize: %s", e)
        raise RuntimeError(
            f"Could not connect to Supabase. Check SUPABASE_* credentials. Detail: {e}"
        ) from e


def reset_store() -> None:
    global _store, _store_kind
    _store = None
    _store_kind = "uninitialized"


def persist_pipeline_audit(
    user_id: str,
    transaction: dict,
    pipeline: dict,
) -> None:
    """Best-effort audit log into Supabase agent_runs."""
    settings = get_settings()
    if not settings.supabase_sync:
        return
    log_agent_run(
        user_id=user_id,
        transaction_id=transaction.get("id"),
        pipeline=pipeline,
        merchant_raw=transaction.get("merchant_raw") or "",
    )


def system_status() -> dict[str, Any]:
    settings = get_settings()
    from app.rag.vector_store import get_vector_store
    from app.services.supabase_client import supabase_health

    vs = get_vector_store()
    rag = vs.status()
    sb = supabase_health()

    return {
        "app": settings.app_name,
        "env": settings.app_env,
        "data_backend": "supabase",
        "gemini": {
            "configured": settings.has_gemini,
            "model": settings.gemini_model if settings.has_gemini else None,
            "embedding_model": settings.embedding_model if settings.has_gemini else None,
        },
        "rag": rag,
        "supabase": sb,
        "architecture": {
            "pipeline": [
                "Transaction Intelligence",
                "Benefit Knowledge (RAG/ChromaDB)",
                "Rules Evaluation",
                "Confidence",
                "Claim Prefill",
            ],
            "knowledge": "markdown policies → Gemini embeddings → ChromaDB → agents",
            "operational_db": "Supabase PostgreSQL",
            "auth": "Supabase Auth",
            "llm": "Google Gemini",
        },
    }
