import argparse
import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User


def main() -> None:
    parser = argparse.ArgumentParser(description="Activate or update a user account")
    parser.add_argument("username")
    parser.add_argument("--password")
    parser.add_argument("--activate", action="store_true")
    parser.add_argument("--clone-voice", action="store_true")
    parser.add_argument("--design-voice", action="store_true")
    parser.add_argument("--gen-voice", action="store_true")
    parser.add_argument("--clone-limit", type=int)
    parser.add_argument("--design-limit", type=int)
    args = parser.parse_args()

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == args.username.lower()))
        if not user:
            parser.error("user does not exist; register it through the API first")
        password = args.password or getpass.getpass("New password (leave blank to keep): ")
        if password:
            user.password_hash = hash_password(password)
        if args.activate:
            user.is_active = True
        if args.clone_voice:
            user.clone_voice = True
        if args.design_voice:
            user.design_voice = True
        if args.gen_voice:
            user.gen_voice = True
        if args.clone_limit is not None:
            user.voice_clone.number_limit = args.clone_limit
        if args.design_limit is not None:
            user.voice_design.number_limit = args.design_limit
        db.commit()
        print(f"Account '{user.username}' updated.")


if __name__ == "__main__":
    main()
