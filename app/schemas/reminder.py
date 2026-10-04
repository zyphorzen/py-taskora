import uuid
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class NotificationType(str, Enum):
    PUSH = "push"
    EMAIL = "email"
    IN_APP = "in_app"


class ReminderBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    remind_at: datetime = Field(...)
    notification_type: NotificationType = NotificationType.PUSH
    task_id: uuid.UUID | None = None
    schedule_id: uuid.UUID | None = None


class ReminderCreate(ReminderBase):
    pass


class ReminderUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    remind_at: datetime | None = None
    notification_type: NotificationType | None = None
    task_id: uuid.UUID | None = None
    schedule_id: uuid.UUID | None = None
    is_sent: bool | None = None


class ReminderResponse(ReminderBase):
    id: uuid.UUID
    user_id: uuid.UUID
    is_sent: bool
    sent_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
