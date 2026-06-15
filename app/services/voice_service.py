from math import ceil
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ApiError
from app.models.user import User
from app.models.voice import Voice, VoiceClone, VoiceDesign
from app.schemas.voice import (
    DesignVoiceRequest,
    GenerationMethod,
    VoiceListResponse,
    VoiceQuotaResponse,
    VoiceResponse,
)
from app.utils.files import delete_stored_file, save_audio_upload

ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a"}
ALLOWED_AUDIO_CONTENT_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/x-m4a",
}

OMNIVOICE_LANGUAGES = {"English", "Chinese"}
OMNIVOICE_GENDERS = {"Male / 男", "Female / 女"}
OMNIVOICE_AGES = {
    "Child / 儿童",
    "Young Adult / 青年",
    "Middle Aged / 中年",
    "Senior / 老年",
}
OMNIVOICE_PITCHES = {
    "Low Pitch / 低音调",
    "Moderate Pitch / 中音调",
    "High Pitch / 高音调",
}
OMNIVOICE_STYLES = {"Auto", "Calm", "Cheerful", "Serious", "Warm"}
OMNIVOICE_ENGLISH_ACCENTS = {
    "Auto",
    "American Accent / 美式口音",
    "British Accent / 英式口音",
    "Australian Accent / 澳式口音",
}
OMNIVOICE_CHINESE_DIALECTS = {
    "Auto",
    "Mandarin / 普通话",
    "Cantonese / 粤语",
    "Sichuan / 四川话",
}


def normalize_voice_name(voice_name: str) -> tuple[str, str]:
    display_name = " ".join(voice_name.split())
    if not display_name:
        raise ApiError(422, "INVALID_DESIGN_OPTIONS", "Tên giọng nói không được rỗng.")
    return display_name, display_name.casefold()


def ensure_voice_permission(user: User, method: GenerationMethod) -> None:
    allowed = (
        user.clone_voice
        if method == GenerationMethod.VOICE_CLONE
        else user.design_voice
    )
    if not user.is_active or not allowed:
        raise ApiError(403, "FORBIDDEN", "Tài khoản không có quyền tạo loại voice này.")


def get_method_limit(user: User, method: GenerationMethod) -> int:
    if method == GenerationMethod.VOICE_CLONE:
        return user.voice_clone.number_limit
    return user.voice_design.number_limit


def count_user_voices(
    db: Session, user_id: int, method: Optional[GenerationMethod] = None
) -> int:
    statement = select(func.count(Voice.id)).where(Voice.user_id == user_id)
    if method is not None:
        statement = statement.where(Voice.generation_method == method.value)
    return db.scalar(statement) or 0


def ensure_voice_quota(db: Session, user: User, method: GenerationMethod) -> None:
    limit_model = (
        VoiceClone if method == GenerationMethod.VOICE_CLONE else VoiceDesign
    )
    limit_record = db.scalar(
        select(limit_model)
        .where(limit_model.user_id == user.id)
        .with_for_update()
    )
    if limit_record is None:
        raise ApiError(
            403,
            "VOICE_LIMIT_REACHED",
            "Tài khoản chưa được cấu hình giới hạn giọng nói.",
            {"current": 0, "limit": 0, "type": method.value},
        )
    limit = limit_record.number_limit
    current = count_user_voices(db, user.id, method)
    if current >= limit:
        raise ApiError(
            403,
            "VOICE_LIMIT_REACHED",
            "Tài khoản đã đạt giới hạn số lượng giọng nói.",
            {"current": current, "limit": limit, "type": method.value},
        )


def ensure_voice_name_available(
    db: Session,
    user_id: int,
    normalized_name: str,
    exclude_voice_id: Optional[UUID] = None,
) -> None:
    statement = select(Voice.id).where(
        Voice.user_id == user_id,
        Voice.voice_name_normalized == normalized_name,
    )
    if exclude_voice_id is not None:
        statement = statement.where(Voice.id != exclude_voice_id)
    if db.scalar(statement) is not None:
        raise ApiError(409, "VOICE_NAME_EXISTS", "Tên giọng nói đã tồn tại.")


def validate_design_options(payload: DesignVoiceRequest) -> None:
    errors: dict[str, str] = {}
    option_sets = {
        "language": OMNIVOICE_LANGUAGES,
        "gender": OMNIVOICE_GENDERS,
        "age": OMNIVOICE_AGES,
        "pitch": OMNIVOICE_PITCHES,
        "style": OMNIVOICE_STYLES,
    }
    for field, allowed in option_sets.items():
        if getattr(payload, field) not in allowed:
            errors[field] = "Giá trị không được OmniVoice hỗ trợ."

    if payload.language == "English":
        if payload.english_accent not in OMNIVOICE_ENGLISH_ACCENTS:
            errors["englishAccent"] = "Bắt buộc và phải là accent được hỗ trợ."
        if payload.chinese_dialect is not None:
            errors["chineseDialect"] = "Không dùng cho ngôn ngữ English."
    elif payload.language == "Chinese":
        if payload.chinese_dialect not in OMNIVOICE_CHINESE_DIALECTS:
            errors["chineseDialect"] = "Bắt buộc và phải là dialect được hỗ trợ."
        if payload.english_accent is not None:
            errors["englishAccent"] = "Không dùng cho ngôn ngữ Chinese."

    if errors:
        raise ApiError(
            422,
            "INVALID_DESIGN_OPTIONS",
            "Tùy chọn thiết kế giọng nói không hợp lệ.",
            errors,
        )


def get_owned_voice(db: Session, user_id: int, voice_id: UUID) -> Voice:
    voice = db.scalar(
        select(Voice).where(Voice.id == voice_id, Voice.user_id == user_id)
    )
    if voice is None:
        raise ApiError(404, "VOICE_NOT_FOUND", "Không tìm thấy giọng nói.")
    return voice


def to_voice_response(voice: Voice, user_public_id: UUID) -> VoiceResponse:
    audio_url = (
        f"/api/voices/{voice.id}/audio"
        if voice.generation_method == GenerationMethod.VOICE_CLONE.value
        else None
    )
    return VoiceResponse(
        id=voice.id,
        user_id=user_public_id,
        voice_name=voice.voice_name,
        generation_method=voice.generation_method,
        created_at=voice.created_at,
        updated_at=voice.updated_at,
        original_file_name=voice.original_file_name,
        audio_url=audio_url,
        language=voice.language,
        gender=voice.gender,
        age=voice.age,
        pitch=voice.pitch,
        style=voice.style,
        english_accent=voice.english_accent,
        chinese_dialect=voice.chinese_dialect,
    )


def create_clone_voice(
    db: Session, user: User, voice_name: str, audio_file: UploadFile
) -> Voice:
    method = GenerationMethod.VOICE_CLONE
    ensure_voice_permission(user, method)
    ensure_voice_quota(db, user, method)
    display_name, normalized_name = normalize_voice_name(voice_name)
    ensure_voice_name_available(db, user.id, normalized_name)

    settings = get_settings()
    storage_key, size, content_type = save_audio_upload(
        audio_file,
        settings.upload_dir,
        user.public_id,
        ALLOWED_AUDIO_EXTENSIONS,
        ALLOWED_AUDIO_CONTENT_TYPES,
        settings.max_audio_file_size_mb * 1024 * 1024,
    )
    voice = Voice(
        user_id=user.id,
        voice_name=display_name,
        voice_name_normalized=normalized_name,
        generation_method=method.value,
        original_file_name=Path(audio_file.filename or "").name,
        storage_key=storage_key,
        audio_content_type=content_type,
        audio_size=size,
    )
    db.add(voice)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        delete_stored_file(settings.upload_dir, storage_key)
        raise ApiError(409, "VOICE_NAME_EXISTS", "Tên giọng nói đã tồn tại.") from exc
    db.refresh(voice)
    return voice


def create_design_voice(
    db: Session, user: User, payload: DesignVoiceRequest
) -> Voice:
    method = GenerationMethod.VOICE_DESIGN
    ensure_voice_permission(user, method)
    ensure_voice_quota(db, user, method)
    validate_design_options(payload)
    display_name, normalized_name = normalize_voice_name(payload.voice_name)
    ensure_voice_name_available(db, user.id, normalized_name)

    voice = Voice(
        user_id=user.id,
        voice_name=display_name,
        voice_name_normalized=normalized_name,
        generation_method=method.value,
        language=payload.language,
        gender=payload.gender,
        age=payload.age,
        pitch=payload.pitch,
        style=payload.style,
        english_accent=payload.english_accent,
        chinese_dialect=payload.chinese_dialect,
    )
    db.add(voice)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(409, "VOICE_NAME_EXISTS", "Tên giọng nói đã tồn tại.") from exc
    db.refresh(voice)
    return voice


def list_user_voices(
    db: Session,
    user: User,
    page: int,
    page_size: int,
    method: Optional[GenerationMethod],
    search: Optional[str],
) -> VoiceListResponse:
    filters = [Voice.user_id == user.id]
    if method is not None:
        filters.append(Voice.generation_method == method.value)
    if search and search.strip():
        filters.append(Voice.voice_name.ilike(f"%{search.strip()}%"))

    total = db.scalar(select(func.count(Voice.id)).where(*filters)) or 0
    voices = db.scalars(
        select(Voice)
        .where(*filters)
        .order_by(Voice.created_at.desc(), Voice.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return VoiceListResponse(
        items=[to_voice_response(voice, user.public_id) for voice in voices],
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=ceil(total / page_size) if total else 0,
    )


def rename_voice(db: Session, user: User, voice_id: UUID, voice_name: str) -> Voice:
    voice = get_owned_voice(db, user.id, voice_id)
    display_name, normalized_name = normalize_voice_name(voice_name)
    ensure_voice_name_available(db, user.id, normalized_name, voice.id)
    voice.voice_name = display_name
    voice.voice_name_normalized = normalized_name
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(409, "VOICE_NAME_EXISTS", "Tên giọng nói đã tồn tại.") from exc
    db.refresh(voice)
    return voice


def delete_voice(db: Session, user: User, voice_id: UUID) -> None:
    voice = get_owned_voice(db, user.id, voice_id)
    storage_key = voice.storage_key
    db.delete(voice)
    db.commit()
    if storage_key:
        delete_stored_file(get_settings().upload_dir, storage_key)


def get_voice_quota(
    db: Session, user: User, method: Optional[GenerationMethod]
) -> VoiceQuotaResponse:
    if method is not None:
        current = count_user_voices(db, user.id, method)
        limit = get_method_limit(user, method)
    else:
        current = count_user_voices(db, user.id)
        limit = user.voice_clone.number_limit + user.voice_design.number_limit
    return VoiceQuotaResponse(
        current=current,
        limit=limit,
        remaining=max(limit - current, 0),
    )
