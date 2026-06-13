from fastapi.testclient import TestClient

from app.main import account_store, app


def test_verify_account(tmp_path):
    account_store.database_path = str(tmp_path / "accounts.sqlite3")

    with TestClient(app) as client:
        account_store.upsert_account("demo", "correct-password")

        response = client.post(
            "/api/auth/verify",
            json={"username": "demo", "password": "correct-password"},
        )

        assert response.status_code == 200
        assert response.json() == {"valid": True, "user": {"username": "demo"}}


def test_reject_invalid_password(tmp_path):
    account_store.database_path = str(tmp_path / "accounts.sqlite3")

    with TestClient(app) as client:
        account_store.upsert_account("demo", "correct-password")

        response = client.post(
            "/api/auth/verify",
            json={"username": "demo", "password": "wrong-password"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Username or password is invalid"
