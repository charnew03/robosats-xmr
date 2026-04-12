from fastapi.testclient import TestClient

from backend.api import create_app
from backend.seed_auth import derive_user_id, mnemonic_to_seed_hex, normalize_mnemonic


def test_register_confirm_login_me_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ROBOSATS_XMR_JWT_SECRET", "k" * 32)
    monkeypatch.setenv("ROBOSATS_XMR_REGISTRATION_SECRET", "unit-test-registration-secret-32")
    db = str(tmp_path / "auth.db")
    client = TestClient(create_app(db_path=db, use_fake_wallet=True))

    init = client.post("/auth/register/init")
    assert init.status_code == 200
    mnemonic = init.json()["mnemonic"]
    setup_token = init.json()["setup_token"]
    assert len(mnemonic.split()) == 25

    bad = client.post(
        "/auth/register/confirm",
        json={"setup_token": setup_token, "mnemonic": "wrong words " * 25},
    )
    assert bad.status_code == 400

    ok = client.post(
        "/auth/register/confirm",
        json={"setup_token": setup_token, "mnemonic": mnemonic},
    )
    assert ok.status_code == 200
    token = ok.json()["access_token"]
    user_id = ok.json()["user_id"]
    assert user_id == derive_user_id(mnemonic_to_seed_hex(normalize_mnemonic(mnemonic)))

    dup = client.post(
        "/auth/register/confirm",
        json={"setup_token": setup_token, "mnemonic": mnemonic},
    )
    assert dup.status_code == 400

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["user_id"] == user_id

    login = client.post("/auth/login", json={"mnemonic": mnemonic})
    assert login.status_code == 200
    assert login.json()["user_id"] == user_id


def test_login_unknown_account(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ROBOSATS_XMR_JWT_SECRET", "k" * 32)
    db = str(tmp_path / "auth2.db")
    client = TestClient(create_app(db_path=db, use_fake_wallet=True))
    init = client.post("/auth/register/init")
    mnemonic = init.json()["mnemonic"]
    r = client.post("/auth/login", json={"mnemonic": mnemonic})
    assert r.status_code == 401
