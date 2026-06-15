from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, File, Form, Query, UploadFile
from fastapi.responses import FileResponse, Response

from app.api.deps import CurrentVoiceUser, DbSession
from app.core.config import get_settings
from app.core.errors import ApiError
from app.schemas.voice import (
    DesignVoiceRequest,
    GenerationMethod,
    RenameVoiceRequest,
    VoiceListResponse,
    VoiceQuotaResponse,
    VoiceResponse,
)
from app.services.voice_service import (
    create_clone_voice,
    create_design_voice,
    delete_voice,
    get_owned_voice,
    get_voice_quota,
    list_user_voices,
    rename_voice,
    to_voice_response,
)
from app.utils.files import resolve_storage_path

router = APIRouter(prefix="/voices", tags=["voices"])


@router.post("/clone", response_model=VoiceResponse)
def clone_voice(
    db: DbSession,
    current_user: CurrentVoiceUser,
    voice_name: str = Form(alias="voiceName"),
    audio_file: UploadFile = File(alias="audioFile"),
) -> VoiceResponse:
    voice = create_clone_voice(db, current_user, voice_name, audio_file)
    return to_voice_response(voice, current_user.public_id)


@router.post("/design", response_model=VoiceResponse)
def design_voice(
    payload: DesignVoiceRequest,
    db: DbSession,
    current_user: CurrentVoiceUser,
) -> VoiceResponse:
    voice = create_design_voice(db, current_user, payload)
    return to_voice_response(voice, current_user.public_id)


@router.get("", response_model=VoiceListResponse)
def list_voices(
    db: DbSession,
    current_user: CurrentVoiceUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 10,
    method: Annotated[
        Optional[GenerationMethod], Query(alias="type")
    ] = None,
    search: Annotated[Optional[str], Query(max_length=150)] = None,
) -> VoiceListResponse:
    return list_user_voices(db, current_user, page, page_size, method, search)


@router.get("/limit", response_model=VoiceQuotaResponse)
def voice_limit(
    db: DbSession,
    current_user: CurrentVoiceUser,
    method: Annotated[
        Optional[GenerationMethod], Query(alias="type")
    ] = None,
) -> VoiceQuotaResponse:
    return get_voice_quota(db, current_user, method)


@router.get("/{voice_id}", response_model=VoiceResponse)
def voice_detail(
    voice_id: UUID, db: DbSession, current_user: CurrentVoiceUser
) -> VoiceResponse:
    voice = get_owned_voice(db, current_user.id, voice_id)
    return to_voice_response(voice, current_user.public_id)


@router.patch("/{voice_id}", response_model=VoiceResponse)
def update_voice(
    voice_id: UUID,
    payload: RenameVoiceRequest,
    db: DbSession,
    current_user: CurrentVoiceUser,
) -> VoiceResponse:
    voice = rename_voice(db, current_user, voice_id, payload.voice_name)
    return to_voice_response(voice, current_user.public_id)


@router.delete("/{voice_id}", status_code=204)
def remove_voice(
    voice_id: UUID, db: DbSession, current_user: CurrentVoiceUser
) -> Response:
    delete_voice(db, current_user, voice_id)
    return Response(status_code=204)


@router.get("/{voice_id}/audio")
def voice_audio(
    voice_id: UUID, db: DbSession, current_user: CurrentVoiceUser
) -> FileResponse:
    voice = get_owned_voice(db, current_user.id, voice_id)
    if voice.generation_method != GenerationMethod.VOICE_CLONE.value or not voice.storage_key:
        raise ApiError(404, "VOICE_NOT_FOUND", "Không tìm thấy file âm thanh.")

    path = resolve_storage_path(get_settings().upload_dir, voice.storage_key)
    if not path.is_file():
        raise ApiError(404, "VOICE_NOT_FOUND", "Không tìm thấy file âm thanh.")
    return FileResponse(
        path,
        media_type=voice.audio_content_type or "application/octet-stream",
        filename=voice.original_file_name,
    )
