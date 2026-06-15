"""Add user public UUID and per-account voice library."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260615_03"
down_revision = "20260614_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "public_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
    )
    op.create_index("ix_users_public_id", "users", ["public_id"], unique=True)

    op.create_table(
        "voices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("voice_name", sa.String(length=150), nullable=False),
        sa.Column("voice_name_normalized", sa.String(length=150), nullable=False),
        sa.Column("generation_method", sa.String(length=30), nullable=False),
        sa.Column("original_file_name", sa.String(length=255), nullable=True),
        sa.Column("storage_key", sa.String(length=500), nullable=True),
        sa.Column("audio_content_type", sa.String(length=100), nullable=True),
        sa.Column("audio_size", sa.Integer(), nullable=True),
        sa.Column("language", sa.String(length=50), nullable=True),
        sa.Column("gender", sa.String(length=50), nullable=True),
        sa.Column("age", sa.String(length=50), nullable=True),
        sa.Column("pitch", sa.String(length=80), nullable=True),
        sa.Column("style", sa.String(length=80), nullable=True),
        sa.Column("english_accent", sa.String(length=100), nullable=True),
        sa.Column("chinese_dialect", sa.String(length=100), nullable=True),
        sa.Column("provider_metadata", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "generation_method IN ('voice-clone', 'voice-design')",
            name="ck_voices_generation_method",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "voice_name_normalized",
            name="uq_voices_user_name_normalized",
        ),
    )
    op.create_index(
        "ix_voices_generation_method",
        "voices",
        ["generation_method"],
        unique=False,
    )
    op.create_index("ix_voices_user_id", "voices", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_table("voices")
    op.drop_index("ix_users_public_id", table_name="users")
    op.drop_column("users", "public_id")
