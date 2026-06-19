from fastapi import APIRouter

from app.api.routes import admin, auth, voices

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(voices.router)
api_router.include_router(admin.router)
