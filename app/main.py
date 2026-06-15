import logging

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DbSession
from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import ApiError
from app.models.user import User

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Text-to-Speech and Voice Clone API",
    version="2.0.0",
)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.exception_handler(ApiError)
async def api_error_handler(_, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    if request.url.path.startswith("/api/voices"):
        code = (
            "INVALID_AUDIO_FILE"
            if request.url.path.endswith("/clone")
            else "INVALID_DESIGN_OPTIONS"
        )
        message = (
            "Dữ liệu file âm thanh không hợp lệ."
            if code == "INVALID_AUDIO_FILE"
            else "Dữ liệu voice không hợp lệ."
        )
        return JSONResponse(
            status_code=422,
            content={
                "code": code,
                "message": message,
                "details": jsonable_encoder(exc.errors()),
            },
        )
    return JSONResponse(
        status_code=422, content={"detail": jsonable_encoder(exc.errors())}
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(_, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("Database operation failed", exc_info=exc)
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Database unavailable or schema is not initialized. "
            "Run 'alembic upgrade head' on the backend server."
        },
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def readiness(db: DbSession) -> dict[str, str]:
    db.execute(select(User.id).limit(1))
    return {"status": "ready", "database": "ok", "schema": "ok"}
