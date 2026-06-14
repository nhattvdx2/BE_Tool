from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    email: EmailStr


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class AcceptFunctionRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    screenid: str = Field(min_length=1, max_length=50)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    clone_voice: bool
    design_voice: bool
    is_active: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime


class LoginUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    clone_voice: bool
    design_voice: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: LoginUserResponse


class FunctionAccessResponse(BaseModel):
    username: str
    screenid: str
    allowed: bool
