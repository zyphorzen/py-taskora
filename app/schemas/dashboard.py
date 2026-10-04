import uuid
from pydantic import BaseModel, ConfigDict
from app.schemas.reminder import ReminderResponse
from app.schemas.schedule import ScheduleOccurrence
from app.schemas.task import TaskResponse


class TaskDashboardSummary(BaseModel):
    total: int
    completed: int
    pending: int
    overdue: int
    completion_rate: float
    by_status: dict[str, int]
    by_priority: dict[str, int]


class ScheduleDashboardSummary(BaseModel):
    total: int
    upcoming_count: int
    today_count: int


class ReminderDashboardSummary(BaseModel):
    total: int
    pending_count: int
    due_count: int


class CategoryDashboardItem(BaseModel):
    id: uuid.UUID
    name: str
    color: str | None = None
    task_count: int
    schedule_count: int

    model_config = ConfigDict(from_attributes=True)


class QuickStatsResponse(BaseModel):
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    overdue_tasks: int
    total_schedules: int
    upcoming_schedules: int
    today_schedules: int
    pending_reminders: int
    due_reminders: int


class DashboardResponse(BaseModel):
    tasks: TaskDashboardSummary
    schedules: ScheduleDashboardSummary
    reminders: ReminderDashboardSummary
    categories: list[CategoryDashboardItem]
    recent_urgent_tasks: list[TaskResponse]
    upcoming_schedules: list[ScheduleOccurrence]
    due_reminders: list[ReminderResponse]
