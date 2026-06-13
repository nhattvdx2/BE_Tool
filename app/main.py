import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DbSession
from app.api.router import api_router
from app.core.config import get_settings
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
