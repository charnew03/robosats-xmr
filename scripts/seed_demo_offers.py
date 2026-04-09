#!/usr/bin/env python3
"""
Post several fake offers to a running robosats-xmr API (fake wallet or real).

Usage (API must be up, e.g. uvicorn backend.main:app --reload):
  python scripts/seed_demo_offers.py
  python scripts/seed_demo_offers.py http://127.0.0.1:8000

Uses unique maker_id per row to avoid seller open-trade limits on shared dev DBs.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


DEMO_OFFERS: list[dict] = [
    {
        "maker_id": "demo-seed-01",
        "amount_xmr": 0.25,
        "premium_pct": 1.2,
        "fiat_currency": "USD",
        "payment_method": "SEPA",
        "maker_bond_amount_xmr": 0.02,
        "taker_bond_amount_xmr": 0.02,
    },
    {
        "maker_id": "demo-seed-02",
        "amount_xmr": 0.5,
        "premium_pct": 0.0,
        "fiat_currency": "EUR",
        "payment_method": "Revolut",
        "maker_bond_amount_xmr": 0.015,
        "taker_bond_amount_xmr": 0.015,
    },
    {
        "maker_id": "demo-seed-03",
        "amount_xmr": 1.0,
        "premium_pct": -0.5,
        "fiat_currency": "GBP",
        "payment_method": "Faster Payments",
        "maker_bond_amount_xmr": 0.03,
        "taker_bond_amount_xmr": 0.03,
    },
    {
        "maker_id": "demo-seed-04",
        "amount_xmr": 0.1,
        "premium_pct": 3.5,
        "fiat_currency": "USD",
        "payment_method": "Zelle",
        "maker_bond_amount_xmr": 0.01,
        "taker_bond_amount_xmr": 0.01,
    },
    {
        "maker_id": "demo-seed-05",
        "amount_xmr": 2.5,
        "premium_pct": 2.0,
        "fiat_currency": "CAD",
        "payment_method": "Interac e-Transfer",
        "maker_bond_amount_xmr": 0.05,
        "taker_bond_amount_xmr": 0.05,
    },
]


def post_offer(base: str, payload: dict) -> dict:
    url = f"{base.rstrip('/')}/offers"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    print(f"Seeding demo offers -> {base}/offers", flush=True)
    ok = 0
    for row in DEMO_OFFERS:
        try:
            out = post_offer(base, row)
            print(f"  OK  {out['offer_id'][:8]}…  {row['amount_xmr']} XMR  {row['fiat_currency']}  {row['payment_method']}")
            ok += 1
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            print(f"  ERR {row['maker_id']}: HTTP {e.code} {body}", file=sys.stderr)
        except urllib.error.URLError as e:
            print(f"  ERR cannot reach API: {e.reason}", file=sys.stderr)
            print(
                "\n  Start the API first (in another terminal), then re-run this script:\n"
                "    cd <repo>\n"
                "    python -m pip install -r requirements-dev.txt   # if needed\n"
                "    uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000\n"
                "  Check: http://127.0.0.1:8000/health\n",
                file=sys.stderr,
            )
            return 1
    print(f"Done. Created {ok}/{len(DEMO_OFFERS)} offers. GET {base}/offers or refresh the frontend.")
    return 0 if ok == len(DEMO_OFFERS) else 2


if __name__ == "__main__":
    raise SystemExit(main())
