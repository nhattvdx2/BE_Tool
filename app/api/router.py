from fastapi import APIRouter

from app.api.routes import auth, voices

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(voices.router)
