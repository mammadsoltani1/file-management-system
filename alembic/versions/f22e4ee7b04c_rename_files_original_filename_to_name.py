"""rename files.original_filename to name

Revision ID: f22e4ee7b04c
Revises: 7e7c21d65970
Create Date: 2026-08-31 15:55:37.027243

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f22e4ee7b04c"
down_revision: str | Sequence[str] | None = "7e7c21d65970"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("files") as batch_op:
        batch_op.alter_column("original_filename", new_column_name="name")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("files") as batch_op:
        batch_op.alter_column("name", new_column_name="original_filename")
