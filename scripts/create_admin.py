import argparse
import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user_admin import UserAdmin
from app.services.auth_service import normalize_username


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update an admin account")
    parser.add_argument("username")
    parser.add_argument("--email")
    parser.add_argument("--password")
    parser.add_argument("--deactivate", action="store_true")
    args = parser.parse_args()

    username = normalize_username(args.username)
    with SessionLocal() as db:
        admin = db.scalar(select(UserAdmin).where(UserAdmin.username == username))
        password = args.password or getpass.getpass(
            "Admin password (leave blank to keep existing): "
        )
        if admin is None:
            if not args.email:
                parser.error("--email is required when creating an admin")
            if not password:
                parser.error("password is required when creating an admin")
            admin = UserAdmin(
                username=username,
                email=args.email.strip().lower(),
                password_hash=hash_password(password),
                is_active=not args.deactivate,
            )
            db.add(admin)
        else:
            if args.email:
                admin.email = args.email.strip().lower()
            if password:
                admin.password_hash = hash_password(password)
            admin.is_active = not args.deactivate
        db.commit()
        print(f"Admin account '{username}' saved.")


if __name__ == "__main__":
    main()
