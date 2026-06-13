from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import AccountStore
from app.schemas import Credentials, VerifiedUser, VerifyResponse

settings = get_settings()
account_store = AccountStore(settings.database_path)


@asynccontextmanager
async def lifespan(_: FastAPI):
    account_store.initialize()
    yield


app = FastAPI(
    title="Angular Electron Account Verification API",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/api/auth/verify",
    response_model=VerifyResponse,
    responses={401: {"description": "Username or password is invalid"}},
)
def verify_credentials(credentials: Credentials) -> VerifyResponse:
    username = credentials.username.strip()
    if not username or not account_store.verify_account(username, credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username or password is invalid",
        )

    return VerifyResponse(valid=True, user=VerifiedUser(username=username))
