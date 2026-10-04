"""create schedules table

Revision ID: 3a59148ccb41
Revises: 54be773f375e
Create Date: 2026-10-04 15:14:37.151319

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "3a59148ccb41"

down_revision: Union[str, Sequence[str], None] = "54be773f375e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "schedules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("category_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_all_day", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column(
            "status", sa.String(length=50), server_default="scheduled", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_schedules_category_id"), "schedules", ["category_id"], unique=False
    )
    op.create_index(
        op.f("ix_schedules_end_time"), "schedules", ["end_time"], unique=False
    )
    op.create_index(op.f("ix_schedules_id"), "schedules", ["id"], unique=False)
    op.create_index(
        op.f("ix_schedules_start_time"), "schedules", ["start_time"], unique=False
    )
    op.create_index(
        op.f("ix_schedules_user_id"), "schedules", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_schedules_user_id"), table_name="schedules")
    op.drop_index(op.f("ix_schedules_start_time"), table_name="schedules")
    op.drop_index(op.f("ix_schedules_id"), table_name="schedules")
    op.drop_index(op.f("ix_schedules_end_time"), table_name="schedules")
    op.drop_index(op.f("ix_schedules_category_id"), table_name="schedules")
    op.drop_table("schedules")
