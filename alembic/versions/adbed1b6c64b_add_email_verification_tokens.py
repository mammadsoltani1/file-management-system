"""add email verification tokens

Revision ID: adbed1b6c64b
Revises: 2c5fa424d88d
Create Date: 2026-09-02 11:07:36.301751

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "adbed1b6c64b"
down_revision: str | Sequence[str] | None = "2c5fa424d88d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "email_verification_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_email_verification_tokens_expires_at",
        "email_verification_tokens",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_email_verification_tokens_token_hash",
        "email_verification_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_email_verification_tokens_used_at",
        "email_verification_tokens",
        ["used_at"],
        unique=False,
    )
    op.create_index(
        "ix_email_verification_tokens_user_id",
        "email_verification_tokens",
        ["user_id"],
        unique=False,
    )
    op.add_column(
        "users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("users", "email_verified_at")
    op.drop_index(
        "ix_email_verification_tokens_user_id", table_name="email_verification_tokens"
    )
    op.drop_index(
        "ix_email_verification_tokens_used_at", table_name="email_verification_tokens"
    )
    op.drop_index(
        "ix_email_verification_tokens_token_hash", table_name="email_verification_tokens"
    )
    op.drop_index(
        "ix_email_verification_tokens_expires_at", table_name="email_verification_tokens"
    )
    op.drop_table("email_verification_tokens")
