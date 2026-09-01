"""add soft delete fields to folders and files

Revision ID: 251b63f9cf8a
Revises: f22e4ee7b04c
Create Date: 2026-09-01

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "251b63f9cf8a"
down_revision: str | Sequence[str] | None = "f22e4ee7b04c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "folders",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "folders",
        sa.Column("trash_batch_id", sa.Uuid(), nullable=True),
    )
    op.create_index("ix_folders_deleted_at", "folders", ["deleted_at"])
    op.create_index("ix_folders_trash_batch_id", "folders", ["trash_batch_id"])

    op.add_column(
        "files",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "files",
        sa.Column("trash_batch_id", sa.Uuid(), nullable=True),
    )
    op.create_index("ix_files_deleted_at", "files", ["deleted_at"])
    op.create_index("ix_files_trash_batch_id", "files", ["trash_batch_id"])


def downgrade() -> None:
    op.drop_index("ix_files_trash_batch_id", table_name="files")
    op.drop_index("ix_files_deleted_at", table_name="files")
    op.drop_column("files", "trash_batch_id")
    op.drop_column("files", "deleted_at")

    op.drop_index("ix_folders_trash_batch_id", table_name="folders")
    op.drop_index("ix_folders_deleted_at", table_name="folders")
    op.drop_column("folders", "trash_batch_id")
    op.drop_column("folders", "deleted_at")
