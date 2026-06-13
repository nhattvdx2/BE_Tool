from fastapi.testclient import TestClient

from app.main import account_store, app


def test_verify_account(monkeypatch):
    monkeypatch.setattr(account_store, "initialize", lambda: None)
    monkeypatch.setattr(
        account_store,
        "verify_account",
        lambda username, password: username == "demo" and password == "correct-password",
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/auth/verify",
            json={"username": "demo", "password": "correct-password"},
        )

        assert response.status_code == 200
        assert response.json() == {"valid": True, "user": {"username": "demo"}}


def test_reject_invalid_password(monkeypatch):
    monkeypatch.setattr(account_store, "initialize", lambda: None)
    monkeypatch.setattr(account_store, "verify_account", lambda *_: False)

    with TestClient(app) as client:
        response = client.post(
            "/api/auth/verify",
            json={"username": "demo", "password": "wrong-password"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Username or password is invalid"
