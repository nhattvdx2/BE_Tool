import json
from math import ceil
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.security import hash_password
from app.models.user import User
from app.models.voice import Voice, VoiceClone, VoiceDesign
from app.schemas.admin import (
    AdminAuditEventResponse,
    AdminAuditListResponse,
    AdminCreateUserRequest,
    AdminDashboardResponse,
    AdminUpdateUserRequest,
    AdminUserListResponse,
    AdminUserResponse,
    AdminVoiceListResponse,
    AdminVoiceResponse,
)
from app.schemas.voice import GenerationMethod
from app.services.auth_service import normalize_username
from app.services.voice_service import normalize_voice_name
from app.utils.files import delete_stored_file


def get_dashboard(db: Session) -> AdminDashboardResponse:
    total_users = db.scalar(select(func.count(User.id))) or 0
    active_users = (
        db.scalar(select(func.count(User.id)).where(User.is_active.is_(True))) or 0
    )
    admin_users = (
        db.scalar(select(func.count(User.id)).where(User.is_default.is_(True))) or 0
    )
    total_voices = db.scalar(select(func.count(Voice.id))) or 0
    clone_voices = (
        db.scalar(
            select(func.count(Voice.id)).where(
                Voice.generation_method == GenerationMethod.VOICE_CLONE.value
            )
        )
        or 0
    )
    return AdminDashboardResponse(
        total_users=total_users,
        active_users=active_users,
        inactive_users=total_users - active_users,
        admin_users=admin_users,
        total_voices=total_voices,
        clone_voices=clone_voices,
        design_voices=total_voices - clone_voices,
    )


def _to_admin_user(user: User, voice_count: int = 0) -> AdminUserResponse:
    return AdminUserResponse(
        id=user.id,
        public_id=user.public_id,
        username=user.username,
        email=user.email,
        clone_voice=user.clone_voice,
        design_voice=user.design_voice,
        gen_voice=user.gen_voice,
        is_active=user.is_active,
        is_default=user.is_default,
        clone_limit=user.voice_clone.number_limit if user.voice_clone else 0,
        design_limit=user.voice_design.number_limit if user.voice_design else 0,
        voice_count=voice_count,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def list_users(
    db: Session,
    page: int,
    page_size: int,
    search: Optional[str],
    active: Optional[bool],
) -> AdminUserListResponse:
    filters = []
    if search and search.strip():
        term = f"%{search.strip()}%"
        filters.append(or_(User.username.ilike(term), User.email.ilike(term)))
    if active is not None:
        filters.append(User.is_active.is_(active))

    total = db.scalar(select(func.count(User.id)).where(*filters)) or 0
    users = db.scalars(
        select(User)
        .options(selectinload(User.voice_clone), selectinload(User.voice_design))
        .where(*filters)
        .order_by(User.created_at.desc(), User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    counts = dict(
        db.execute(
            select(Voice.user_id, func.count(Voice.id))
            .where(Voice.user_id.in_([user.id for user in users]))
            .group_by(Voice.user_id)
        ).all()
    ) if users else {}
    return AdminUserListResponse(
        items=[_to_admin_user(user, counts.get(user.id, 0)) for user in users],
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=ceil(total / page_size) if total else 0,
    )


def create_user(db: Session, payload: AdminCreateUserRequest) -> AdminUserResponse:
    username = normalize_username(payload.username)
    email = str(payload.email).strip().lower()
    if db.scalar(select(User.id).where(or_(User.username == username, User.email == email))):
        raise HTTPException(status.HTTP_409_CONFLICT, "Username or email already exists")
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(payload.password),
        is_active=payload.is_active,
        is_default=payload.is_default,
        clone_voice=payload.clone_voice,
        design_voice=payload.design_voice,
        gen_voice=payload.gen_voice,
        voice_clone=VoiceClone(number_limit=payload.clone_limit),
        voice_design=VoiceDesign(number_limit=payload.design_limit),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Username or email already exists"
        ) from exc
    db.refresh(user)
    return _to_admin_user(user)


def get_user(db: Session, user_id: int) -> User:
    user = db.scalar(
        select(User)
        .options(selectinload(User.voice_clone), selectinload(User.voice_design))
        .where(User.id == user_id)
    )
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


def update_user(
    db: Session,
    admin: User,
    user_id: int,
    payload: AdminUpdateUserRequest,
) -> AdminUserResponse:
    user = get_user(db, user_id)
    changes = payload.model_dump(exclude_unset=True)
    if user.id == admin.id and (
        changes.get("is_active") is False or changes.get("is_default") is False
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "You cannot deactivate or remove your own administrator access",
        )
    if "email" in changes:
        email = str(changes.pop("email")).strip().lower()
        duplicate = db.scalar(
            select(User.id).where(User.email == email, User.id != user.id)
        )
        if duplicate:
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already exists")
        user.email = email
    if "clone_limit" in changes:
        user.voice_clone.number_limit = changes.pop("clone_limit")
    if "design_limit" in changes:
        user.voice_design.number_limit = changes.pop("design_limit")
    for field, value in changes.items():
        setattr(user, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already exists") from exc
    db.refresh(user)
    voice_count = db.scalar(
        select(func.count(Voice.id)).where(Voice.user_id == user.id)
    ) or 0
    return _to_admin_user(user, voice_count)


def reset_user_password(db: Session, user_id: int, new_password: str) -> None:
    user = get_user(db, user_id)
    user.password_hash = hash_password(new_password)
    db.commit()


def _to_admin_voice(voice: Voice) -> AdminVoiceResponse:
    return AdminVoiceResponse(
        id=voice.id,
        owner_id=voice.user_id,
        owner_username=voice.user.username,
        voice_name=voice.voice_name,
        generation_method=voice.generation_method,
        original_file_name=voice.original_file_name,
        audio_size=voice.audio_size,
        language=voice.language,
        gender=voice.gender,
        style=voice.style,
        created_at=voice.created_at,
        updated_at=voice.updated_at,
    )


def list_voices(
    db: Session,
    page: int,
    page_size: int,
    method: Optional[GenerationMethod],
    search: Optional[str],
) -> AdminVoiceListResponse:
    filters = []
    if method is not None:
        filters.append(Voice.generation_method == method.value)
    if search and search.strip():
        term = f"%{search.strip()}%"
        filters.append(or_(Voice.voice_name.ilike(term), User.username.ilike(term)))
    total = db.scalar(
        select(func.count(Voice.id)).join(User).where(*filters)
    ) or 0
    voices = db.scalars(
        select(Voice)
        .join(User)
        .options(selectinload(Voice.user))
        .where(*filters)
        .order_by(Voice.created_at.desc(), Voice.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return AdminVoiceListResponse(
        items=[_to_admin_voice(voice) for voice in voices],
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=ceil(total / page_size) if total else 0,
    )


def get_voice(db: Session, voice_id: UUID) -> Voice:
    voice = db.scalar(
        select(Voice).options(selectinload(Voice.user)).where(Voice.id == voice_id)
    )
    if voice is None:
        raise ApiError(404, "VOICE_NOT_FOUND", "Không tìm thấy giọng nói.")
    return voice


def rename_voice(db: Session, voice_id: UUID, voice_name: str) -> AdminVoiceResponse:
    voice = get_voice(db, voice_id)
    display_name, normalized_name = normalize_voice_name(voice_name)
    duplicate = db.scalar(
        select(Voice.id).where(
            Voice.user_id == voice.user_id,
            Voice.voice_name_normalized == normalized_name,
            Voice.id != voice.id,
        )
    )
    if duplicate:
        raise ApiError(409, "VOICE_NAME_EXISTS", "Tên giọng nói đã tồn tại.")
    voice.voice_name = display_name
    voice.voice_name_normalized = normalized_name
    db.commit()
    db.refresh(voice)
    return _to_admin_voice(voice)


def delete_voice(db: Session, voice_id: UUID) -> None:
    voice = get_voice(db, voice_id)
    storage_key = voice.storage_key
    db.delete(voice)
    db.commit()
    if storage_key:
        delete_stored_file(get_settings().upload_dir, storage_key)


def list_audit_events(limit: int) -> AdminAuditListResponse:
    settings = get_settings()
    if not settings.audit_log_enabled:
        return AdminAuditListResponse(items=[])
    log_dir = Path(settings.audit_log_dir)
    events = []
    for path in log_dir.glob("*.log*") if log_dir.is_dir() else []:
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                raw = json.loads(line)
                events.append(
                    AdminAuditEventResponse(
                        timestamp=raw["timestamp"],
                        username=raw.get("username", "unknown"),
                        request_id=raw.get("requestId"),
                        user_id=raw.get("userId"),
                        method=raw.get("method", ""),
                        path=raw.get("path", ""),
                        status_code=raw.get("statusCode", 0),
                        duration_ms=raw.get("durationMs", 0),
                        client_ip=raw.get("clientIp"),
                    )
                )
        except (OSError, ValueError, KeyError):
            continue
    events.sort(key=lambda item: item.timestamp, reverse=True)
    return AdminAuditListResponse(items=events[:limit])
