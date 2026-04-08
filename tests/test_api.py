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

    client.post(f"/trades/{trade_id}/assign-deposit")
    client.post(f"/trades/{trade_id}/seed-confirmations", json={"confirmations": 10})
    funded = client.post(f"/trades/{trade_id}/refresh-funding")
    assert funded.status_code == 200
    assert funded.json()["state"] == "FUNDED"

    fiat_response = client.post(f"/trades/{trade_id}/mark-fiat-paid")
    assert fiat_response.status_code == 200
    assert fiat_response.json()["state"] == "FIAT_MARKED_PAID"

    release_response = client.post(
        f"/trades/{trade_id}/release-escrow",
        json={"buyer_payout_address": "48xmrBuyerPayoutPhase2"},
    )
    assert release_response.status_code == 200
    release_payload = release_response.json()
    assert release_payload["state"] == "RELEASED"
    assert release_payload["release_txid"]


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


def test_dispute_and_moderator_resolve_refund(client: TestClient) -> None:
    create_response = client.post(
        "/trades",
        json={
            "amount_xmr": 0.7,
            "seller_id": "seller-api-4",
            "required_confirmations": 10,
        },
    )
    trade_id = create_response.json()["trade_id"]

    client.post(f"/trades/{trade_id}/assign-deposit")
    client.post(f"/trades/{trade_id}/seed-confirmations", json={"confirmations": 10})
    client.post(f"/trades/{trade_id}/refresh-funding")

    dispute_response = client.post(
        f"/trades/{trade_id}/dispute",
        json={"reason": "buyer did not pay fiat"},
    )
    assert dispute_response.status_code == 200
    assert dispute_response.json()["state"] == "DISPUTED"

    resolve_response = client.post(
        f"/trades/{trade_id}/moderator/resolve",
        json={
            "moderator_id": "mod-1",
            "outcome": "refund",
            "address": "48xmrSellerRefund",
            "note": "refund to seller",
        },
    )
    assert resolve_response.status_code == 200
    payload = resolve_response.json()
    assert payload["state"] == "REFUNDED"
    assert payload["seller_refund_address"] == "48xmrSellerRefund"
    assert payload["refund_txid"]


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
