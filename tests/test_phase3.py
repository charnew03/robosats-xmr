import sqlite3
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from backend.api import create_app
from backend.bond_service import assign_trade_bonds
from backend.fake_wallet import FakeWalletFundingRPC
from backend.repository import InMemoryTradeRepository, SQLiteTradeRepository
from backend.sweeper import run_stale_trade_sweep_loop, sweep_stale_trades
from backend.trade_engine import Trade, TradeState


@pytest.fixture
def client(tmp_path) -> TestClient:
    app = create_app(db_path=str(tmp_path / "test.db"), use_fake_wallet=True)
    return TestClient(app)


def test_assign_trade_bonds_is_idempotent() -> None:
    trade = Trade(trade_id="bond-idem-1", amount_xmr=1.0, seller_id="s")
    wallet = FakeWalletFundingRPC()
    assign_trade_bonds(trade, wallet)
    a1, b1 = trade.maker_bond_address, trade.taker_bond_address
    assign_trade_bonds(trade, wallet)
    assert trade.maker_bond_address == a1
    assert trade.taker_bond_address == b1


def test_api_assign_deposit_sets_bond_addresses_and_amounts(client: TestClient) -> None:
    r = client.post(
        "/trades",
        json={
            "amount_xmr": 2.0,
            "seller_id": "seller-bond-1",
            "maker_bond_amount_xmr": 0.05,
            "taker_bond_amount_xmr": 0.03,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["maker_bond_amount"] == 0.05
    assert body["taker_bond_amount"] == 0.03
    assert body["maker_bond_address"] is None
    trade_id = body["trade_id"]

    assign = client.post(f"/trades/{trade_id}/assign-deposit")
    assert assign.status_code == 200
    a = assign.json()
    assert a["state"] == "FUNDS_PENDING"
    assert a["deposit_address"]
    assert a["maker_bond_address"]
    assert a["taker_bond_address"]
    assert a["maker_bond_address"] != a["taker_bond_address"]
    assert a["maker_bond_address"] != a["deposit_address"]


def test_api_collaborative_cancel_before_funding(client: TestClient) -> None:
    r = client.post("/trades", json={"amount_xmr": 0.2, "seller_id": "seller-can"})
    trade_id = r.json()["trade_id"]
    cancel = client.post(
        f"/trades/{trade_id}/cancel",
        json={"actor_id": "seller-can", "reason": "changed mind"},
    )
    assert cancel.status_code == 200
    assert cancel.json()["state"] == "CANCELLED"


def test_api_collaborative_cancel_rejects_after_funded(client: TestClient) -> None:
    r = client.post("/trades", json={"amount_xmr": 0.2, "seller_id": "seller-can2"})
    trade_id = r.json()["trade_id"]
    client.post(f"/trades/{trade_id}/assign-deposit")
    client.post(f"/trades/{trade_id}/seed-confirmations", json={"confirmations": 10})
    client.post(f"/trades/{trade_id}/refresh-funding")
    bad = client.post(
        f"/trades/{trade_id}/cancel",
        json={"actor_id": "x", "reason": "too late"},
    )
    assert bad.status_code == 400


def test_sweeper_loop_respects_max_iterations() -> None:
    repo = InMemoryTradeRepository()
    stats = run_stale_trade_sweep_loop(
        repo, interval_seconds=0, max_iterations=3
    )
    assert stats.iterations == 3


def test_sweeper_sqlite_writes_audit_events(tmp_path) -> None:
    db_path = tmp_path / "sw.db"
    repo = SQLiteTradeRepository(db_path=str(db_path))
    now = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    stale = Trade(trade_id="sw1", amount_xmr=0.1, seller_id="s")
    stale.created_at = now - timedelta(hours=48)
    stale.updated_at = stale.created_at
    repo.save(stale)

    sweep_stale_trades(repo, now=now)

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT action, note FROM audit_events WHERE trade_id = ?",
            ("sw1",),
        ).fetchone()
    assert row is not None
    assert row[0] == "sweeper_cancel"
    assert "timeout" in row[1]
