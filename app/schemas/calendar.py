import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.schemas.schedule import ScheduleOccurrence


class CalendarTaskItem(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None = None
    status: str
    priority: str
    due_date: datetime
    completed_at: datetime | None = None
    category_id: uuid.UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class CalendarReminderItem(BaseModel):
    id: uuid.UUID
    title: str
    remind_at: datetime
    notification_type: str
    is_sent: bool
    task_id: uuid.UUID | None = None
    schedule_id: uuid.UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class CalendarViewResponse(BaseModel):
    start_date: datetime
    end_date: datetime
    schedules: list[ScheduleOccurrence]
    tasks: list[CalendarTaskItem]
    reminders: list[CalendarReminderItem]
    total_schedules: int
    total_tasks: int
    total_reminders: int
    total_items: int


class CalendarDaySummary(BaseModel):
    date: str
    schedules_count: int
    tasks_count: int
    reminders_count: int
    total_count: int
