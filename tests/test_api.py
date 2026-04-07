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
