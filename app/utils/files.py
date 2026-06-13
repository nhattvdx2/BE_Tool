from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


def save_upload(upload: UploadFile, upload_dir: str, username: str) -> tuple[str, int]:
    suffix = Path(upload.filename or "").suffix.lower()
    safe_name = f"{uuid4().hex}{suffix}"
    target_dir = Path(upload_dir) / username
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / safe_name

    size = 0
    with target.open("wb") as output:
        while chunk := upload.file.read(1024 * 1024):
            size += len(chunk)
            output.write(chunk)
    return str(target), size
