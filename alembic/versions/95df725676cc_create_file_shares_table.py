"""create file shares table

Revision ID: 95df725676cc
Revises: e4cbf7df3a5c
Create Date: 2026-09-05

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "95df725676cc"
down_revision: str | Sequence[str] | None = "e4cbf7df3a5c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "file_shares",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("file_id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "file_id", "recipient_id", name="uq_file_shares_file_id_recipient_id"
        ),
    )
    op.create_index("ix_file_shares_file_id", "file_shares", ["file_id"])
    op.create_index("ix_file_shares_owner_id", "file_shares", ["owner_id"])
    op.create_index("ix_file_shares_recipient_id", "file_shares", ["recipient_id"])


def downgrade() -> None:
    op.drop_index("ix_file_shares_recipient_id", table_name="file_shares")
    op.drop_index("ix_file_shares_owner_id", table_name="file_shares")
    op.drop_index("ix_file_shares_file_id", table_name="file_shares")
    op.drop_table("file_shares")
