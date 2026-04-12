import json

from fastapi.testclient import TestClient

from backend.api import create_app


def test_escrow_defaults_to_multisig_when_env_unset(tmp_path, monkeypatch) -> None:
    """This module skips tests/conftest legacy autouse; unset env → product default."""
    monkeypatch.delenv("ROBOSATS_XMR_ESCROW_MODE", raising=False)
    client = TestClient(create_app(db_path=str(tmp_path / "default-ms.db"), use_fake_wallet=True))
    offer = client.post(
        "/offers",
        json={
            "maker_id": "m-def",
            "amount_xmr": 0.1,
            "premium_pct": 0,
            "fiat_currency": "USD",
            "payment_method": "T",
        },
    ).json()
    take = client.post(
        f"/offers/{offer['offer_id']}/take",
        json={"taker_id": "t-def"},
    ).json()
    assert take["escrow_mode"] == "MULTISIG_2OF3"
    assert (take["deposit_address"] or "").startswith("45msig2of3")


def test_take_offer_uses_multisig_when_env_set(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ROBOSATS_XMR_ESCROW_MODE", "multisig_2of3")
    db = str(tmp_path / "ms.db")
    client = TestClient(create_app(db_path=db, use_fake_wallet=True))

    offer = client.post(
        "/offers",
        json={
            "maker_id": "maker-ms-1",
            "amount_xmr": 0.2,
            "premium_pct": 0,
            "fiat_currency": "USD",
            "payment_method": "TEST",
        },
    )
    assert offer.status_code == 200
    offer_id = offer.json()["offer_id"]

    take = client.post(
        f"/offers/{offer_id}/take",
        json={"taker_id": "taker-ms-1"},
    )
    assert take.status_code == 200
    trade = take.json()
    assert trade["escrow_mode"] == "MULTISIG_2OF3"
    assert trade["deposit_address"].startswith("45msig2of3")
    info = json.loads(trade["multisig_info"])
    assert info["threshold"] == 2
    assert info["total"] == 3


def test_release_multisig_path(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ROBOSATS_XMR_ESCROW_MODE", "multisig_2of3")
    db = str(tmp_path / "ms2.db")
    client = TestClient(create_app(db_path=db, use_fake_wallet=True))

    trade_id = client.post(
        "/trades",
        json={"amount_xmr": 0.3, "seller_id": "s", "buyer_id": "b", "required_confirmations": 2},
    ).json()["trade_id"]

    client.post(f"/trades/{trade_id}/assign-deposit")
    dep = client.get(f"/trades/{trade_id}").json()["deposit_address"]
    assert dep.startswith("45msig2of3")

    client.post(f"/trades/{trade_id}/seed-confirmations", json={"confirmations": 2})
    client.post(f"/trades/{trade_id}/refresh-funding")
    client.post(f"/trades/{trade_id}/mark-fiat-paid")

    rel = client.post(
        f"/trades/{trade_id}/release",
        json={"buyer_payout_address": "48buyerpayoutaddr"},
    )
    assert rel.status_code == 200
    txid = rel.json()["release_txid"]
    assert "fake-msig2of3" in txid
