import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator


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

    @model_validator(mode="after")
    def validate_times(self) -> "ScheduleBase":
        if self.end_time < self.start_time:
            raise ValueError("end_time must be greater than or equal to start_time")
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
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "ScheduleBase",
    "ScheduleCreate",
    "ScheduleUpdate",
    "ScheduleResponse",
]
