import psycopg
from psycopg.rows import dict_row

from app.security import hash_password, verify_password


class AccountStore:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def upsert_account(self, username: str, password: str) -> None:
        normalized_username = username.strip().lower()
        password_hash = hash_password(password)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO accounts (username, password_hash)
                VALUES (%s, %s)
                ON CONFLICT(username) DO UPDATE SET
                    password_hash = excluded.password_hash,
                    is_active = TRUE,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (normalized_username, password_hash),
            )

    def verify_account(self, username: str, password: str) -> bool:
        normalized_username = username.strip().lower()
        with self._connect() as connection:
            account = connection.execute(
                "SELECT password_hash, is_active FROM accounts WHERE username = %s",
                (normalized_username,),
            ).fetchone()

        if account is None:
            return False
        return bool(account["is_active"]) and verify_password(
            password, account["password_hash"]
        )
