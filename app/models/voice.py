from __future__ import annotations

from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class VoiceClone(TimestampMixin, Base):
    __tablename__ = "voice_clones"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    number_limit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped["User"] = relationship(back_populates="voice_clone")


class VoiceDesign(TimestampMixin, Base):
    __tablename__ = "voice_designs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    number_limit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped["User"] = relationship(back_populates="voice_design")


class Voice(TimestampMixin, Base):
    __tablename__ = "voices"
    __table_args__ = (
        CheckConstraint(
            "generation_method IN ('voice-clone', 'voice-design')",
            name="ck_voices_generation_method",
        ),
        UniqueConstraint(
            "user_id",
            "voice_name_normalized",
            name="uq_voices_user_name_normalized",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    voice_name: Mapped[str] = mapped_column(String(150))
    voice_name_normalized: Mapped[str] = mapped_column(String(150))
    generation_method: Mapped[str] = mapped_column(String(30), index=True)

    original_file_name: Mapped[Optional[str]] = mapped_column(String(255))
    storage_key: Mapped[Optional[str]] = mapped_column(String(500))
    audio_content_type: Mapped[Optional[str]] = mapped_column(String(100))
    audio_size: Mapped[Optional[int]] = mapped_column(Integer)

    language: Mapped[Optional[str]] = mapped_column(String(50))
    gender: Mapped[Optional[str]] = mapped_column(String(50))
    age: Mapped[Optional[str]] = mapped_column(String(50))
    pitch: Mapped[Optional[str]] = mapped_column(String(80))
    style: Mapped[Optional[str]] = mapped_column(String(80))
    english_accent: Mapped[Optional[str]] = mapped_column(String(100))
    chinese_dialect: Mapped[Optional[str]] = mapped_column(String(100))
    provider_metadata: Mapped[Optional[str]] = mapped_column(Text)

    user: Mapped["User"] = relationship(back_populates="voices")
