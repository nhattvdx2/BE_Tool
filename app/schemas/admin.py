from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.schemas.voice import GenerationMethod


class AdminDashboardResponse(BaseModel):
    total_users: int
    active_users: int
    inactive_users: int
    admin_users: int
    total_voices: int
    clone_voices: int
    design_voices: int


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    public_id: UUID
    username: str
    email: str
    clone_voice: bool
    design_voice: bool
    gen_voice: bool
    is_active: bool
    is_default: bool
    clone_limit: int
    design_limit: int
    voice_count: int
    created_at: datetime
    updated_at: datetime


class AdminUserListResponse(BaseModel):
    items: list[AdminUserResponse]
    page: int
    page_size: int
    total_items: int
    total_pages: int


class AdminCreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    is_active: bool = True
    is_default: bool = False
    clone_voice: bool = False
    design_voice: bool = True
    gen_voice: bool = True
    clone_limit: int = Field(default=0, ge=0)
    design_limit: int = Field(default=0, ge=0)


class AdminUpdateUserRequest(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    clone_voice: Optional[bool] = None
    design_voice: Optional[bool] = None
    gen_voice: Optional[bool] = None
    clone_limit: Optional[int] = Field(default=None, ge=0)
    design_limit: Optional[int] = Field(default=None, ge=0)

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        return self


class AdminResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)


class AdminVoiceResponse(BaseModel):
    id: UUID
    owner_id: int
    owner_username: str
    voice_name: str
    generation_method: GenerationMethod
    original_file_name: Optional[str] = None
    audio_size: Optional[int] = None
    language: Optional[str] = None
    gender: Optional[str] = None
    style: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AdminVoiceListResponse(BaseModel):
    items: list[AdminVoiceResponse]
    page: int
    page_size: int
    total_items: int
    total_pages: int


class AdminAuditEventResponse(BaseModel):
    timestamp: datetime
    username: str
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    method: str
    path: str
    status_code: int
    duration_ms: float
    client_ip: Optional[str] = None


class AdminAuditListResponse(BaseModel):
    items: list[AdminAuditEventResponse]
