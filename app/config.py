import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_path: str
    cors_origins: list[str]


def get_settings() -> Settings:
    origins = os.getenv("CORS_ORIGINS", "http://localhost:4200")
    return Settings(
        database_path=os.getenv("DATABASE_PATH", "data/accounts.sqlite3"),
        cors_origins=[origin.strip() for origin in origins.split(",") if origin.strip()],
    )
