from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import CurrentUser, DbSession
from app.core.security import create_access_token
from app.schemas.auth import (
    AcceptFunctionRequest,
    ChangePasswordRequest,
    FunctionAccessResponse,
    LoginUserResponse,
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
def register(payload: RegisterRequest, db: DbSession, request: Request) -> UserResponse:
    user = register_user(db, payload)
    request.state.audit_username = user.username
    request.state.audit_user_id = str(user.public_id)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DbSession, request: Request) -> TokenResponse:
    user = authenticate_user(db, payload.username, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active",
        )
    request.state.audit_username = user.username
    request.state.audit_user_id = str(user.public_id)
    return TokenResponse(
        access_token=create_access_token(user.id, user.username),
        user=LoginUserResponse.model_validate(user),
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
    if not user or user.id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return FunctionAccessResponse(
        username=user.username,
        screenid=payload.screenid,
        allowed=has_screen_access(user, payload.screenid),
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: CurrentUser) -> UserResponse:
    return current_user
