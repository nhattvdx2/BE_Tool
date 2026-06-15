from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import Boolean, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), default=uuid4, unique=True, index=True
    )
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    clone_voice: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    design_voice: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    gen_voice: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    voice_clone: Mapped["VoiceClone"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    voice_design: Mapped["VoiceDesign"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    voices: Mapped[list["Voice"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
