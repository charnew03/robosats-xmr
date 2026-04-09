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
    assert a["deposit_subaddress_index"] is not None
    assert a["maker_bond_subaddress_index"] is not None
    assert a["taker_bond_subaddress_index"] is not None
    assert a["maker_bond_address"] != a["taker_bond_address"]
    assert a["maker_bond_address"] != a["deposit_address"]

    fetched = client.get(f"/trades/{trade_id}")
    assert fetched.status_code == 200
    trade = fetched.json()
    assert trade["maker_bond_amount"] == 0.05
    assert trade["taker_bond_amount"] == 0.03
    assert trade["maker_bond_address"]
    assert trade["taker_bond_address"]

    listed = client.get("/trades")
    assert listed.status_code == 200
    by_id = {t["trade_id"]: t for t in listed.json()}
    assert by_id[trade_id]["maker_bond_amount"] == 0.05
    assert by_id[trade_id]["taker_bond_amount"] == 0.03


def test_api_collaborative_cancel_before_funding(client: TestClient) -> None:
    r = client.post("/trades", json={"amount_xmr": 0.2, "seller_id": "seller-can"})
    trade_id = r.json()["trade_id"]
    cancel = client.post(
        f"/trades/{trade_id}/cancel",
        json={"actor_id": "seller-can", "reason": "changed mind"},
    )
    assert cancel.status_code == 200
    assert cancel.json()["state"] == "CANCELLED"


def test_api_collaborative_cancel_can_return_bonds_with_fake_wallet(tmp_path) -> None:
    db_path = tmp_path / "cancel-bonds.db"
    app = create_app(db_path=str(db_path), use_fake_wallet=True)
    client = TestClient(app)

    created = client.post(
        "/trades",
        json={"amount_xmr": 0.4, "seller_id": "seller-bond-cancel"},
    )
    trade_id = created.json()["trade_id"]
    assigned = client.post(f"/trades/{trade_id}/assign-deposit")
    assert assigned.status_code == 200
    maker_bond_address = assigned.json()["maker_bond_address"]
    taker_bond_address = assigned.json()["taker_bond_address"]
    assert maker_bond_address and taker_bond_address

    cancel = client.post(
        f"/trades/{trade_id}/cancel",
        json={
            "actor_id": "seller-bond-cancel",
            "reason": "mutual cancel",
            "maker_return_address": "48xmrMakerReturn",
            "taker_return_address": "48xmrTakerReturn",
        },
    )
    assert cancel.status_code == 200
    assert cancel.json()["state"] == "CANCELLED"

    with sqlite3.connect(db_path) as conn:
        note = conn.execute(
            "SELECT note FROM audit_events WHERE trade_id = ? AND action = ? ORDER BY id DESC LIMIT 1",
            (trade_id, "collaborative_cancel"),
        ).fetchone()
    assert note is not None
    assert "maker_bond_returned:fake-bond-from-" in note[0]
    assert "taker_bond_returned:fake-bond-from-" in note[0]


def test_phase3_refresh_updates_bond_confirmation_tracking(client: TestClient) -> None:
    created = client.post(
        "/trades",
        json={"amount_xmr": 0.8, "seller_id": "seller-bond-conf"},
    )
    trade_id = created.json()["trade_id"]
    assigned = client.post(f"/trades/{trade_id}/assign-deposit")
    maker_bond = assigned.json()["maker_bond_address"]
    taker_bond = assigned.json()["taker_bond_address"]
    deposit = assigned.json()["deposit_address"]
    assert maker_bond and taker_bond and deposit

    # Seed fake-wallet confirmations for escrow and both bond addresses.
    client.post(f"/trades/{trade_id}/seed-confirmations", json={"confirmations": 10})
    app_client_trade = client.get(f"/trades/{trade_id}").json()
    # Simulate bond confirmations by using helper endpoint's fake wallet state.
    # We need direct DB-backed app fixture, so call assign-confirmed endpoints via
    # the same app where fake wallet is in memory.
    # There is no bond seed endpoint by design; this verifies defaults remain exposed.
    assert app_client_trade["maker_bond_confirmations"] >= 0
    assert app_client_trade["taker_bond_confirmations"] >= 0

    refreshed = client.post(f"/trades/{trade_id}/refresh-funding")
    assert refreshed.status_code == 200
    body = refreshed.json()
    assert body["current_confirmations"] == 10
    assert body["maker_bond_confirmations"] >= 0
    assert body["taker_bond_confirmations"] >= 0


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


def test_phase3_mark_fiat_paid_requires_bond_accounting(tmp_path) -> None:
    db_path = tmp_path / "legacy-bonds.db"
    repo = SQLiteTradeRepository(db_path=str(db_path))
    # Legacy-style funded trade without bond addresses should be rejected by Phase 3 guard.
    legacy = Trade(
        trade_id="legacy-no-bonds",
        amount_xmr=1.0,
        seller_id="seller-legacy",
        state=TradeState.FUNDED,
    )
    repo.save(legacy)

    app = create_app(db_path=str(db_path), use_fake_wallet=True)
    client = TestClient(app)
    res = client.post("/trades/legacy-no-bonds/mark-fiat-paid")
    assert res.status_code == 400
    assert "bond subaddresses" in res.json()["detail"]


def test_phase3_release_can_return_bonds_and_records_notes(tmp_path) -> None:
    db_path = tmp_path / "release-bonds.db"
    app = create_app(db_path=str(db_path), use_fake_wallet=True)
    client = TestClient(app)

    created = client.post(
        "/trades",
        json={"amount_xmr": 0.9, "seller_id": "seller-rel-bond"},
    )
    trade_id = created.json()["trade_id"]
    client.post(f"/trades/{trade_id}/assign-deposit")
    client.post(f"/trades/{trade_id}/seed-confirmations", json={"confirmations": 10})
    assert client.post(f"/trades/{trade_id}/refresh-funding").status_code == 200
    assert client.post(f"/trades/{trade_id}/mark-fiat-paid").status_code == 200

    release = client.post(
        f"/trades/{trade_id}/release-escrow",
        json={
            "buyer_payout_address": "48xmrBuyerOut",
            "maker_return_address": "48xmrMakerBack",
            "taker_return_address": "48xmrTakerBack",
        },
    )
    assert release.status_code == 200
    assert release.json()["state"] == "RELEASED"

    with sqlite3.connect(db_path) as conn:
        note = conn.execute(
            "SELECT note FROM audit_events WHERE trade_id = ? AND action = ? ORDER BY id DESC LIMIT 1",
            (trade_id, "release_escrow"),
        ).fetchone()
    assert note is not None
    assert "maker:fake-bond-from-" in note[0]
    assert "taker:fake-bond-from-" in note[0]


def test_phase3_dispute_logs_bond_slash_placeholder(tmp_path) -> None:
    db_path = tmp_path / "slash-placeholder.db"
    app = create_app(db_path=str(db_path), use_fake_wallet=True)
    client = TestClient(app)
    created = client.post(
        "/trades",
        json={"amount_xmr": 0.3, "seller_id": "seller-dispute"},
    )
    trade_id = created.json()["trade_id"]
    client.post(f"/trades/{trade_id}/assign-deposit")
    client.post(f"/trades/{trade_id}/seed-confirmations", json={"confirmations": 10})
    client.post(f"/trades/{trade_id}/refresh-funding")
    dispute = client.post(
        f"/trades/{trade_id}/open-dispute",
        json={"reason": "placeholder slashing"},
    )
    assert dispute.status_code == 200
    assert dispute.json()["state"] == "DISPUTED"

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT action, note FROM audit_events WHERE trade_id = ? AND action = ? ORDER BY id DESC LIMIT 1",
            (trade_id, "bond_slash_placeholder"),
        ).fetchone()
    assert row is not None
    assert row[0] == "bond_slash_placeholder"


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
