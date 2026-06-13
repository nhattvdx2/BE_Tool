from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.schemas.voice import UploadResponse, VoiceLimitResponse
from app.services.auth_service import get_user_by_username, has_screen_access
from app.services.voice_service import get_number_limit
from app.utils.files import save_upload

router = APIRouter(prefix="/voices", tags=["voices"])


def get_requested_user(db: DbSession, current_user: CurrentUser, username: str):
    user = get_user_by_username(db, username)
    if not user or (user.id != current_user.id and not current_user.is_default):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return user


@router.get("/numberLimit", response_model=VoiceLimitResponse)
def number_limit(
    db: DbSession,
    current_user: CurrentUser,
    screenid: Annotated[str, Query(min_length=1, max_length=50)],
    username: Annotated[str, Query(min_length=1, max_length=100)],
) -> VoiceLimitResponse:
    user = get_requested_user(db, current_user, username)
    return VoiceLimitResponse(
        username=user.username,
        screenid=screenid,
        number_limit=get_number_limit(user, screenid),
    )


@router.post("/upload", response_model=UploadResponse)
def upload_voice_file(
    current_user: CurrentUser,
    screenid: Annotated[str, Form()],
    upload: Annotated[UploadFile, File()],
) -> UploadResponse:
    if not has_screen_access(current_user, screenid):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to this screen",
        )
    path, size = save_upload(
        upload, get_settings().upload_dir, current_user.username
    )
    return UploadResponse(filename=upload.filename or "", path=path, size=size)
