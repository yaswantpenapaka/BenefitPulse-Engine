"""
Supabase-backed operational store (PostgreSQL free tier).

Mirrors DemoStore methods so routers stay backend-agnostic.
Uses service_role key for agent pipeline writes (bypasses RLS).
"""

from __future__ import annotations

import logging
import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.services.supabase_client import get_supabase_admin, get_supabase_anon

logger = logging.getLogger(__name__)

DEMO_EMAIL = "demo@amex.com"
DEMO_PASSWORD = "demo1234"
DEMO_FULL_NAME = "Priya Sharma"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _uid() -> str:
    return str(uuid.uuid4())


class SupabaseStore:
    def __init__(self) -> None:
        client = get_supabase_admin()
        if client is None:
            raise RuntimeError("Supabase admin client unavailable")
        self.client = client

    # ── Auth ──────────────────────────────────────────────────────────

    def authenticate(self, email: str, password: str) -> Optional[dict]:
        anon = get_supabase_anon()
        if anon is None:
            return None
        try:
            res = anon.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            session = res.session
            user = res.user
            if not session or not user:
                return None
            profile = self.get_profile(user.id)
            if not profile:
                profile = {
                    "id": user.id,
                    "email": email,
                    "full_name": (user.user_metadata or {}).get("full_name")
                    or DEMO_FULL_NAME,
                }
            return {
                "access_token": session.access_token,
                "user": profile,
            }
        except Exception as e:
            logger.warning("Supabase login failed: %s", e)
            return None

    def signup(self, email: str, password: str, full_name: str) -> dict:
        anon = get_supabase_anon()
        if anon is None:
            raise ValueError("Supabase auth not configured")
        try:
            res = anon.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                    "options": {"data": {"full_name": full_name}},
                }
            )
            session = res.session
            user = res.user
            if not user:
                raise ValueError("Signup failed — check email confirmation settings")
            # Ensure profile row (trigger may race)
            try:
                self.client.table("profiles").upsert(
                    {
                        "id": user.id,
                        "email": email,
                        "full_name": full_name,
                    }
                ).execute()
            except Exception:
                pass
            # Auto-create a Platinum card for new members
            try:
                self.client.table("cards").insert(
                    {
                        "user_id": user.id,
                        "card_name": "American Express Platinum",
                        "card_type": "Platinum",
                        "last_four": "1005",
                        "is_active": True,
                    }
                ).execute()
            except Exception:
                pass
            if not session:
                # Email confirm may be required — fall back message
                raise ValueError(
                    "Account created. If login fails, disable email confirmation "
                    "in Supabase Auth settings for local demo, then try again."
                )
            return {
                "access_token": session.access_token,
                "user": self.get_profile(user.id)
                or {"id": user.id, "email": email, "full_name": full_name},
            }
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(str(e)) from e

    def user_id_from_token(self, token: str) -> Optional[str]:
        if not token:
            return None
        if token.startswith("Bearer "):
            token = token[7:]
        # Demo token compatibility when dual-mode
        if token.startswith("demo-token-"):
            return token.replace("demo-token-", "", 1)
        try:
            from app.config import get_settings
            import jwt

            settings = get_settings()
            if settings.supabase_jwt_secret:
                payload = jwt.decode(
                    token,
                    settings.supabase_jwt_secret,
                    algorithms=["HS256"],
                    audience="authenticated",
                )
                return payload.get("sub")
        except Exception:
            pass
        # Fallback: ask Supabase
        try:
            anon = get_supabase_anon()
            if anon:
                user = anon.auth.get_user(token)
                if user and user.user:
                    return user.user.id
        except Exception:
            pass
        return None

    def get_profile(self, user_id: str) -> Optional[dict]:
        res = (
            self.client.table("profiles")
            .select("*")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return deepcopy(rows[0]) if rows else None

    # ── Domain ────────────────────────────────────────────────────────

    def get_cards(self, user_id: str) -> list[dict]:
        res = (
            self.client.table("cards")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        return list(res.data or [])

    def get_transactions(self, user_id: str) -> list[dict]:
        res = (
            self.client.table("transactions")
            .select("*")
            .eq("user_id", user_id)
            .order("transaction_date", desc=True)
            .execute()
        )
        return list(res.data or [])

    def get_transaction(self, txn_id: str) -> Optional[dict]:
        res = (
            self.client.table("transactions")
            .select("*")
            .eq("id", txn_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return deepcopy(rows[0]) if rows else None

    def get_benefits(self, user_id: str) -> list[dict]:
        res = (
            self.client.table("detected_benefits")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        benefits = list(res.data or [])
        for b in benefits:
            txn = self.get_transaction(b["transaction_id"])
            if txn:
                b["merchant"] = txn.get("merchant_normalized") or txn.get("merchant_raw")
                b["amount"] = float(txn.get("amount") or 0)
                b["transaction_date"] = txn.get("transaction_date")
                b["category"] = txn.get("category")
        return benefits

    def get_benefit(self, benefit_id: str, user_id: Optional[str] = None) -> Optional[dict]:
        q = self.client.table("detected_benefits").select("*").eq("id", benefit_id)
        if user_id:
            q = q.eq("user_id", user_id)
        res = q.limit(1).execute()
        rows = res.data or []
        if not rows:
            return None
        result = deepcopy(rows[0])
        txn = self.get_transaction(result["transaction_id"])
        if txn:
            result["merchant"] = txn.get("merchant_normalized") or txn.get("merchant_raw")
            result["amount"] = float(txn.get("amount") or 0)
            result["transaction_date"] = txn.get("transaction_date")
            result["category"] = txn.get("category")
            result["transaction"] = txn
        claim = self.get_claim_by_benefit(benefit_id)
        if claim:
            result["claim"] = claim
            result["prefilled_data"] = claim.get("prefilled_data")
            result["missing_documents"] = claim.get("missing_documents")
        return result

    def get_claim_by_benefit(self, benefit_id: str) -> Optional[dict]:
        res = (
            self.client.table("claims")
            .select("*")
            .eq("detected_benefit_id", benefit_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return deepcopy(rows[0]) if rows else None

    def get_claim(self, claim_id: str, user_id: Optional[str] = None) -> Optional[dict]:
        q = self.client.table("claims").select("*").eq("id", claim_id)
        if user_id:
            q = q.eq("user_id", user_id)
        res = q.limit(1).execute()
        rows = res.data or []
        return deepcopy(rows[0]) if rows else None

    def get_claims(self, user_id: str) -> list[dict]:
        res = (
            self.client.table("claims")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        return list(res.data or [])

    def update_claim(self, claim_id: str, user_id: str, updates: dict) -> Optional[dict]:
        payload = {k: v for k, v in updates.items() if v is not None}
        if not payload:
            return self.get_claim(claim_id, user_id)
        res = (
            self.client.table("claims")
            .update(payload)
            .eq("id", claim_id)
            .eq("user_id", user_id)
            .execute()
        )
        rows = res.data or []
        return deepcopy(rows[0]) if rows else self.get_claim(claim_id, user_id)

    def submit_claim(
        self,
        claim_id: str,
        user_id: str,
        notes: Optional[str] = None,
        prefilled: Optional[dict] = None,
    ) -> Optional[dict]:
        payload: dict[str, Any] = {
            "status": "submitted",
            "submitted_at": _iso(_now()),
        }
        if notes is not None:
            payload["customer_notes"] = notes
        if prefilled is not None:
            payload["prefilled_data"] = prefilled
        claim = self.update_claim(claim_id, user_id, payload)
        if claim and claim.get("detected_benefit_id"):
            try:
                self.client.table("detected_benefits").update(
                    {"status": "submitted"}
                ).eq("id", claim["detected_benefit_id"]).execute()
            except Exception as e:
                logger.warning("benefit status update failed: %s", e)
        return claim

    def add_document(
        self, claim_id: str, file_url: str, file_name: str, doc_type: str = "receipt"
    ) -> dict:
        doc = {
            "id": _uid(),
            "claim_id": claim_id,
            "file_url": file_url,
            "file_name": file_name,
            "document_type": doc_type,
            "uploaded_at": _iso(_now()),
        }
        self.client.table("documents").insert(doc).execute()
        claim = self.get_claim(claim_id)
        if claim:
            missing = list(claim.get("missing_documents") or [])
            if doc_type in ("receipt", "receipt_photo") and "receipt_photo" in missing:
                missing.remove("receipt_photo")
                self.client.table("claims").update(
                    {"missing_documents": missing}
                ).eq("id", claim_id).execute()
        return doc

    def ensure_claim_for_benefit(self, benefit_id: str, user_id: str) -> Optional[dict]:
        existing = self.get_claim_by_benefit(benefit_id)
        if existing:
            return existing
        benefit = self.get_benefit(benefit_id, user_id)
        if not benefit:
            return None
        txn = benefit.get("transaction") or self.get_transaction(benefit["transaction_id"])
        if not txn:
            return None
        window = benefit.get("coverage_window_days") or 90
        prefilled = {
            "benefit_type": benefit["benefit_type"],
            "merchant": txn.get("merchant_normalized") or txn.get("merchant_raw"),
            "amount": float(txn["amount"]),
            "currency": txn.get("currency", "INR"),
            "transaction_date": txn["transaction_date"],
            "transaction_id": txn["id"],
            "card_name": "American Express Platinum",
            "category": txn.get("category"),
            "item_description": txn.get("description"),
            "coverage_window_days": window,
            "max_coverage_amount": benefit.get("max_coverage_amount"),
            "policy_reference": benefit.get("policy_reference"),
            "explanation": benefit.get("explanation"),
            "confidence_score": benefit.get("confidence_score"),
        }
        claim = {
            "id": _uid(),
            "detected_benefit_id": benefit_id,
            "user_id": user_id,
            "status": "draft",
            "prefilled_data": prefilled,
            "missing_documents": ["receipt_photo"],
        }
        res = self.client.table("claims").insert(claim).execute()
        rows = res.data or [claim]
        return deepcopy(rows[0])

    def add_transaction(
        self,
        user_id: str,
        merchant_raw: str,
        amount: float,
        *,
        description: str = "",
        category: Optional[str] = None,
        mcc: Optional[str] = None,
        currency: str = "INR",
        transaction_date: Optional[str] = None,
        card_id: Optional[str] = None,
        merchant_normalized: Optional[str] = None,
    ) -> dict:
        cards = self.get_cards(user_id)
        if not card_id:
            card_id = cards[0]["id"] if cards else None
        txn = {
            "id": _uid(),
            "user_id": user_id,
            "card_id": card_id,
            "merchant_raw": merchant_raw,
            "merchant_normalized": merchant_normalized,
            "amount": float(amount),
            "currency": currency,
            "transaction_date": transaction_date or _iso(_now()),
            "mcc": mcc,
            "category": category,
            "description": description,
        }
        res = self.client.table("transactions").insert(txn).execute()
        rows = res.data or [txn]
        return deepcopy(rows[0])

    def apply_pipeline_result(
        self,
        user_id: str,
        transaction: dict,
        pipeline: dict,
    ) -> Optional[dict]:
        status = pipeline.get("status") or ""
        rules = pipeline.get("rules_decision") or {}
        if status in ("not_eligible",) or not rules.get("eligible"):
            return None

        pref = pipeline.get("prefilled_claim") or {}
        conf = pipeline.get("confidence_score")
        explanation = pipeline.get("explanation") or pref.get("explanation")
        benefit_type = rules.get("benefit") or pref.get("benefit_type") or "Purchase Protection"
        intel = pipeline.get("transaction_intelligence") or {}

        # Update transaction normalization
        txn_updates = {}
        if intel.get("merchant_normalized"):
            txn_updates["merchant_normalized"] = intel["merchant_normalized"]
        if intel.get("category"):
            txn_updates["category"] = intel["category"]
        if intel.get("product_type") and not transaction.get("description"):
            txn_updates["description"] = intel["product_type"]
        if txn_updates:
            self.client.table("transactions").update(txn_updates).eq(
                "id", transaction["id"]
            ).execute()

        # Upsert benefit for this transaction
        existing = (
            self.client.table("detected_benefits")
            .select("*")
            .eq("transaction_id", transaction["id"])
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        existing_rows = existing.data or []
        benefit_payload = {
            "transaction_id": transaction["id"],
            "user_id": user_id,
            "benefit_type": benefit_type,
            "confidence_score": conf,
            "status": "prefilled" if pref else "detected",
            "explanation": explanation,
            "policy_reference": rules.get("policy_reference") or pref.get("policy_reference"),
            "coverage_window_days": rules.get("coverage_window_days")
            or pref.get("coverage_window_days"),
            "max_coverage_amount": rules.get("max_coverage") or pref.get("max_coverage_amount"),
            "confidence_breakdown": pipeline.get("confidence_breakdown"),
        }

        if existing_rows:
            bid = existing_rows[0]["id"]
            self.client.table("detected_benefits").update(benefit_payload).eq(
                "id", bid
            ).execute()
            benefit = {**existing_rows[0], **benefit_payload, "id": bid}
            claim_existing = self.get_claim_by_benefit(bid)
            missing = pipeline.get("missing_documents") or ["receipt_photo"]
            if claim_existing and claim_existing.get("status") == "draft":
                self.client.table("claims").update(
                    {
                        "prefilled_data": pref or claim_existing.get("prefilled_data"),
                        "missing_documents": missing,
                    }
                ).eq("id", claim_existing["id"]).execute()
                claim = self.get_claim(claim_existing["id"])
            elif not claim_existing:
                claim = {
                    "id": _uid(),
                    "detected_benefit_id": bid,
                    "user_id": user_id,
                    "status": "draft",
                    "prefilled_data": pref,
                    "missing_documents": missing,
                }
                self.client.table("claims").insert(claim).execute()
            else:
                claim = claim_existing
        else:
            bid = _uid()
            benefit_payload["id"] = bid
            self.client.table("detected_benefits").insert(benefit_payload).execute()
            benefit = benefit_payload
            claim = {
                "id": _uid(),
                "detected_benefit_id": bid,
                "user_id": user_id,
                "status": "draft",
                "prefilled_data": pref
                or {
                    "benefit_type": benefit_type,
                    "merchant": intel.get("merchant_normalized")
                    or transaction.get("merchant_raw"),
                    "amount": transaction.get("amount"),
                    "explanation": explanation,
                },
                "missing_documents": pipeline.get("missing_documents") or ["receipt_photo"],
            }
            self.client.table("claims").insert(claim).execute()

        result = deepcopy(benefit)
        result["claim"] = deepcopy(claim) if claim else None
        return result


_supabase_store: Optional[SupabaseStore] = None


def get_supabase_store() -> SupabaseStore:
    global _supabase_store
    if _supabase_store is None:
        _supabase_store = SupabaseStore()
    return _supabase_store
