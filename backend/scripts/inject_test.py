"""
Inject a live transaction and print agent pipeline output.

Usage (from backend/ with venv active):
  python scripts/inject_test.py
  python scripts/inject_test.py --merchant "SWIGGY *ORDER" --amount 450 --desc "Dinner"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"


def main() -> int:
    p = argparse.ArgumentParser(description="Inject transaction + run agents")
    p.add_argument("--email", default="demo@amex.com")
    p.add_argument("--password", default="demo1234")
    p.add_argument("--merchant", default="AMZN MKTP IN *XPS14TEST")
    p.add_argument("--amount", type=float, default=124999.0)
    p.add_argument("--desc", default="Dell XPS 14 OLED Laptop")
    p.add_argument("--category", default=None, help="Optional category hint")
    p.add_argument("--base", default=BASE)
    args = p.parse_args()

    with httpx.Client(base_url=args.base, timeout=60.0) as client:
        login = client.post(
            "/api/auth/login",
            json={"email": args.email, "password": args.password},
        )
        if login.status_code != 200:
            print("Login failed:", login.status_code, login.text)
            return 1
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "merchant_raw": args.merchant,
            "amount": args.amount,
            "description": args.desc,
            "run_detection": True,
        }
        if args.category:
            payload["category"] = args.category

        res = client.post("/api/benefits/inject", json=payload, headers=headers)
        print("Status:", res.status_code)
        data = res.json()
        print(json.dumps(data, indent=2, default=str))

        print("\n--- Quick read ---")
        print("pipeline_status:", data.get("pipeline_status"))
        print("confidence:", data.get("confidence_score"))
        intel = data.get("transaction_intelligence") or {}
        print("normalized merchant:", intel.get("merchant_normalized"))
        print("category:", intel.get("category"))
        rules = data.get("rules_decision") or {}
        print("eligible:", rules.get("eligible"), "| benefit:", rules.get("benefit"))
        if data.get("saved_benefit"):
            print("saved benefit id:", data["saved_benefit"].get("id"))
            print("→ Refresh dashboard UI to see the new detected benefit.")
        else:
            print("No benefit saved (not eligible) — expected for food/fuel etc.")
    return 0


if __name__ == "__main__":
    # Ensure backend path works if run from scripts/
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    raise SystemExit(main())
