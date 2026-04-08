from fastapi.testclient import TestClient

from backend.api import app


client = TestClient(app)


def test_create_trade_endpoint() -> None:
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


def test_full_funding_flow_end_to_end() -> None:
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


def test_assign_deposit_missing_trade_returns_404() -> None:
    response = client.post("/trades/not-real/assign-deposit")
    assert response.status_code == 404


def test_get_trade_endpoint_returns_saved_trade() -> None:
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


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["db_path"]


def test_fiat_paid_and_release_flow() -> None:
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


def test_dispute_and_moderator_resolve_refund() -> None:
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
