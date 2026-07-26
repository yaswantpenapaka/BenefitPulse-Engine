"""Supabase client factory (service role for backend agent writes)."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_supabase_admin():
    """Service-role client — bypasses RLS for seed + agent pipeline writes."""
    settings = get_settings()
    if not settings.has_supabase:
        return None
    try:
        from supabase import create_client

        client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )
        logger.info("Supabase admin client ready (%s)", settings.supabase_url[:40])
        return client
    except Exception as e:
        logger.warning("Supabase admin client failed: %s", e)
        return None


@lru_cache
def get_supabase_anon():
    """Anon client — used for password login when cloud auth is enabled."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_anon_key:
        return None
    try:
        from supabase import create_client

        return create_client(settings.supabase_url, settings.supabase_anon_key)
    except Exception as e:
        logger.warning("Supabase anon client failed: %s", e)
        return None


def supabase_health() -> dict[str, Any]:
    settings = get_settings()
    out: dict[str, Any] = {
        "configured": settings.has_supabase,
        "url": settings.supabase_url[:48] + "…" if settings.supabase_url else None,
        "reachable": False,
        "error": None,
        "tables_ok": False,
    }
    if not settings.has_supabase:
        out["error"] = "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY"
        return out
    client = get_supabase_admin()
    if client is None:
        out["error"] = "Could not create Supabase client (is supabase package installed?)"
        return out
    try:
        # Lightweight probe — profiles table from schema.sql
        res = client.table("profiles").select("id").limit(1).execute()
        out["reachable"] = True
        out["tables_ok"] = True
        out["sample_count"] = len(res.data or [])
    except Exception as e:
        out["reachable"] = True  # HTTP reached but query failed
        out["error"] = str(e)
        # Try to distinguish "relation does not exist"
        if "does not exist" in str(e).lower() or "PGRST" in str(e):
            out["tables_ok"] = False
            out["error"] = (
                "Schema not applied. Run supabase/schema.sql in the Supabase SQL Editor."
            )
    return out


def log_agent_run(
    *,
    user_id: Optional[str],
    transaction_id: Optional[str],
    pipeline: dict,
    merchant_raw: str = "",
) -> None:
    """Write audit row for architecture 'Sync & Audit' path (best-effort)."""
    client = get_supabase_admin()
    if client is None:
        return
    try:
        rules = pipeline.get("rules_decision") or {}
        intel = pipeline.get("transaction_intelligence") or {}
        llm = pipeline.get("_llm") or {}
        row = {
            "user_id": user_id,
            "transaction_id": transaction_id,
            "merchant_raw": merchant_raw,
            "pipeline_status": pipeline.get("status"),
            "eligible": bool(rules.get("eligible")),
            "benefit_type": rules.get("benefit"),
            "confidence_score": pipeline.get("confidence_score"),
            "category": intel.get("category"),
            "merchant_normalized": intel.get("merchant_normalized"),
            "mode": pipeline.get("_mode"),
            "llm_meta": llm,
            "rules_decision": rules,
            "confidence_breakdown": pipeline.get("confidence_breakdown"),
            "explanation": pipeline.get("explanation"),
        }
        client.table("agent_runs").insert(row).execute()
    except Exception as e:
        logger.debug("agent_runs insert skipped: %s", e)
