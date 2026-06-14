from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.models.voice import VoiceClone, VoiceDesign
from app.schemas.auth import RegisterRequest


def normalize_username(username: str) -> str:
    return username.strip().lower()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.scalar(select(User).where(User.username == normalize_username(username)))


def register_user(db: Session, payload: RegisterRequest) -> User:
    username = normalize_username(payload.username)
    email = payload.email.strip().lower()
    exists = db.scalar(
        select(User).where(or_(User.username == username, User.email == email))
    )
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists",
        )

    settings = get_settings()
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(payload.password),
        is_active=False,
        clone_voice=False,
        design_voice=False,
    )
    user.voice_clone = VoiceClone(number_limit=settings.default_clone_voice_limit)
    user.voice_design = VoiceDesign(number_limit=settings.default_design_voice_limit)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = get_user_by_username(db, username)
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def change_password(
    db: Session, user: User, current_password: str, new_password: str
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is invalid",
        )
    user.password_hash = hash_password(new_password)
    db.commit()


def has_screen_access(user: User, screenid: str) -> bool:
    screen = screenid.strip().lower()
    permissions = {
        "clone_voice": user.clone_voice,
        "voice_clone": user.clone_voice,
        "design_voice": user.design_voice,
        "voice_design": user.design_voice,
    }
    if screen not in permissions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported screenid",
        )
    return bool(user.is_active and permissions[screen])
