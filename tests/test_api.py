from fastapi.testclient import TestClient
import pytest

from backend.api import create_app


@pytest.fixture
def client(tmp_path) -> TestClient:
    app = create_app(db_path=str(tmp_path / "test.db"), use_fake_wallet=True)
    return TestClient(app)


def test_create_trade_endpoint(client: TestClient) -> None:
    response = client.post(
        "/trades",
        json={
            "amount_xmr": 0.45,
            "seller_id": "seller-api-1",
            "required_confirmations": 10,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["state"] == "CREATED"
    assert payload["amount_xmr"] == 0.45
    assert payload["seller_id"] == "seller-api-1"


def test_full_funding_flow_end_to_end(client: TestClient) -> None:
    create_response = client.post(
        "/trades",
        json={
            "amount_xmr": 1.0,
            "seller_id": "seller-api-2",
            "required_confirmations": 10,
        },
    )
    trade_id = create_response.json()["trade_id"]

    assign_response = client.post(f"/trades/{trade_id}/assign-deposit")
    assert assign_response.status_code == 200
    assert assign_response.json()["state"] == "FUNDS_PENDING"
    assert assign_response.json()["deposit_address"] is not None

    seed_response = client.post(
        f"/trades/{trade_id}/seed-confirmations",
        json={"confirmations": 10},
    )
    assert seed_response.status_code == 200

    refresh_response = client.post(f"/trades/{trade_id}/refresh-funding")
    assert refresh_response.status_code == 200
    assert refresh_response.json()["state"] == "FUNDED"
    assert refresh_response.json()["current_confirmations"] == 10

    # Re-refresh should be stable and return the same funded status.
    refresh_again = client.post(f"/trades/{trade_id}/refresh-funding")
    assert refresh_again.status_code == 200
    assert refresh_again.json()["state"] == "FUNDED"
    assert refresh_again.json()["current_confirmations"] == 10


def test_assign_deposit_missing_trade_returns_404(client: TestClient) -> None:
    response = client.post("/trades/not-real/assign-deposit")
    assert response.status_code == 404


def test_get_trade_endpoint_returns_saved_trade(client: TestClient) -> None:
    create_response = client.post(
        "/trades",
        json={
            "amount_xmr": 0.22,
            "seller_id": "seller-get-1",
            "required_confirmations": 10,
        },
    )
    trade_id = create_response.json()["trade_id"]

    get_response = client.get(f"/trades/{trade_id}")
    assert get_response.status_code == 200
    payload = get_response.json()
    assert payload["trade_id"] == trade_id
    assert payload["state"] == "CREATED"


def test_get_trade_missing_trade_returns_404(client: TestClient) -> None:
    response = client.get("/trades/not-real")
    assert response.status_code == 404


def test_list_trades_endpoint_returns_created_trades(client: TestClient) -> None:
    first = client.post(
        "/trades",
        json={"amount_xmr": 0.31, "seller_id": "seller-list-1", "required_confirmations": 10},
    )
    second = client.post(
        "/trades",
        json={"amount_xmr": 0.32, "seller_id": "seller-list-2", "required_confirmations": 10},
    )
    assert first.status_code == 200
    assert second.status_code == 200

    response = client.get("/trades")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)

    returned_ids = {trade["trade_id"] for trade in payload}
    assert first.json()["trade_id"] in returned_ids
    assert second.json()["trade_id"] in returned_ids


def test_health_endpoint_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["db_path"]


def test_fiat_paid_and_release_flow(client: TestClient) -> None:
    create_response = client.post(
        "/trades",
        json={
            "amount_xmr": 0.5,
            "seller_id": "seller-api-3",
            "required_confirmations": 10,
        },
    )
    trade_id = create_response.json()["trade_id"]

    client.post(f"/trades/{trade_id}/assign-deposit")
    client.post(f"/trades/{trade_id}/seed-confirmations", json={"confirmations": 10})
    client.post(f"/trades/{trade_id}/refresh-funding")

    fiat_response = client.post(f"/trades/{trade_id}/mark-fiat-paid")
    assert fiat_response.status_code == 200
    assert fiat_response.json()["state"] == "FIAT_MARKED_PAID"

    release_response = client.post(
        f"/trades/{trade_id}/release",
        json={"buyer_payout_address": "48xmrBuyerPayout"},
    )
    assert release_response.status_code == 200
    payload = release_response.json()
    assert payload["state"] == "RELEASED"
    assert payload["buyer_payout_address"] == "48xmrBuyerPayout"
    assert payload["release_txid"]


def test_phase2_happy_path_with_new_endpoint_names(client: TestClient) -> None:
    create_response = client.post(
        "/trades",
        json={
            "amount_xmr": 0.6,
            "seller_id": "seller-phase2-1",
            "buyer_id": "buyer-phase2-1",
            "required_confirmations": 10,
        },
    )
    trade_id = create_response.json()["trade_id"]

    assign = client.post(f"/trades/{trade_id}/assign-deposit")
    assert assign.status_code == 200
    deposit_address = assign.json()["deposit_address"]
    assert deposit_address

    client.post(f"/trades/{trade_id}/seed-confirmations", json={"confirmations": 10})
    funded = client.post(f"/trades/{trade_id}/refresh-funding")
    assert funded.status_code == 200
    assert funded.json()["state"] == "FUNDED"

    fiat_response = client.post(f"/trades/{trade_id}/mark-fiat-paid")
    assert fiat_response.status_code == 200
    assert fiat_response.json()["state"] == "FIAT_MARKED_PAID"

    buyer_payout = "48xmrBuyerPayoutPhase2"
    release_response = client.post(
        f"/trades/{trade_id}/release-escrow",
        json={"buyer_payout_address": buyer_payout},
    )
    assert release_response.status_code == 200
    release_payload = release_response.json()
    assert release_payload["state"] == "RELEASED"
    txid = release_payload["release_txid"]
    assert txid
    assert deposit_address[:16] in txid
    assert buyer_payout[:12] in txid
    assert "0.6" in txid

    persisted = client.get(f"/trades/{trade_id}")
    assert persisted.status_code == 200
    body = persisted.json()
    assert body["state"] == "RELEASED"
    assert body["release_txid"] == txid
    assert body["buyer_payout_address"] == buyer_payout


def test_phase2_open_dispute_freezes_trade(client: TestClient) -> None:
    create_response = client.post(
        "/trades",
        json={
            "amount_xmr": 0.4,
            "seller_id": "seller-phase2-2",
            "buyer_id": "buyer-phase2-2",
            "required_confirmations": 10,
        },
    )
    trade_id = create_response.json()["trade_id"]

    client.post(f"/trades/{trade_id}/assign-deposit")
    client.post(f"/trades/{trade_id}/seed-confirmations", json={"confirmations": 10})
    funded = client.post(f"/trades/{trade_id}/refresh-funding")
    assert funded.status_code == 200
    assert funded.json()["state"] == "FUNDED"

    dispute_response = client.post(
        f"/trades/{trade_id}/open-dispute",
        json={"reason": "payment mismatch"},
    )
    assert dispute_response.status_code == 200
    payload = dispute_response.json()
    assert payload["state"] == "DISPUTED"
    assert payload["dispute_reason"] == "payment mismatch"

    blocked_fiat = client.post(f"/trades/{trade_id}/mark-fiat-paid")
    assert blocked_fiat.status_code == 400

    blocked_release = client.post(
        f"/trades/{trade_id}/release-escrow",
        json={"buyer_payout_address": "48xmrBuyerBlocked"},
    )
    assert blocked_release.status_code == 400


def test_phase2_open_dispute_from_fiat_marked_paid_freezes_trade(client: TestClient) -> None:
    create_response = client.post(
        "/trades",
        json={
            "amount_xmr": 0.55,
            "seller_id": "seller-phase2-fiat-dispute",
            "required_confirmations": 10,
        },
    )
    trade_id = create_response.json()["trade_id"]
    client.post(f"/trades/{trade_id}/assign-deposit")
    client.post(f"/trades/{trade_id}/seed-confirmations", json={"confirmations": 10})
    client.post(f"/trades/{trade_id}/refresh-funding")
    client.post(f"/trades/{trade_id}/mark-fiat-paid")

    dispute_response = client.post(
        f"/trades/{trade_id}/open-dispute",
        json={"reason": "fiat issue"},
    )
    assert dispute_response.status_code == 200
    assert dispute_response.json()["state"] == "DISPUTED"

    assert client.post(f"/trades/{trade_id}/release-escrow", json={"buyer_payout_address": "48xmrX"}).status_code == 400


def test_phase2_cannot_open_dispute_twice(client: TestClient) -> None:
    create_response = client.post(
        "/trades",
        json={"amount_xmr": 0.33, "seller_id": "seller-phase2-dup", "required_confirmations": 10},
    )
    trade_id = create_response.json()["trade_id"]
    client.post(f"/trades/{trade_id}/assign-deposit")
    client.post(f"/trades/{trade_id}/seed-confirmations", json={"confirmations": 10})
    client.post(f"/trades/{trade_id}/refresh-funding")
    assert (
        client.post(
            f"/trades/{trade_id}/open-dispute",
            json={"reason": "first"},
        ).status_code
        == 200
    )
    dup = client.post(
        f"/trades/{trade_id}/open-dispute",
        json={"reason": "second"},
    )
    assert dup.status_code == 400
    assert "already DISPUTED" in dup.json()["detail"]


def test_phase2_invalid_transitions_return_400(client: TestClient) -> None:
    create_response = client.post(
        "/trades",
        json={"amount_xmr": 0.25, "seller_id": "seller-phase2-inv", "required_confirmations": 10},
    )
    trade_id = create_response.json()["trade_id"]

    # CREATED: cannot mark fiat or release.
    assert client.post(f"/trades/{trade_id}/mark-fiat-paid").status_code == 400
    assert (
        client.post(
            f"/trades/{trade_id}/release-escrow",
            json={"buyer_payout_address": "48xmrBuyer"},
        ).status_code
        == 400
    )

    client.post(f"/trades/{trade_id}/assign-deposit")
    # FUNDS_PENDING: cannot mark fiat or release.
    assert client.post(f"/trades/{trade_id}/mark-fiat-paid").status_code == 400
    assert (
        client.post(
            f"/trades/{trade_id}/release-escrow",
            json={"buyer_payout_address": "48xmrBuyer"},
        ).status_code
        == 400
    )

    client.post(f"/trades/{trade_id}/seed-confirmations", json={"confirmations": 10})
    client.post(f"/trades/{trade_id}/refresh-funding")
    # FUNDED: cannot release before fiat marked.
    assert (
        client.post(
            f"/trades/{trade_id}/release-escrow",
            json={"buyer_payout_address": "48xmrBuyer"},
        ).status_code
        == 400
    )

    client.post(f"/trades/{trade_id}/mark-fiat-paid")
    # FIAT_MARKED_PAID: cannot mark fiat again.
    assert client.post(f"/trades/{trade_id}/mark-fiat-paid").status_code == 400

    client.post(
        f"/trades/{trade_id}/release-escrow",
        json={"buyer_payout_address": "48xmrBuyerFinal"},
    )
    # RELEASED: no further settlement.
    assert client.post(f"/trades/{trade_id}/mark-fiat-paid").status_code == 400
    assert (
        client.post(
            f"/trades/{trade_id}/release-escrow",
            json={"buyer_payout_address": "48xmrBuyer2"},
        ).status_code
        == 400
    )
    assert (
        client.post(f"/trades/{trade_id}/open-dispute", json={"reason": "late"}).status_code
        == 400
    )


def test_create_trade_enforces_open_trade_limit_per_seller(client: TestClient) -> None:
    for _ in range(3):
        r = client.post(
            "/trades",
            json={
                "amount_xmr": 0.1,
                "seller_id": "seller-limit-1",
                "required_confirmations": 10,
            },
        )
        assert r.status_code == 200

    blocked = client.post(
        "/trades",
        json={
            "amount_xmr": 0.1,
            "seller_id": "seller-limit-1",
            "required_confirmations": 10,
        },
    )
    assert blocked.status_code == 400


def test_offer_create_list_and_take_flow(client: TestClient) -> None:
    created_offer = client.post(
        "/offers",
        json={
            "maker_id": "maker-offer-1",
            "amount_xmr": 0.75,
            "premium_pct": 1.5,
            "fiat_currency": "USD",
            "payment_method": "SEPA",
            "maker_bond_amount_xmr": 0.07,
            "taker_bond_amount_xmr": 0.04,
        },
    )
    assert created_offer.status_code == 200
    offer = created_offer.json()
    offer_id = offer["offer_id"]
    assert offer["is_active"] is True
    assert offer["fiat_currency"] == "USD"
    assert offer["maker_bond_amount"] == 0.07
    assert offer["taker_bond_amount"] == 0.04

    offers_list = client.get("/offers")
    assert offers_list.status_code == 200
    offer_ids = {o["offer_id"] for o in offers_list.json()}
    assert offer_id in offer_ids

    take = client.post(
        f"/offers/{offer_id}/take",
        json={"taker_id": "taker-offer-1"},
    )
    assert take.status_code == 200
    trade = take.json()
    assert trade["seller_id"] == "maker-offer-1"
    assert trade["buyer_id"] == "taker-offer-1"
    assert trade["state"] == "FUNDS_PENDING"
    assert trade["deposit_address"] is not None
    assert trade["maker_bond_address"] is not None
    assert trade["taker_bond_address"] is not None
    assert trade["maker_bond_amount"] == 0.07
    assert trade["taker_bond_amount"] == 0.04

    offers_after_take = client.get("/offers")
    assert offers_after_take.status_code == 200
    offer_ids_after = {o["offer_id"] for o in offers_after_take.json()}
    assert offer_id not in offer_ids_after


def test_take_offer_rejects_inactive_offer(client: TestClient) -> None:
    created_offer = client.post(
        "/offers",
        json={
            "maker_id": "maker-offer-2",
            "amount_xmr": 0.2,
            "premium_pct": 0.5,
            "fiat_currency": "EUR",
            "payment_method": "REVOLUT",
        },
    )
    offer_id = created_offer.json()["offer_id"]

    first_take = client.post(
        f"/offers/{offer_id}/take",
        json={"taker_id": "taker-offer-2"},
    )
    assert first_take.status_code == 200

    second_take = client.post(
        f"/offers/{offer_id}/take",
        json={"taker_id": "taker-offer-3"},
    )
    assert second_take.status_code == 400


def test_offer_creation_enforces_seller_risk_limit(client: TestClient) -> None:
    for _ in range(3):
        made = client.post(
            "/trades",
            json={
                "amount_xmr": 0.2,
                "seller_id": "maker-risk-limited",
                "required_confirmations": 10,
            },
        )
        assert made.status_code == 200

    blocked_offer = client.post(
        "/offers",
        json={
            "maker_id": "maker-risk-limited",
            "amount_xmr": 0.15,
            "premium_pct": 1.0,
            "fiat_currency": "USD",
            "payment_method": "SEPA",
        },
    )
    assert blocked_offer.status_code == 400
