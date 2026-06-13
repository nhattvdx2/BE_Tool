import sqlite3
from pathlib import Path

from app.security import hash_password, verify_password


class AccountStore:
    def __init__(self, database_path: str):
        self.database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        path = Path(self.database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    username TEXT PRIMARY KEY COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def upsert_account(self, username: str, password: str) -> None:
        password_hash = hash_password(password)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO accounts (username, password_hash)
                VALUES (?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    password_hash = excluded.password_hash,
                    is_active = 1,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (username, password_hash),
            )

    def verify_account(self, username: str, password: str) -> bool:
        with self._connect() as connection:
            account = connection.execute(
                "SELECT password_hash, is_active FROM accounts WHERE username = ?",
                (username,),
            ).fetchone()

        if account is None:
            return False
        return bool(account["is_active"]) and verify_password(
            password, account["password_hash"]
        )
