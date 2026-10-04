from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "7d49712f3313"
down_revision: Union[str, Sequence[str], None] = "6a8f2af6c31d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reminders",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("schedule_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("remind_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_sent", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "notification_type",
            sa.String(length=50),
            server_default="push",
            nullable=False,
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
        sa.ForeignKeyConstraint(["schedule_id"], ["schedules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reminders_id"), "reminders", ["id"], unique=False)
    op.create_index(
        op.f("ix_reminders_is_sent"), "reminders", ["is_sent"], unique=False
    )
    op.create_index(
        op.f("ix_reminders_remind_at"), "reminders", ["remind_at"], unique=False
    )
    op.create_index(
        op.f("ix_reminders_schedule_id"), "reminders", ["schedule_id"], unique=False
    )
    op.create_index(
        op.f("ix_reminders_task_id"), "reminders", ["task_id"], unique=False
    )
    op.create_index(
        op.f("ix_reminders_user_id"), "reminders", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_reminders_user_id"), table_name="reminders")
    op.drop_index(op.f("ix_reminders_task_id"), table_name="reminders")
    op.drop_index(op.f("ix_reminders_schedule_id"), table_name="reminders")
    op.drop_index(op.f("ix_reminders_remind_at"), table_name="reminders")
    op.drop_index(op.f("ix_reminders_is_sent"), table_name="reminders")
    op.drop_index(op.f("ix_reminders_id"), table_name="reminders")
    op.drop_table("reminders")
