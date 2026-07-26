"""
In-memory / JSON demo data store.

Enables a full working prototype without Supabase credentials.
When Supabase is configured, the same seed shape is used for remote seeding.
"""

from __future__ import annotations

import json
import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Optional

from app.config import DEMO_DATA_PATH

# Fixed demo user credentials
DEMO_USER_ID = "a0000000-0000-4000-8000-000000000001"
DEMO_EMAIL = "demo@amex.com"
DEMO_PASSWORD = "demo1234"
DEMO_FULL_NAME = "Priya Sharma"

CARD_ID = "b0000000-0000-4000-8000-000000000001"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _uid() -> str:
    return str(uuid.uuid4())


def build_seed_data() -> dict[str, Any]:
    """Create realistic demo seed: 1 user, 1 Platinum card, 8 transactions, benefits, claims."""
    now = _now()
    days = lambda d: now - timedelta(days=d)

    transactions = [
        {
            "id": "t0000000-0000-4000-8000-000000000001",
            "user_id": DEMO_USER_ID,
            "card_id": CARD_ID,
            "merchant_raw": "AMZN MKTP IN *12AB34CD",
            "merchant_normalized": "Amazon",
            "amount": 142999.00,
            "currency": "INR",
            "transaction_date": _iso(days(23)),
            "mcc": "5732",
            "category": "Electronics",
            "description": "MacBook Air M3 15-inch",
            "created_at": _iso(days(23)),
        },
        {
            "id": "t0000000-0000-4000-8000-000000000002",
            "user_id": DEMO_USER_ID,
            "card_id": CARD_ID,
            "merchant_raw": "APPLE.COM/BILL",
            "merchant_normalized": "Apple",
            "amount": 89900.00,
            "currency": "INR",
            "transaction_date": _iso(days(15)),
            "mcc": "5732",
            "category": "Electronics",
            "description": "iPhone 16 Pro 256GB",
            "created_at": _iso(days(15)),
        },
        {
            "id": "t0000000-0000-4000-8000-000000000003",
            "user_id": DEMO_USER_ID,
            "card_id": CARD_ID,
            "merchant_raw": "INDIGO 6E-2341 BOM-DEL",
            "merchant_normalized": "IndiGo Airlines",
            "amount": 12450.00,
            "currency": "INR",
            "transaction_date": _iso(days(8)),
            "mcc": "4511",
            "category": "Travel",
            "description": "Flight BOM-DEL economy",
            "created_at": _iso(days(8)),
        },
        {
            "id": "t0000000-0000-4000-8000-000000000004",
            "user_id": DEMO_USER_ID,
            "card_id": CARD_ID,
            "merchant_raw": "CROMA RETAIL PVT LTD",
            "merchant_normalized": "Croma",
            "amount": 24990.00,
            "currency": "INR",
            "transaction_date": _iso(days(40)),
            "mcc": "5732",
            "category": "Electronics",
            "description": "Sony WH-1000XM5 Headphones",
            "created_at": _iso(days(40)),
        },
        {
            "id": "t0000000-0000-4000-8000-000000000005",
            "user_id": DEMO_USER_ID,
            "card_id": CARD_ID,
            "merchant_raw": "SWIGGY *ORDER",
            "merchant_normalized": "Swiggy",
            "amount": 687.00,
            "currency": "INR",
            "transaction_date": _iso(days(2)),
            "mcc": "5812",
            "category": "Food & Dining",
            "description": "Food delivery",
            "created_at": _iso(days(2)),
        },
        {
            "id": "t0000000-0000-4000-8000-000000000006",
            "user_id": DEMO_USER_ID,
            "card_id": CARD_ID,
            "merchant_raw": "INDIAN OIL PETROL PUMP",
            "merchant_normalized": "Indian Oil",
            "amount": 3500.00,
            "currency": "INR",
            "transaction_date": _iso(days(5)),
            "mcc": "5541",
            "category": "Fuel",
            "description": "Petrol fill",
            "created_at": _iso(days(5)),
        },
        {
            "id": "t0000000-0000-4000-8000-000000000007",
            "user_id": DEMO_USER_ID,
            "card_id": CARD_ID,
            "merchant_raw": "MYNTRA DESIGNS PVT",
            "merchant_normalized": "Myntra",
            "amount": 4999.00,
            "currency": "INR",
            "transaction_date": _iso(days(12)),
            "mcc": "5651",
            "category": "Apparel",
            "description": "Winter jacket – brand apparel",
            "created_at": _iso(days(12)),
        },
        {
            "id": "t0000000-0000-4000-8000-000000000008",
            "user_id": DEMO_USER_ID,
            "card_id": CARD_ID,
            "merchant_raw": "FLIPKART *ELECTRONICS",
            "merchant_normalized": "Flipkart",
            "amount": 54990.00,
            "currency": "INR",
            "transaction_date": _iso(days(55)),
            "mcc": "5732",
            "category": "Electronics",
            "description": "Samsung 55-inch QLED TV",
            "created_at": _iso(days(55)),
        },
    ]

    # Pre-computed detected benefits for eligible transactions
    benefits = [
        {
            "id": "d0000000-0000-4000-8000-000000000001",
            "transaction_id": transactions[0]["id"],
            "user_id": DEMO_USER_ID,
            "benefit_type": "Purchase Protection",
            "confidence_score": 0.94,
            "status": "prefilled",
            "explanation": (
                "Your Amazon purchase of a MacBook Air (Electronics) is eligible under "
                "Purchase Protection. Electronics bought with an eligible Platinum Card "
                "are protected against accidental damage and theft for 90 days from purchase. "
                "67 days remain in the coverage window."
            ),
            "policy_reference": "Purchase Protection Guide – Section 3.2 (Electronics)",
            "coverage_window_days": 90,
            "max_coverage_amount": 100000.00,
            "created_at": _iso(days(22)),
            "confidence_breakdown": {
                "merchant_normalization": 0.98,
                "category_match": 0.96,
                "rule_match": 0.95,
                "policy_match": 0.92,
                "receipt_status": 0.70,
            },
        },
        {
            "id": "d0000000-0000-4000-8000-000000000002",
            "transaction_id": transactions[1]["id"],
            "user_id": DEMO_USER_ID,
            "benefit_type": "Purchase Protection",
            "confidence_score": 0.91,
            "status": "prefilled",
            "explanation": (
                "iPhone 16 Pro purchased from Apple qualifies for Purchase Protection. "
                "Smartphones are eligible electronics. Coverage window: 90 days from purchase; "
                "75 days remaining. Max coverage ₹1,00,000 per occurrence."
            ),
            "policy_reference": "Purchase Protection Guide – Section 3.2 (Electronics)",
            "coverage_window_days": 90,
            "max_coverage_amount": 100000.00,
            "created_at": _iso(days(14)),
            "confidence_breakdown": {
                "merchant_normalization": 0.99,
                "category_match": 0.97,
                "rule_match": 0.93,
                "policy_match": 0.90,
                "receipt_status": 0.70,
            },
        },
        {
            "id": "d0000000-0000-4000-8000-000000000003",
            "transaction_id": transactions[2]["id"],
            "user_id": DEMO_USER_ID,
            "benefit_type": "Travel Delay Insurance",
            "confidence_score": 0.82,
            "status": "detected",
            "explanation": (
                "Airline ticket charged to Platinum Card may trigger Travel Delay Insurance "
                "if your common carrier is delayed 4+ hours. Keep delay certificates and "
                "expense receipts ready."
            ),
            "policy_reference": "Travel Delay Insurance Certificate – Section 4.3",
            "coverage_window_days": 30,
            "max_coverage_amount": 20000.00,
            "created_at": _iso(days(7)),
            "confidence_breakdown": {
                "merchant_normalization": 0.95,
                "category_match": 0.94,
                "rule_match": 0.75,
                "policy_match": 0.85,
                "receipt_status": 0.50,
            },
        },
        {
            "id": "d0000000-0000-4000-8000-000000000004",
            "transaction_id": transactions[3]["id"],
            "user_id": DEMO_USER_ID,
            "benefit_type": "Purchase Protection",
            "confidence_score": 0.88,
            "status": "prefilled",
            "explanation": (
                "Sony WH-1000XM5 headphones from Croma are eligible under Purchase Protection. "
                "50 days remain of the 90-day coverage window. Headphones are listed as eligible electronics."
            ),
            "policy_reference": "Purchase Protection Guide – Section 3.2 (Electronics)",
            "coverage_window_days": 90,
            "max_coverage_amount": 100000.00,
            "created_at": _iso(days(39)),
            "confidence_breakdown": {
                "merchant_normalization": 0.92,
                "category_match": 0.94,
                "rule_match": 0.90,
                "policy_match": 0.88,
                "receipt_status": 0.70,
            },
        },
        {
            "id": "d0000000-0000-4000-8000-000000000005",
            "transaction_id": transactions[6]["id"],
            "user_id": DEMO_USER_ID,
            "benefit_type": "Return Protection",
            "confidence_score": 0.76,
            "status": "detected",
            "explanation": (
                "Apparel purchase from Myntra may qualify for Return Protection if the merchant "
                "return window is more restrictive than Amex’s 90-day Return Protection benefit."
            ),
            "policy_reference": "Return Protection Policy – Section 2.1",
            "coverage_window_days": 90,
            "max_coverage_amount": 50000.00,
            "created_at": _iso(days(11)),
            "confidence_breakdown": {
                "merchant_normalization": 0.90,
                "category_match": 0.85,
                "rule_match": 0.72,
                "policy_match": 0.78,
                "receipt_status": 0.60,
            },
        },
        {
            "id": "d0000000-0000-4000-8000-000000000006",
            "transaction_id": transactions[7]["id"],
            "user_id": DEMO_USER_ID,
            "benefit_type": "Extended Warranty",
            "confidence_score": 0.85,
            "status": "prefilled",
            "explanation": (
                "Samsung QLED TV may qualify for Extended Warranty, which doubles the "
                "manufacturer’s warranty period (up to 12 additional months) after the original warranty ends."
            ),
            "policy_reference": "Extended Warranty Description of Coverage – Section 1.4",
            "coverage_window_days": 365,
            "max_coverage_amount": 100000.00,
            "created_at": _iso(days(54)),
            "confidence_breakdown": {
                "merchant_normalization": 0.93,
                "category_match": 0.91,
                "rule_match": 0.84,
                "policy_match": 0.86,
                "receipt_status": 0.70,
            },
        },
    ]

    def prefill_for(benefit: dict, txn: dict) -> dict:
        remaining = max(
            0,
            benefit["coverage_window_days"]
            - (now - datetime.fromisoformat(txn["transaction_date"])).days,
        )
        return {
            "benefit_type": benefit["benefit_type"],
            "merchant": txn["merchant_normalized"] or txn["merchant_raw"],
            "merchant_raw": txn["merchant_raw"],
            "amount": txn["amount"],
            "currency": txn["currency"],
            "transaction_date": txn["transaction_date"],
            "transaction_id": txn["id"],
            "card_name": "American Express Platinum",
            "card_last_four": "1005",
            "card_type": "Platinum",
            "category": txn["category"],
            "item_description": txn["description"],
            "coverage_window_days": benefit["coverage_window_days"],
            "coverage_remaining_days": remaining,
            "max_coverage_amount": benefit["max_coverage_amount"],
            "policy_reference": benefit["policy_reference"],
            "explanation": benefit["explanation"],
            "confidence_score": benefit["confidence_score"],
            "claim_deadline": _iso(
                datetime.fromisoformat(txn["transaction_date"])
                + timedelta(days=benefit["coverage_window_days"])
            ),
            "incident_type": (
                "accidental_damage_or_theft"
                if benefit["benefit_type"] == "Purchase Protection"
                else "other"
            ),
            "estimated_claim_amount": min(txn["amount"], benefit["max_coverage_amount"]),
        }

    txn_by_id = {t["id"]: t for t in transactions}
    claims = []
    for b in benefits:
        if b["status"] in ("prefilled", "detected"):
            txn = txn_by_id[b["transaction_id"]]
            missing = ["receipt_photo"]
            if b["benefit_type"] == "Travel Delay Insurance":
                missing = ["delay_certificate", "expense_receipts"]
            elif b["benefit_type"] == "Return Protection":
                missing = ["receipt_photo", "merchant_refusal"]
            claims.append(
                {
                    "id": _uid(),
                    "detected_benefit_id": b["id"],
                    "user_id": DEMO_USER_ID,
                    "status": "draft",
                    "prefilled_data": prefill_for(b, txn),
                    "missing_documents": missing,
                    "customer_notes": None,
                    "submitted_at": None,
                    "created_at": b["created_at"],
                }
            )

    return {
        "users": [
            {
                "id": DEMO_USER_ID,
                "email": DEMO_EMAIL,
                "password": DEMO_PASSWORD,
                "full_name": DEMO_FULL_NAME,
                "created_at": _iso(days(90)),
            }
        ],
        "profiles": [
            {
                "id": DEMO_USER_ID,
                "full_name": DEMO_FULL_NAME,
                "email": DEMO_EMAIL,
                "created_at": _iso(days(90)),
            }
        ],
        "cards": [
            {
                "id": CARD_ID,
                "user_id": DEMO_USER_ID,
                "card_name": "American Express Platinum",
                "card_type": "Platinum",
                "last_four": "1005",
                "is_active": True,
                "created_at": _iso(days(90)),
            }
        ],
        "transactions": transactions,
        "detected_benefits": benefits,
        "claims": claims,
        "documents": [],
        "sessions": {},
    }


class DemoStore:
    """Thread-safe demo persistence with optional JSON snapshot."""

    def __init__(self, path: Optional[Path] = None):
        self.path = path or DEMO_DATA_PATH
        self._lock = Lock()
        self.data = build_seed_data()
        self._load_or_seed()

    def _load_or_seed(self) -> None:
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                return
            except Exception:
                pass
        self._persist()

    def _persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, default=str)

    def reset(self) -> None:
        with self._lock:
            self.data = build_seed_data()
            self._persist()

    def save(self) -> None:
        with self._lock:
            self._persist()

    # ── Auth ──────────────────────────────────────────────────────────

    def authenticate(self, email: str, password: str) -> Optional[dict]:
        for u in self.data["users"]:
            if u["email"].lower() == email.lower() and u["password"] == password:
                token = f"demo-token-{u['id']}"
                self.data["sessions"][token] = u["id"]
                self.save()
                return {
                    "access_token": token,
                    "user": self.get_profile(u["id"]),
                }
        return None

    def signup(self, email: str, password: str, full_name: str) -> dict:
        for u in self.data["users"]:
            if u["email"].lower() == email.lower():
                raise ValueError("Email already registered")
        user_id = _uid()
        user = {
            "id": user_id,
            "email": email,
            "password": password,
            "full_name": full_name,
            "created_at": _iso(_now()),
        }
        self.data["users"].append(user)
        self.data["profiles"].append(
            {
                "id": user_id,
                "full_name": full_name,
                "email": email,
                "created_at": user["created_at"],
            }
        )
        token = f"demo-token-{user_id}"
        self.data["sessions"][token] = user_id
        self.save()
        return {"access_token": token, "user": self.get_profile(user_id)}

    def user_id_from_token(self, token: str) -> Optional[str]:
        if not token:
            return None
        if token.startswith("Bearer "):
            token = token[7:]
        # Allow fixed demo token pattern
        if token.startswith("demo-token-"):
            uid = token.replace("demo-token-", "", 1)
            if any(u["id"] == uid for u in self.data["users"]):
                return uid
        return self.data.get("sessions", {}).get(token)

    def get_profile(self, user_id: str) -> Optional[dict]:
        for p in self.data["profiles"]:
            if p["id"] == user_id:
                return deepcopy(p)
        return None

    # ── Domain queries ────────────────────────────────────────────────

    def get_cards(self, user_id: str) -> list[dict]:
        return [deepcopy(c) for c in self.data["cards"] if c["user_id"] == user_id]

    def get_transactions(self, user_id: str) -> list[dict]:
        txns = [deepcopy(t) for t in self.data["transactions"] if t["user_id"] == user_id]
        txns.sort(key=lambda t: t["transaction_date"], reverse=True)
        return txns

    def get_transaction(self, txn_id: str) -> Optional[dict]:
        for t in self.data["transactions"]:
            if t["id"] == txn_id:
                return deepcopy(t)
        return None

    def get_benefits(self, user_id: str) -> list[dict]:
        benefits = [
            deepcopy(b) for b in self.data["detected_benefits"] if b["user_id"] == user_id
        ]
        for b in benefits:
            txn = self.get_transaction(b["transaction_id"])
            if txn:
                b["merchant"] = txn.get("merchant_normalized") or txn.get("merchant_raw")
                b["amount"] = txn.get("amount")
                b["transaction_date"] = txn.get("transaction_date")
                b["category"] = txn.get("category")
        benefits.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        return benefits

    def get_benefit(self, benefit_id: str, user_id: Optional[str] = None) -> Optional[dict]:
        for b in self.data["detected_benefits"]:
            if b["id"] == benefit_id and (user_id is None or b["user_id"] == user_id):
                result = deepcopy(b)
                txn = self.get_transaction(b["transaction_id"])
                if txn:
                    result["merchant"] = txn.get("merchant_normalized") or txn.get("merchant_raw")
                    result["amount"] = txn.get("amount")
                    result["transaction_date"] = txn.get("transaction_date")
                    result["category"] = txn.get("category")
                    result["transaction"] = txn
                claim = self.get_claim_by_benefit(benefit_id)
                if claim:
                    result["claim"] = claim
                    result["prefilled_data"] = claim.get("prefilled_data")
                    result["missing_documents"] = claim.get("missing_documents")
                return result
        return None

    def get_claim_by_benefit(self, benefit_id: str) -> Optional[dict]:
        for c in self.data["claims"]:
            if c["detected_benefit_id"] == benefit_id:
                return deepcopy(c)
        return None

    def get_claim(self, claim_id: str, user_id: Optional[str] = None) -> Optional[dict]:
        for c in self.data["claims"]:
            if c["id"] == claim_id and (user_id is None or c["user_id"] == user_id):
                return deepcopy(c)
        return None

    def get_claims(self, user_id: str) -> list[dict]:
        return [deepcopy(c) for c in self.data["claims"] if c["user_id"] == user_id]

    def update_claim(
        self, claim_id: str, user_id: str, updates: dict
    ) -> Optional[dict]:
        with self._lock:
            for i, c in enumerate(self.data["claims"]):
                if c["id"] == claim_id and c["user_id"] == user_id:
                    for k, v in updates.items():
                        if v is not None and k in c:
                            c[k] = v
                    self.data["claims"][i] = c
                    self._persist()
                    return deepcopy(c)
        return None

    def submit_claim(
        self, claim_id: str, user_id: str, notes: Optional[str] = None, prefilled: Optional[dict] = None
    ) -> Optional[dict]:
        with self._lock:
            for i, c in enumerate(self.data["claims"]):
                if c["id"] == claim_id and c["user_id"] == user_id:
                    c["status"] = "submitted"
                    c["submitted_at"] = _iso(_now())
                    if notes is not None:
                        c["customer_notes"] = notes
                    if prefilled is not None:
                        c["prefilled_data"] = prefilled
                    # Update linked benefit status
                    for j, b in enumerate(self.data["detected_benefits"]):
                        if b["id"] == c["detected_benefit_id"]:
                            b["status"] = "submitted"
                            self.data["detected_benefits"][j] = b
                    self.data["claims"][i] = c
                    self._persist()
                    return deepcopy(c)
        return None

    def add_document(self, claim_id: str, file_url: str, file_name: str, doc_type: str = "receipt") -> dict:
        doc = {
            "id": _uid(),
            "claim_id": claim_id,
            "file_url": file_url,
            "file_name": file_name,
            "document_type": doc_type,
            "uploaded_at": _iso(_now()),
        }
        with self._lock:
            self.data["documents"].append(doc)
            # Remove from missing if receipt
            for i, c in enumerate(self.data["claims"]):
                if c["id"] == claim_id:
                    missing = list(c.get("missing_documents") or [])
                    if doc_type in ("receipt", "receipt_photo") and "receipt_photo" in missing:
                        missing.remove("receipt_photo")
                    c["missing_documents"] = missing
                    self.data["claims"][i] = c
            self._persist()
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
        # Build prefill via local helper logic
        from datetime import datetime as dt

        now = _now()
        window = benefit.get("coverage_window_days") or 90
        txn_date = dt.fromisoformat(txn["transaction_date"]) if isinstance(txn["transaction_date"], str) else txn["transaction_date"]
        remaining = max(0, window - (now - txn_date).days)
        prefilled = {
            "benefit_type": benefit["benefit_type"],
            "merchant": txn.get("merchant_normalized") or txn.get("merchant_raw"),
            "amount": txn["amount"],
            "currency": txn.get("currency", "INR"),
            "transaction_date": txn["transaction_date"],
            "transaction_id": txn["id"],
            "card_name": "American Express Platinum",
            "card_last_four": "1005",
            "category": txn.get("category"),
            "item_description": txn.get("description"),
            "coverage_window_days": window,
            "coverage_remaining_days": remaining,
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
            "customer_notes": None,
            "submitted_at": None,
            "created_at": _iso(now),
        }
        with self._lock:
            self.data["claims"].append(claim)
            self._persist()
        return deepcopy(claim)

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
        """Inject a new transaction (for live agent testing)."""
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
            "created_at": _iso(_now()),
        }
        with self._lock:
            self.data["transactions"].append(txn)
            self._persist()
        return deepcopy(txn)

    def apply_pipeline_result(
        self,
        user_id: str,
        transaction: dict,
        pipeline: dict,
    ) -> Optional[dict]:
        """
        Persist agent output as detected_benefit + draft claim when eligible/prefilled.
        Returns the saved benefit dict, or None if not eligible.
        """
        status = pipeline.get("status") or ""
        rules = pipeline.get("rules_decision") or {}
        if status in ("not_eligible",) or not rules.get("eligible"):
            return None

        pref = pipeline.get("prefilled_claim") or {}
        conf = pipeline.get("confidence_score")
        explanation = pipeline.get("explanation") or pref.get("explanation")
        benefit_type = rules.get("benefit") or pref.get("benefit_type") or "Purchase Protection"

        # Update transaction with agent normalization
        intel = pipeline.get("transaction_intelligence") or {}
        with self._lock:
            for i, t in enumerate(self.data["transactions"]):
                if t["id"] == transaction["id"]:
                    if intel.get("merchant_normalized"):
                        t["merchant_normalized"] = intel["merchant_normalized"]
                    if intel.get("category"):
                        t["category"] = intel["category"]
                    if intel.get("product_type") and not t.get("description"):
                        t["description"] = intel["product_type"]
                    self.data["transactions"][i] = t
                    break

        existing_benefit = next(
            (
                b
                for b in self.data["detected_benefits"]
                if b["transaction_id"] == transaction["id"] and b["user_id"] == user_id
            ),
            None,
        )
        benefit_id = existing_benefit["id"] if existing_benefit else _uid()
        benefit = {
            "id": benefit_id,
            "transaction_id": transaction["id"],
            "user_id": user_id,
            "benefit_type": benefit_type,
            "confidence_score": conf,
            "status": "prefilled" if pref else "detected",
            "explanation": explanation,
            "policy_reference": rules.get("policy_reference") or pref.get("policy_reference"),
            "coverage_window_days": rules.get("coverage_window_days") or pref.get("coverage_window_days"),
            "max_coverage_amount": rules.get("max_coverage") or pref.get("max_coverage_amount"),
            "created_at": existing_benefit.get("created_at") if existing_benefit else _iso(_now()),
            "confidence_breakdown": pipeline.get("confidence_breakdown"),
        }
        prefilled_data = pref or {
            "benefit_type": benefit_type,
            "merchant": intel.get("merchant_normalized") or transaction.get("merchant_raw"),
            "amount": transaction.get("amount"),
            "explanation": explanation,
        }
        missing = pipeline.get("missing_documents") or ["receipt_photo"]

        with self._lock:
            if existing_benefit:
                for i, b in enumerate(self.data["detected_benefits"]):
                    if b["id"] == benefit_id:
                        self.data["detected_benefits"][i] = benefit
                        break
                # Refresh draft claim if still draft
                updated_claim = None
                for i, c in enumerate(self.data["claims"]):
                    if c["detected_benefit_id"] == benefit_id:
                        if c.get("status") == "draft":
                            c["prefilled_data"] = prefilled_data
                            c["missing_documents"] = missing
                            self.data["claims"][i] = c
                        updated_claim = deepcopy(c)
                        break
                if updated_claim is None:
                    claim = {
                        "id": _uid(),
                        "detected_benefit_id": benefit_id,
                        "user_id": user_id,
                        "status": "draft",
                        "prefilled_data": prefilled_data,
                        "missing_documents": missing,
                        "customer_notes": None,
                        "submitted_at": None,
                        "created_at": _iso(_now()),
                    }
                    self.data["claims"].append(claim)
                    updated_claim = deepcopy(claim)
            else:
                claim = {
                    "id": _uid(),
                    "detected_benefit_id": benefit_id,
                    "user_id": user_id,
                    "status": "draft",
                    "prefilled_data": prefilled_data,
                    "missing_documents": missing,
                    "customer_notes": None,
                    "submitted_at": None,
                    "created_at": _iso(_now()),
                }
                self.data["detected_benefits"].append(benefit)
                self.data["claims"].append(claim)
                updated_claim = deepcopy(claim)

            self._persist()

        result = deepcopy(benefit)
        result["claim"] = updated_claim
        return result


_store: Optional[DemoStore] = None


def get_demo_store() -> DemoStore:
    global _store
    if _store is None:
        _store = DemoStore()
    return _store
