from pathlib import Path
from typing import Collection
from uuid import UUID, uuid4

from fastapi import UploadFile

from app.core.errors import ApiError


def save_audio_upload(
    upload: UploadFile,
    upload_dir: str,
    user_public_id: UUID,
    allowed_extensions: Collection[str],
    allowed_content_types: Collection[str],
    max_size_bytes: int,
) -> tuple[str, int, str]:
    suffix = Path(upload.filename or "").suffix.lower()
    content_type = (upload.content_type or "").lower()
    if suffix not in allowed_extensions or content_type not in allowed_content_types:
        raise ApiError(
            422,
            "INVALID_AUDIO_FILE",
            "File âm thanh phải có định dạng WAV, MP3 hoặc M4A.",
        )

    safe_name = f"{uuid4().hex}{suffix}"
    relative_key = Path(str(user_public_id)) / safe_name
    target_dir = Path(upload_dir) / str(user_public_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / safe_name

    size = 0
    try:
        with target.open("wb") as output:
            while chunk := upload.file.read(1024 * 1024):
                size += len(chunk)
                if size > max_size_bytes:
                    raise ApiError(
                        413,
                        "FILE_TOO_LARGE",
                        "File âm thanh vượt quá kích thước cho phép.",
                        {"maxSizeBytes": max_size_bytes},
                    )
                output.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return str(relative_key), size, content_type


def resolve_storage_path(upload_dir: str, storage_key: str) -> Path:
    root = Path(upload_dir).resolve()
    target = (root / storage_key).resolve()
    if root not in target.parents:
        raise ApiError(404, "VOICE_NOT_FOUND", "Không tìm thấy giọng nói.")
    return target


def delete_stored_file(upload_dir: str, storage_key: str) -> None:
    resolve_storage_path(upload_dir, storage_key).unlink(missing_ok=True)


def save_upload(upload: UploadFile, upload_dir: str, username: str) -> tuple[str, int]:
    target_dir = Path(upload_dir) / username
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{uuid4().hex}{Path(upload.filename or '').suffix.lower()}"
    size = 0
    with target.open("wb") as output:
        while chunk := upload.file.read(1024 * 1024):
            size += len(chunk)
            output.write(chunk)
    return str(target), size
