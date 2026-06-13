from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    database_url: str = "postgresql://postgres:postgres@localhost:5432/be_tool"
    cors_origins: str = "http://localhost:4200"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    upload_dir: str = "uploads"
    default_clone_voice_limit: int = 0
    default_design_voice_limit: int = 0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
