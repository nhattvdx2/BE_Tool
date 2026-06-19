import hashlib
import json
import logging
import re
from collections import OrderedDict
from datetime import datetime, timezone
from functools import lru_cache
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Lock
from typing import Any

from app.core.config import get_settings

SAFE_FILENAME = re.compile(r"[^a-zA-Z0-9_.-]+")
MAX_OPEN_HANDLERS = 100
logger = logging.getLogger(__name__)


class AuditLogger:
    def __init__(
        self,
        log_dir: str,
        max_bytes: int,
        backup_count: int,
    ):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self._handlers: OrderedDict[str, RotatingFileHandler] = OrderedDict()
        self._lock = Lock()

    def _filename(self, username: str) -> str:
        identity = username.strip() or "anonymous"
        slug = SAFE_FILENAME.sub("_", identity).strip("._") or "user"
        digest = hashlib.sha256(identity.encode()).hexdigest()[:10]
        return f"{slug[:80]}_{digest}.log"

    def _get_handler(self, username: str) -> RotatingFileHandler:
        filename = self._filename(username)
        handler = self._handlers.pop(filename, None)
        if handler is None:
            handler = RotatingFileHandler(
                self.log_dir / filename,
                maxBytes=self.max_bytes,
                backupCount=self.backup_count,
                encoding="utf-8",
            )
            handler.setFormatter(logging.Formatter("%(message)s"))
        self._handlers[filename] = handler

        if len(self._handlers) > MAX_OPEN_HANDLERS:
            _, oldest = self._handlers.popitem(last=False)
            oldest.close()
        return handler

    def write(self, username: str, event: dict[str, Any]) -> None:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "username": username,
            **event,
        }
        record = logging.LogRecord(
            name="audit",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            args=(),
            exc_info=None,
        )
        with self._lock:
            self._get_handler(username).emit(record)

    def close(self) -> None:
        with self._lock:
            for handler in self._handlers.values():
                handler.close()
            self._handlers.clear()


@lru_cache
def get_audit_logger() -> AuditLogger:
    settings = get_settings()
    return AuditLogger(
        settings.audit_log_dir,
        settings.audit_log_max_bytes,
        settings.audit_log_backup_count,
    )


def write_audit_event(username: str, event: dict[str, Any]) -> None:
    try:
        if get_settings().audit_log_enabled:
            get_audit_logger().write(username, event)
    except Exception:
        logger.exception("Could not write audit log")
