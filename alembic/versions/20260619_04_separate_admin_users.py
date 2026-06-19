"""Create separate admin users and remove the user admin flag."""

from alembic import op
import sqlalchemy as sa

revision = "20260619_04"
down_revision = "20260615_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_admins",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_user_admins_username", "user_admins", ["username"], unique=True
    )
    op.create_index("ix_user_admins_email", "user_admins", ["email"], unique=True)

    op.execute(
        sa.text(
            """
            INSERT INTO user_admins
                (username, password_hash, email, is_active, created_at, updated_at)
            SELECT username, password_hash, email, is_active, created_at, updated_at
            FROM users
            WHERE is_default = true
            """
        )
    )
    op.drop_column("users", "is_default")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_default", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.execute(
        sa.text(
            """
            UPDATE users
            SET is_default = true
            WHERE username IN (SELECT username FROM user_admins)
            """
        )
    )
    op.drop_table("user_admins")
