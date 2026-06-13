from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.core.security import create_access_token
from app.schemas.auth import (
    AcceptFunctionRequest,
    ChangePasswordRequest,
    FunctionAccessResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.common import MessageResponse
from app.services.auth_service import (
    authenticate_user,
    change_password,
    get_user_by_username,
    has_screen_access,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_200_OK)
def register(payload: RegisterRequest, db: DbSession) -> UserResponse:
    return register_user(db, payload)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    user = authenticate_user(db, payload.username, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials or inactive account",
        )
    return TokenResponse(
        access_token=create_access_token(user.id, user.username),
        user=UserResponse.model_validate(user),
    )


@router.post("/changepassword", response_model=MessageResponse)
def change_user_password(
    payload: ChangePasswordRequest, current_user: CurrentUser, db: DbSession
) -> MessageResponse:
    change_password(db, current_user, payload.current_password, payload.new_password)
    return MessageResponse(message="Password changed successfully")


@router.post("/acceptFuntion", response_model=FunctionAccessResponse)
def accept_function(
    payload: AcceptFunctionRequest, current_user: CurrentUser, db: DbSession
) -> FunctionAccessResponse:
    user = get_user_by_username(db, payload.username)
    if not user or (user.id != current_user.id and not current_user.is_default):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return FunctionAccessResponse(
        username=user.username,
        screenid=payload.screenid,
        allowed=has_screen_access(user, payload.screenid),
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: CurrentUser) -> UserResponse:
    return current_user
