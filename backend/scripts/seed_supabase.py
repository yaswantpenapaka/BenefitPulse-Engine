"""
Seed Supabase with a sample member, cards, transactions, and detections.

Covers Overview / Benefits / Transactions scenarios:
  - High confidence detections (Purchase Protection)
  - Medium confidence (Return Protection, Travel Delay)
  - Low confidence (borderline Extended Warranty / aged purchase)
  - No-benefit charges (food, fuel, rides, groceries)
  - Mixed statuses: detected, prefilled

Usage (from backend/ with venv):
  python scripts/seed_supabase.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.services.supabase_client import get_supabase_admin

SEED_EMAIL = "demo@amex.com"
SEED_PASSWORD = "demo1234"
SEED_NAME = "Priya Sharma"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _days_ago(n: int) -> str:
    return _iso(_now() - timedelta(days=n))


# Transaction scenarios. benefit=None means no detection should be seeded.
# confidence bands: High >= 0.85, Medium >= 0.60, Low < 0.60
SCENARIOS: list[dict[str, Any]] = [
    # ── High confidence ──────────────────────────────────────────
    {
        "key": "high_pp_laptop",
        "merchant_raw": "AMZN MKTP IN *MBP15SEED",
        "merchant_normalized": "Amazon",
        "amount": 142999,
        "category": "Electronics",
        "description": "MacBook Air M3 15-inch",
        "mcc": "5732",
        "days_ago": 12,
        "card": "Platinum",
        "benefit": {
            "benefit_type": "Purchase Protection",
            "confidence_score": 0.93,
            "status": "prefilled",
            "explanation": (
                "High confidence: electronics purchased on The Platinum Card® fall under "
                "Purchase Protection for accidental damage and theft (90-day window). "
                "Clear merchant, full amount charged, and policy section 3.2 matches."
            ),
            "policy_reference": "Purchase Protection Guide – Section 3.2",
            "coverage_window_days": 90,
            "max_coverage_amount": 100000,
            "confidence_breakdown": {
                "merchant_match": 0.96,
                "category_fit": 0.95,
                "policy_match": 0.94,
                "window_remaining": 0.90,
            },
        },
    },
    {
        "key": "high_pp_phone",
        "merchant_raw": "APPLE.COM/BILL",
        "merchant_normalized": "Apple",
        "amount": 89900,
        "category": "Electronics",
        "description": "iPhone 16 Pro 256GB",
        "mcc": "5732",
        "days_ago": 8,
        "card": "Platinum",
        "benefit": {
            "benefit_type": "Purchase Protection",
            "confidence_score": 0.89,
            "status": "detected",
            "explanation": (
                "High confidence Purchase Protection on a new phone purchase. "
                "Merchant and category align with eligible electronics; coverage window open."
            ),
            "policy_reference": "Purchase Protection Guide – Section 3.2",
            "coverage_window_days": 90,
            "max_coverage_amount": 100000,
            "confidence_breakdown": {
                "merchant_match": 0.94,
                "category_fit": 0.93,
                "policy_match": 0.90,
                "window_remaining": 0.92,
            },
        },
    },
    # ── Medium confidence ────────────────────────────────────────
    {
        "key": "med_return_apparel",
        "merchant_raw": "MYNTRA DESIGNS PVT LTD",
        "merchant_normalized": "Myntra",
        "amount": 6499,
        "category": "Apparel",
        "description": "Winter parka – apparel",
        "mcc": "5651",
        "days_ago": 18,
        "card": "Gold",
        "benefit": {
            "benefit_type": "Return Protection",
            "confidence_score": 0.74,
            "status": "prefilled",
            "explanation": (
                "Medium confidence Return Protection: apparel is typically eligible if the "
                "merchant refuses a return within the coverage window. Confirm size/condition "
                "and merchant refusal proof before submitting."
            ),
            "policy_reference": "Return Protection Policy – Section 2.1",
            "coverage_window_days": 90,
            "max_coverage_amount": 50000,
            "confidence_breakdown": {
                "merchant_match": 0.82,
                "category_fit": 0.78,
                "policy_match": 0.72,
                "window_remaining": 0.70,
            },
        },
    },
    {
        "key": "med_travel_delay",
        "merchant_raw": "INDIGO 6E-2341 BOM-DEL",
        "merchant_normalized": "IndiGo Airlines",
        "amount": 12450,
        "category": "Travel",
        "description": "Flight BOM-DEL economy",
        "mcc": "4511",
        "days_ago": 5,
        "card": "Platinum",
        "benefit": {
            "benefit_type": "Travel Delay Insurance",
            "confidence_score": 0.67,
            "status": "detected",
            "explanation": (
                "Medium confidence Travel Delay Insurance: airline ticket on an eligible card "
                "may cover meals and lodging if the common carrier is delayed 4+ hours. "
                "Requires delay certificate and expense receipts."
            ),
            "policy_reference": "Travel Delay Insurance – Eligibility",
            "coverage_window_days": 30,
            "max_coverage_amount": 20000,
            "confidence_breakdown": {
                "merchant_match": 0.88,
                "category_fit": 0.85,
                "policy_match": 0.62,
                "window_remaining": 0.80,
            },
        },
    },
    # ── Low confidence ───────────────────────────────────────────
    {
        "key": "low_warranty",
        "merchant_raw": "CROMA RETAIL PVT LTD",
        "merchant_normalized": "Croma",
        "amount": 24990,
        "category": "Electronics",
        "description": "Sony WH-1000XM5 Headphones",
        "mcc": "5732",
        "days_ago": 40,
        "card": "Gold",
        "benefit": {
            "benefit_type": "Extended Warranty",
            "confidence_score": 0.54,
            "status": "detected",
            "explanation": (
                "Low confidence Extended Warranty: headphones may qualify if the manufacturer "
                "warranty is ≤12 months, but model-level warranty terms are unverified. "
                "Review original warranty card before filing."
            ),
            "policy_reference": "Extended Warranty – Section 1",
            "coverage_window_days": 365,
            "max_coverage_amount": 50000,
            "confidence_breakdown": {
                "merchant_match": 0.75,
                "category_fit": 0.70,
                "policy_match": 0.48,
                "window_remaining": 0.55,
            },
        },
    },
    {
        "key": "low_pp_borderline",
        "merchant_raw": "BESTBUY.COM #8821 ONLINE",
        "merchant_normalized": "Best Buy",
        "amount": 18999,
        "category": "Electronics",
        "description": "Portable SSD 2TB",
        "mcc": "5732",
        "days_ago": 78,
        "card": "Platinum",
        "benefit": {
            "benefit_type": "Purchase Protection",
            "confidence_score": 0.42,
            "status": "detected",
            "explanation": (
                "Low confidence: purchase is near the end of the 90-day protection window "
                "and the descriptor is ambiguous. May still qualify if accidental damage "
                "or theft occurred while coverage was active — needs manual review."
            ),
            "policy_reference": "Purchase Protection Guide – Section 3.2",
            "coverage_window_days": 90,
            "max_coverage_amount": 100000,
            "confidence_breakdown": {
                "merchant_match": 0.60,
                "category_fit": 0.72,
                "policy_match": 0.50,
                "window_remaining": 0.22,
            },
        },
    },
    # ── Outside coverage (agent ran — not claim-eligible) ────────
    {
        "key": "none_food",
        "merchant_raw": "SWIGGY *ORDER",
        "merchant_normalized": "Swiggy",
        "amount": 687,
        "category": "Food & Dining",
        "description": "Food delivery dinner",
        "mcc": "5812",
        "days_ago": 2,
        "card": "Gold",
        "benefit": {
            "benefit_type": "Outside coverage",
            "confidence_score": 0.12,
            "status": "not_eligible",
            "explanation": (
                "Outside coverage: food and dining are standard policy exclusions. "
                "This charge is not eligible for purchase protection, return protection, "
                "or other card-linked claims."
            ),
            "policy_reference": "General Exclusions – Consumables & dining",
            "coverage_window_days": 0,
            "max_coverage_amount": 0,
            "confidence_breakdown": {
                "merchant_match": 0.90,
                "category_fit": 0.10,
                "policy_match": 0.08,
                "window_remaining": 0.0,
            },
        },
    },
    {
        "key": "none_fuel",
        "merchant_raw": "INDIAN OIL PETROL PUMP",
        "merchant_normalized": "Indian Oil",
        "amount": 2800,
        "category": "Fuel",
        "description": "Petrol fill",
        "mcc": "5541",
        "days_ago": 3,
        "card": "Platinum",
        "benefit": {
            "benefit_type": "Outside coverage",
            "confidence_score": 0.10,
            "status": "not_eligible",
            "explanation": (
                "Outside coverage: fuel and petroleum products are excluded from card "
                "purchase protections. No claim can be opened for this posting."
            ),
            "policy_reference": "General Exclusions – Fuel & utilities",
            "coverage_window_days": 0,
            "max_coverage_amount": 0,
            "confidence_breakdown": {
                "merchant_match": 0.92,
                "category_fit": 0.08,
                "policy_match": 0.06,
                "window_remaining": 0.0,
            },
        },
    },
    {
        "key": "none_ride",
        "merchant_raw": "UBER TRIP *HELP.UBER.COM",
        "merchant_normalized": "Uber",
        "amount": 412,
        "category": "Transport",
        "description": "Ride to airport",
        "mcc": "4121",
        "days_ago": 4,
        "card": "Gold",
        "benefit": {
            "benefit_type": "Outside coverage",
            "confidence_score": 0.14,
            "status": "not_eligible",
            "explanation": (
                "Outside coverage: rideshare and local transport fares do not trigger "
                "purchase protection or travel delay insurance on their own."
            ),
            "policy_reference": "General Exclusions – Services & transport",
            "coverage_window_days": 0,
            "max_coverage_amount": 0,
            "confidence_breakdown": {
                "merchant_match": 0.88,
                "category_fit": 0.12,
                "policy_match": 0.10,
                "window_remaining": 0.0,
            },
        },
    },
    {
        "key": "none_grocery",
        "merchant_raw": "BIGBASKET *GROCERIES",
        "merchant_normalized": "BigBasket",
        "amount": 2340,
        "category": "Groceries",
        "description": "Weekly groceries",
        "mcc": "5411",
        "days_ago": 6,
        "card": "Platinum",
        "benefit": {
            "benefit_type": "Outside coverage",
            "confidence_score": 0.11,
            "status": "not_eligible",
            "explanation": (
                "Outside coverage: grocery and consumable purchases are not covered under "
                "purchase protection or return protection policy terms."
            ),
            "policy_reference": "General Exclusions – Consumables",
            "coverage_window_days": 0,
            "max_coverage_amount": 0,
            "confidence_breakdown": {
                "merchant_match": 0.85,
                "category_fit": 0.09,
                "policy_match": 0.07,
                "window_remaining": 0.0,
            },
        },
    },
]


def _missing_docs(benefit_type: str) -> list[str]:
    if benefit_type == "Travel Delay Insurance":
        return ["delay_certificate", "expense_receipts"]
    if benefit_type == "Return Protection":
        return ["receipt_photo", "merchant_refusal"]
    if benefit_type == "Extended Warranty":
        return ["receipt_photo", "manufacturer_warranty"]
    return ["receipt_photo"]


def _prefill(
    *,
    user_id: str,
    txn: dict[str, Any],
    benefit_row: dict[str, Any],
    card_name: str,
    card_last_four: str,
) -> dict[str, Any]:
    amount = float(txn["amount"])
    max_cov = float(benefit_row.get("max_coverage_amount") or amount)
    window = int(benefit_row.get("coverage_window_days") or 90)
    conf = float(benefit_row.get("confidence_score") or 0)
    return {
        "benefit_type": benefit_row["benefit_type"],
        "merchant": txn.get("merchant_normalized") or txn.get("merchant_raw"),
        "merchant_raw": txn.get("merchant_raw"),
        "amount": amount,
        "currency": txn.get("currency", "INR"),
        "transaction_date": txn.get("transaction_date"),
        "transaction_id": txn.get("id"),
        "card_name": card_name,
        "card_last_four": card_last_four,
        "card_type": benefit_row.get("_card_type") or "Platinum",
        "category": txn.get("category"),
        "item_description": txn.get("description"),
        "coverage_window_days": window,
        "coverage_remaining_days": max(0, window - int(txn.get("_days_ago") or 0)),
        "max_coverage_amount": max_cov,
        "policy_reference": benefit_row.get("policy_reference"),
        "explanation": benefit_row.get("explanation"),
        "confidence_score": conf,
        "estimated_claim_amount": min(amount, max_cov),
        "incident_type": (
            "accidental_damage_or_theft"
            if benefit_row["benefit_type"] == "Purchase Protection"
            else "other"
        ),
    }


def main() -> int:
    settings = get_settings()
    if not settings.has_supabase:
        print("ERROR: Supabase credentials missing in backend/.env")
        print(
            "  Need: SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_JWT_SECRET"
        )
        return 1

    admin = get_supabase_admin()
    if admin is None:
        print("ERROR: Could not create Supabase client. pip install supabase")
        return 1

    print("Creating / updating seed auth user…")
    user_id = None
    try:
        users = admin.auth.admin.list_users()
        for u in users:
            email = getattr(u, "email", None) or (
                u.get("email") if isinstance(u, dict) else None
            )
            if email and email.lower() == SEED_EMAIL:
                user_id = getattr(u, "id", None) or u.get("id")
                print(f"  Found existing user: {user_id}")
                break
    except Exception as e:
        print(f"  list_users note: {e}")

    if not user_id:
        try:
            created = admin.auth.admin.create_user(
                {
                    "email": SEED_EMAIL,
                    "password": SEED_PASSWORD,
                    "email_confirm": True,
                    "user_metadata": {"full_name": SEED_NAME},
                }
            )
            user = created.user if hasattr(created, "user") else created
            user_id = getattr(user, "id", None) or (
                user.get("id") if isinstance(user, dict) else None
            )
            print(f"  Created user: {user_id}")
        except Exception as e:
            print(f"ERROR creating user: {e}")
            print("  Tip: disable email confirmation; check service_role key.")
            return 1

    if not user_id:
        print("ERROR: no user id")
        return 1

    admin.table("profiles").upsert(
        {"id": user_id, "email": SEED_EMAIL, "full_name": SEED_NAME}
    ).execute()
    print("  Profile upserted")

    # ── Cards ────────────────────────────────────────────────────
    desired_cards = [
        {
            "card_name": "The Platinum Card®",
            "card_type": "Platinum",
            "last_four": "1005",
            "is_active": True,
        },
        {
            "card_name": "American Express® Gold Card",
            "card_type": "Gold",
            "last_four": "3007",
            "is_active": True,
        },
    ]

    cards = (
        admin.table("cards").select("*").eq("user_id", user_id).execute().data or []
    )
    by_type: dict[str, dict] = {
        (c.get("card_type") or "").title(): c for c in cards
    }
    card_ids: dict[str, str] = {}

    for desired in desired_cards:
        existing = by_type.get(desired["card_type"])
        if existing:
            card_ids[desired["card_type"]] = existing["id"]
            try:
                admin.table("cards").update(
                    {
                        "card_name": desired["card_name"],
                        "card_type": desired["card_type"],
                        "last_four": desired["last_four"],
                        "is_active": True,
                    }
                ).eq("id", existing["id"]).execute()
                print(f"  Updated card: {desired['card_name']}")
            except Exception as e:
                print(f"  Card update note: {e}")
        else:
            row = {"user_id": user_id, **desired}
            res = admin.table("cards").insert(row).execute()
            new_id = (res.data or [{}])[0].get("id")
            card_ids[desired["card_type"]] = new_id
            print(f"  Created card: {desired['card_name']} ({new_id})")

    platinum_id = card_ids.get("Platinum") or next(iter(card_ids.values()), None)
    if not platinum_id:
        print("ERROR: no card available")
        return 1

    # ── Reset prior seed activity (claims → benefits → transactions) ──
    print("  Clearing previous seed transactions / detections / claims…")
    try:
        claims = (
            admin.table("claims").select("id").eq("user_id", user_id).execute().data
            or []
        )
        for c in claims:
            try:
                admin.table("documents").delete().eq("claim_id", c["id"]).execute()
            except Exception:
                pass
        admin.table("claims").delete().eq("user_id", user_id).execute()
        admin.table("detected_benefits").delete().eq("user_id", user_id).execute()
        admin.table("transactions").delete().eq("user_id", user_id).execute()
    except Exception as e:
        print(f"  Clear note: {e}")

    # ── Insert transactions + detections ─────────────────────────
    benefit_count = 0
    outside_count = 0
    # Stagger benefit created_at so Overview (created_at desc) shows High → Medium → Low first.
    # Rank: higher rank = more recent. Prefer high conf, then med, then low, then extras.
    # Higher rank = more recent on Overview. Mix claim-eligible + outside coverage.
    conf_rank = {
        "high_pp_laptop": 10,
        "none_food": 9,
        "med_return_apparel": 8,
        "none_fuel": 7,
        "low_warranty": 6,
        "high_pp_phone": 5,
        "med_travel_delay": 4,
        "none_ride": 3,
        "low_pp_borderline": 2,
        "none_grocery": 1,
    }

    for scenario in SCENARIOS:
        card_type = scenario.get("card") or "Platinum"
        card_id = card_ids.get(card_type) or platinum_id
        card_meta = next(
            (d for d in desired_cards if d["card_type"] == card_type),
            desired_cards[0],
        )

        txn_row = {
            "user_id": user_id,
            "card_id": card_id,
            "merchant_raw": scenario["merchant_raw"],
            "merchant_normalized": scenario["merchant_normalized"],
            "amount": scenario["amount"],
            "currency": "INR",
            "transaction_date": _days_ago(int(scenario["days_ago"])),
            "mcc": scenario.get("mcc"),
            "category": scenario["category"],
            "description": scenario["description"],
        }
        tres = admin.table("transactions").insert(txn_row).execute()
        txn = (tres.data or [None])[0]
        if not txn:
            print(f"  ERROR inserting txn {scenario['key']}")
            continue
        txn["_days_ago"] = scenario["days_ago"]
        print(
            f"  Txn: {scenario['merchant_normalized']} · ₹{scenario['amount']} · "
            f"{scenario['category']}"
            + (
                " · no benefit"
                if not scenario.get("benefit")
                else f" · {scenario['benefit']['benefit_type']} "
                f"({scenario['benefit']['confidence_score']:.0%})"
            )
        )

        benefit_spec = scenario.get("benefit")
        if not benefit_spec:
            continue

        rank = conf_rank.get(scenario["key"], 0)
        created = _now() - timedelta(minutes=max(0, 40 - rank))
        is_outside = (benefit_spec.get("status") or "").lower() in (
            "not_eligible",
            "ineligible",
            "declined",
        )

        benefit_payload = {
            "transaction_id": txn["id"],
            "user_id": user_id,
            "benefit_type": benefit_spec["benefit_type"],
            "confidence_score": benefit_spec["confidence_score"],
            "status": benefit_spec["status"],
            "explanation": benefit_spec["explanation"],
            "policy_reference": benefit_spec.get("policy_reference"),
            "coverage_window_days": benefit_spec.get("coverage_window_days"),
            "max_coverage_amount": benefit_spec.get("max_coverage_amount"),
            "confidence_breakdown": benefit_spec.get("confidence_breakdown"),
            "created_at": _iso(created),
        }
        bres = admin.table("detected_benefits").insert(benefit_payload).execute()
        benefit_row = (bres.data or [None])[0]
        if not benefit_row:
            print(f"  ERROR inserting benefit for {scenario['key']}")
            continue
        if is_outside:
            outside_count += 1
        else:
            benefit_count += 1

        # Claims only for claim-eligible coverage — not for outside-coverage outcomes
        if (benefit_spec.get("status") or "").lower() not in (
            "not_eligible",
            "ineligible",
            "declined",
        ):
            benefit_spec = {**benefit_spec, "_card_type": card_type}
            prefilled = _prefill(
                user_id=user_id,
                txn=txn,
                benefit_row=benefit_spec,
                card_name=card_meta["card_name"],
                card_last_four=card_meta["last_four"],
            )
            claim_payload = {
                "detected_benefit_id": benefit_row["id"],
                "user_id": user_id,
                "status": "draft",
                "prefilled_data": prefilled,
                "missing_documents": _missing_docs(benefit_spec["benefit_type"]),
                "customer_notes": None,
                "submitted_at": None,
                "created_at": _iso(created),
            }
            admin.table("claims").insert(claim_payload).execute()

    print("\nSeed complete.")
    print(f"  Login: {SEED_EMAIL} / {SEED_PASSWORD}")
    print(f"  Cards: {len(card_ids)}")
    print(f"  Transactions: {len(SCENARIOS)}")
    print(f"  Claim-eligible detections: {benefit_count}")
    print(f"  Outside-coverage outcomes: {outside_count}")
    print("  Restart is not required if API is already running — refresh the UI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
