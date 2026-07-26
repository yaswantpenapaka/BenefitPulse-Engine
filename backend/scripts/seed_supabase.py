"""
Seed Supabase free-tier project with demo user + Platinum card + sample txns.

Prerequisites (YOUR side):
  1. Create Supabase project
  2. Run supabase/schema.sql in SQL Editor (full file)
  3. Auth → Providers → Email enabled
  4. Auth → Settings → disable "Confirm email" for local demo
  5. backend/.env filled with URL + anon + service_role + jwt secret

Usage (from backend/ with venv):
  python scripts/seed_supabase.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# backend/ on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.services.supabase_client import get_supabase_admin


DEMO_EMAIL = "demo@amex.com"
DEMO_PASSWORD = "demo1234"
DEMO_NAME = "Priya Sharma"


def main() -> int:
    settings = get_settings()
    if not settings.has_supabase:
        print("ERROR: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing in .env")
        return 1

    admin = get_supabase_admin()
    if admin is None:
        print("ERROR: Could not create Supabase client. pip install supabase")
        return 1

    print("Creating / updating demo auth user…")
    user_id = None
    try:
        # List users and find demo
        users = admin.auth.admin.list_users()
        for u in users:
            email = getattr(u, "email", None) or (u.get("email") if isinstance(u, dict) else None)
            if email and email.lower() == DEMO_EMAIL:
                user_id = getattr(u, "id", None) or u.get("id")
                print(f"  Found existing user: {user_id}")
                break
    except Exception as e:
        print(f"  list_users note: {e}")

    if not user_id:
        try:
            created = admin.auth.admin.create_user(
                {
                    "email": DEMO_EMAIL,
                    "password": DEMO_PASSWORD,
                    "email_confirm": True,
                    "user_metadata": {"full_name": DEMO_NAME},
                }
            )
            user = created.user if hasattr(created, "user") else created
            user_id = getattr(user, "id", None) or (user.get("id") if isinstance(user, dict) else None)
            print(f"  Created user: {user_id}")
        except Exception as e:
            print(f"ERROR creating user: {e}")
            print("  Tip: disable email confirmation; check service_role key.")
            return 1

    if not user_id:
        print("ERROR: no user id")
        return 1

    # Profile
    admin.table("profiles").upsert(
        {"id": user_id, "email": DEMO_EMAIL, "full_name": DEMO_NAME}
    ).execute()
    print("  Profile upserted")

    # Card
    cards = (
        admin.table("cards").select("*").eq("user_id", user_id).execute().data or []
    )
    if cards:
        card_id = cards[0]["id"]
        print(f"  Using existing card: {card_id}")
    else:
        card = {
            "user_id": user_id,
            "card_name": "American Express Platinum",
            "card_type": "Platinum",
            "last_four": "1005",
            "is_active": True,
        }
        res = admin.table("cards").insert(card).execute()
        card_id = (res.data or [{}])[0].get("id")
        print(f"  Created card: {card_id}")

    # Sample transactions (only if few exist)
    existing_tx = (
        admin.table("transactions").select("id").eq("user_id", user_id).execute().data
        or []
    )
    if len(existing_tx) >= 4:
        print(f"  Transactions already present ({len(existing_tx)}) — skip seed txns")
    else:
        now = datetime.now(timezone.utc)
        samples = [
            ("AMZN MKTP IN *SEEDMBP", "Amazon", 142999, "Electronics", "MacBook Air M3", 20),
            ("APPLE.COM/BILL", "Apple", 89900, "Electronics", "iPhone 16 Pro", 12),
            ("INDIGO 6E-2341", "IndiGo", 12450, "Travel", "Flight BOM-DEL", 5),
            ("SWIGGY *ORDER", "Swiggy", 687, "Food & Dining", "Food delivery", 1),
        ]
        rows = []
        for raw, norm, amt, cat, desc, days in samples:
            rows.append(
                {
                    "user_id": user_id,
                    "card_id": card_id,
                    "merchant_raw": raw,
                    "merchant_normalized": norm,
                    "amount": amt,
                    "currency": "INR",
                    "transaction_date": (now - timedelta(days=days)).isoformat(),
                    "category": cat,
                    "description": desc,
                }
            )
        admin.table("transactions").insert(rows).execute()
        print(f"  Inserted {len(rows)} sample transactions")

    print("\n✓ Seed complete.")
    print(f"  Login: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    print("  Set in backend/.env:")
    print("    DEMO_MODE=false")
    print("    DATA_BACKEND=supabase")
    print("  Then restart uvicorn and open the UI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
