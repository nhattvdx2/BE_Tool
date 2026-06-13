from app.database import AccountStore
from app.security import hash_password


class FakeConnection:
    def __init__(self, account=None):
        self.account = account
        self.query = ""
        self.parameters = ()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def execute(self, query, parameters=()):
        self.query = query
        self.parameters = parameters
        return self

    def fetchone(self):
        return self.account


def test_upsert_normalizes_username_and_uses_postgres_parameters(monkeypatch):
    connection = FakeConnection()
    store = AccountStore("postgresql://example")
    monkeypatch.setattr(store, "_connect", lambda: connection)

    store.upsert_account("  Demo.User  ", "password")

    assert "VALUES (%s, %s)" in connection.query
    assert connection.parameters[0] == "demo.user"


def test_verify_account_from_postgres(monkeypatch):
    connection = FakeConnection(
        {"password_hash": hash_password("correct-password"), "is_active": True}
    )
    store = AccountStore("postgresql://example")
    monkeypatch.setattr(store, "_connect", lambda: connection)

    assert store.verify_account("  Demo.User ", "correct-password") is True
    assert connection.parameters == ("demo.user",)
