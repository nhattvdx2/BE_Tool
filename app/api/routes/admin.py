from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, Response

from app.api.deps import CurrentAdmin, DbSession
from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.security import create_access_token
from app.schemas.admin import (
    AdminAuditListResponse,
    AdminCreateUserRequest,
    AdminDashboardResponse,
    AdminLoginRequest,
    AdminLoginUserResponse,
    AdminResetPasswordRequest,
    AdminUpdateUserRequest,
    AdminUserListResponse,
    AdminUserResponse,
    AdminTokenResponse,
    AdminVoiceListResponse,
    AdminVoiceResponse,
)
from app.schemas.common import MessageResponse
from app.schemas.voice import GenerationMethod, RenameVoiceRequest
from app.services import admin_service
from app.utils.files import resolve_storage_path

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/auth/login", response_model=AdminTokenResponse)
def admin_login(
    payload: AdminLoginRequest, db: DbSession, request: Request
) -> AdminTokenResponse:
    admin = admin_service.authenticate_admin(db, payload.username, payload.password)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin username or password",
        )
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is not active",
        )
    request.state.audit_username = f"admin:{admin.username}"
    request.state.audit_user_id = f"admin:{admin.id}"
    return AdminTokenResponse(
        access_token=create_access_token(admin.id, admin.username, "admin"),
        user=AdminLoginUserResponse.model_validate(admin),
    )


@router.get("/dashboard", response_model=AdminDashboardResponse)
def dashboard(db: DbSession, _: CurrentAdmin) -> AdminDashboardResponse:
    return admin_service.get_dashboard(db)


@router.get("/users", response_model=AdminUserListResponse)
def users(
    db: DbSession,
    _: CurrentAdmin,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    search: Annotated[Optional[str], Query(max_length=255)] = None,
    active: Optional[bool] = None,
) -> AdminUserListResponse:
    return admin_service.list_users(db, page, page_size, search, active)


@router.post(
    "/users", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED
)
def create_user(
    payload: AdminCreateUserRequest, db: DbSession, _: CurrentAdmin
) -> AdminUserResponse:
    return admin_service.create_user(db, payload)


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
def update_user(
    user_id: int,
    payload: AdminUpdateUserRequest,
    db: DbSession,
    _: CurrentAdmin,
) -> AdminUserResponse:
    return admin_service.update_user(db, user_id, payload)


@router.post("/users/{user_id}/reset-password", response_model=MessageResponse)
def reset_password(
    user_id: int,
    payload: AdminResetPasswordRequest,
    db: DbSession,
    _: CurrentAdmin,
) -> MessageResponse:
    admin_service.reset_user_password(db, user_id, payload.new_password)
    return MessageResponse(message="Password reset successfully")


@router.get("/voices", response_model=AdminVoiceListResponse)
def voices(
    db: DbSession,
    _: CurrentAdmin,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    method: Annotated[
        Optional[GenerationMethod], Query(alias="type")
    ] = None,
    search: Annotated[Optional[str], Query(max_length=255)] = None,
) -> AdminVoiceListResponse:
    return admin_service.list_voices(db, page, page_size, method, search)


@router.patch("/voices/{voice_id}", response_model=AdminVoiceResponse)
def update_voice(
    voice_id: UUID,
    payload: RenameVoiceRequest,
    db: DbSession,
    _: CurrentAdmin,
) -> AdminVoiceResponse:
    return admin_service.rename_voice(db, voice_id, payload.voice_name)


@router.delete("/voices/{voice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_voice(voice_id: UUID, db: DbSession, _: CurrentAdmin) -> Response:
    admin_service.delete_voice(db, voice_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/voices/{voice_id}/audio")
def voice_audio(voice_id: UUID, db: DbSession, _: CurrentAdmin) -> FileResponse:
    voice = admin_service.get_voice(db, voice_id)
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


@router.get("/audit", response_model=AdminAuditListResponse)
def audit_events(
    _: CurrentAdmin,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> AdminAuditListResponse:
    return admin_service.list_audit_events(limit)
