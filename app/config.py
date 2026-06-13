import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    cors_origins: list[str]


def get_settings() -> Settings:
    origins = os.getenv("CORS_ORIGINS", "http://localhost:4200")
    return Settings(
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/be_tool",
        ),
        cors_origins=[origin.strip() for origin in origins.split(",") if origin.strip()],
    )
