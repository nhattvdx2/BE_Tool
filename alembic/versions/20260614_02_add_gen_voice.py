"""Add gen voice permission and enable design voice by default."""

from alembic import op
import sqlalchemy as sa

revision = "20260614_02"
down_revision = "20260613_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "gen_voice",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.alter_column("users", "design_voice", server_default=sa.true())


def downgrade() -> None:
    op.alter_column("users", "design_voice", server_default=sa.false())
    op.drop_column("users", "gen_voice")
