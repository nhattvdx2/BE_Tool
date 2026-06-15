from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


def to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(word.capitalize() for word in rest)


class GenerationMethod(str, Enum):
    VOICE_CLONE = "voice-clone"
    VOICE_DESIGN = "voice-design"


class DesignVoiceRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    voice_name: str = Field(min_length=1, max_length=150)
    language: str
    gender: str
    age: str
    pitch: str
    style: str
    english_accent: Optional[str] = None
    chinese_dialect: Optional[str] = None


class RenameVoiceRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    voice_name: str = Field(min_length=1, max_length=150)


class VoiceResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )

    id: UUID
    user_id: UUID
    voice_name: str
    generation_method: GenerationMethod
    created_at: datetime
    updated_at: datetime
    original_file_name: Optional[str] = None
    audio_url: Optional[str] = None
    language: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[str] = None
    pitch: Optional[str] = None
    style: Optional[str] = None
    english_accent: Optional[str] = None
    chinese_dialect: Optional[str] = None


class VoiceListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    items: list[VoiceResponse]
    page: int
    page_size: int
    total_items: int
    total_pages: int


class VoiceQuotaResponse(BaseModel):
    current: int
    limit: int
    remaining: int


class VoiceErrorResponse(BaseModel):
    code: str
    message: str
    details: Any = None


class VoiceLimitResponse(BaseModel):
    username: str
    screenid: str
    number_limit: int


class UploadResponse(BaseModel):
    filename: str
    path: str
    size: int
