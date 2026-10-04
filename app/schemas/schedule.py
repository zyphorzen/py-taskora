import uuid
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, model_validator


class RecurrencePattern(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class ScheduleBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Schedule title")
    description: str | None = Field(default=None, description="Schedule description")
    category_id: uuid.UUID | None = Field(
        default=None, description="Associated category ID"
    )
    start_time: datetime = Field(..., description="Start timestamp with timezone")
    end_time: datetime = Field(..., description="End timestamp with timezone")
    is_all_day: bool = Field(default=False, description="Whether event spans whole day")
    location: str | None = Field(
        default=None, max_length=255, description="Event location"
    )
    status: str = Field(
        default="scheduled", max_length=50, description="Schedule status"
    )
    is_recurring: bool = Field(
        default=False, description="Whether schedule repeats periodically"
    )
    recurrence_pattern: RecurrencePattern | None = Field(
        default=None, description="Recurrence pattern: daily, weekly, monthly, yearly"
    )
    recurrence_interval: int = Field(
        default=1, ge=1, description="Interval step for recurrence"
    )
    recurrence_end_date: datetime | None = Field(
        default=None, description="End limit timestamp for recurrence"
    )

    @model_validator(mode="after")
    def validate_schedule(self) -> "ScheduleBase":
        if self.end_time < self.start_time:
            raise ValueError("end_time must be greater than or equal to start_time")
        if self.is_recurring and not self.recurrence_pattern:
            raise ValueError("recurrence_pattern is required when is_recurring is True")
        if (
            self.recurrence_end_date is not None
            and self.recurrence_end_date < self.start_time
        ):
            raise ValueError(
                "recurrence_end_date must be greater than or equal to start_time"
            )
        return self


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleUpdate(BaseModel):
    title: str | None = Field(
        default=None, min_length=1, max_length=255, description="Schedule title"
    )
    description: str | None = Field(default=None, description="Schedule description")
    category_id: uuid.UUID | None = Field(
        default=None, description="Associated category ID"
    )
    start_time: datetime | None = Field(
        default=None, description="Start timestamp with timezone"
    )
    end_time: datetime | None = Field(
        default=None, description="End timestamp with timezone"
    )
    is_all_day: bool | None = Field(
        default=None, description="Whether event spans whole day"
    )
    location: str | None = Field(
        default=None, max_length=255, description="Event location"
    )
    status: str | None = Field(
        default=None, max_length=50, description="Schedule status"
    )
    is_recurring: bool | None = Field(
        default=None, description="Whether schedule repeats periodically"
    )
    recurrence_pattern: RecurrencePattern | None = Field(
        default=None, description="Recurrence pattern"
    )
    recurrence_interval: int | None = Field(
        default=None, ge=1, description="Interval step"
    )
    recurrence_end_date: datetime | None = Field(
        default=None, description="End limit timestamp for recurrence"
    )

    @model_validator(mode="after")
    def validate_times(self) -> "ScheduleUpdate":
        if self.start_time is not None and self.end_time is not None:
            if self.end_time < self.start_time:
                raise ValueError("end_time must be greater than or equal to start_time")
        return self


class ScheduleResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    category_id: uuid.UUID | None = None
    title: str
    description: str | None = None
    start_time: datetime
    end_time: datetime
    is_all_day: bool
    location: str | None = None
    status: str
    is_recurring: bool
    recurrence_pattern: str | None = None
    recurrence_interval: int
    recurrence_end_date: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScheduleOccurrence(BaseModel):
    schedule_id: uuid.UUID
    title: str
    description: str | None = None
    start_time: datetime
    end_time: datetime
    is_all_day: bool
    location: str | None = None
    status: str
    category_id: uuid.UUID | None = None
    is_recurring: bool
    recurrence_pattern: str | None = None


__all__ = [
    "RecurrencePattern",
    "ScheduleBase",
    "ScheduleCreate",
    "ScheduleUpdate",
    "ScheduleResponse",
    "ScheduleOccurrence",
]
