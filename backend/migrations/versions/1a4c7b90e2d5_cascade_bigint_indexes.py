"""Cascade alert deletion, widen size, index the columns actually queried

Revision ID: 1a4c7b90e2d5
Revises: 0d6439d2e79f
Create Date: 2026-09-03 23:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "1a4c7b90e2d5"
down_revision: str | Sequence[str] | None = "0d6439d2e79f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Deleting a file that had ever been processed failed outright: every
    # processed file owns at least one alert and the key had no cascade.
    op.drop_constraint("alerts_file_id_fkey", "alerts", type_="foreignkey")
    op.create_foreign_key(
        "alerts_file_id_fkey",
        "alerts",
        "files",
        ["file_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Uploads are bounded at 1 GB by configuration; a 32-bit column caps the
    # recordable size at 2.1 GB, which is the wrong place for that limit.
    op.alter_column(
        "files",
        "size",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )

    # Both lists sort by created_at. The index on alerts.file_id is not for a
    # query but for the cascade above, which otherwise scans the whole table
    # once per deleted file.
    op.create_index("ix_files_created_at", "files", ["created_at"])
    op.create_index("ix_alerts_created_at", "alerts", ["created_at"])
    op.create_index("ix_alerts_file_id", "alerts", ["file_id"])


def downgrade() -> None:
    op.drop_index("ix_alerts_file_id", table_name="alerts")
    op.drop_index("ix_alerts_created_at", table_name="alerts")
    op.drop_index("ix_files_created_at", table_name="files")

    op.alter_column(
        "files",
        "size",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )

    op.drop_constraint("alerts_file_id_fkey", "alerts", type_="foreignkey")
    op.create_foreign_key("alerts_file_id_fkey", "alerts", "files", ["file_id"], ["id"])
