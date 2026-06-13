import argparse
import getpass

from app.config import get_settings
from app.database import AccountStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update an account")
    parser.add_argument("username", help="Account username")
    parser.add_argument("--password", help="Password; omit to enter it securely")
    args = parser.parse_args()

    username = args.username.strip()
    if not username:
        parser.error("username cannot be empty")

    password = args.password or getpass.getpass("Password: ")
    if not password:
        parser.error("password cannot be empty")

    store = AccountStore(get_settings().database_path)
    store.initialize()
    store.upsert_account(username, password)
    print(f"Account '{username}' is ready.")


if __name__ == "__main__":
    main()
