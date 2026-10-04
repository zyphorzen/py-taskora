"""add recurrence fields to schedules

Revision ID: 6a8f2af6c31d
Revises: 3a59148ccb41
Create Date: 2026-10-04 15:22:07.909693

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "6a8f2af6c31d"
down_revision: Union[str, Sequence[str], None] = "3a59148ccb41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "schedules",
        sa.Column("is_recurring", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "schedules",
        sa.Column("recurrence_pattern", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "schedules",
        sa.Column(
            "recurrence_interval", sa.Integer(), server_default="1", nullable=False
        ),
    )
    op.add_column(
        "schedules",
        sa.Column("recurrence_end_date", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("schedules", "recurrence_end_date")
    op.drop_column("schedules", "recurrence_interval")
    op.drop_column("schedules", "recurrence_pattern")
    op.drop_column("schedules", "is_recurring")
