import uuid
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Task title")
    description: str | None = Field(
        default=None, description="Detailed task description"
    )
    category_id: uuid.UUID | None = Field(
        default=None, description="Associated category ID"
    )
    status: TaskStatus = Field(default=TaskStatus.TODO, description="Task status")
    priority: TaskPriority = Field(
        default=TaskPriority.MEDIUM, description="Task priority level"
    )
    due_date: datetime | None = Field(
        default=None, description="Due date/time with timezone"
    )


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = Field(
        default=None, min_length=1, max_length=255, description="Task title"
    )
    description: str | None = Field(
        default=None, description="Detailed task description"
    )
    category_id: uuid.UUID | None = Field(
        default=None, description="Associated category ID"
    )
    status: TaskStatus | None = Field(default=None, description="Task status")
    priority: TaskPriority | None = Field(
        default=None, description="Task priority level"
    )
    due_date: datetime | None = Field(
        default=None, description="Due date/time with timezone"
    )
    completed_at: datetime | None = Field(
        default=None, description="Completion timestamp"
    )


class TaskResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    category_id: uuid.UUID | None = None
    title: str
    description: str | None = None
    status: str
    priority: str
    due_date: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskStatusUpdate(BaseModel):
    status: TaskStatus = Field(..., description="Target status")


class TaskPriorityUpdate(BaseModel):
    priority: TaskPriority = Field(..., description="Target priority level")


class TaskBulkStatusUpdate(BaseModel):
    task_ids: list[uuid.UUID] = Field(
        ..., min_length=1, description="List of task IDs to update"
    )
    status: TaskStatus = Field(..., description="Target status for all specified tasks")


class TaskBulkDelete(BaseModel):
    task_ids: list[uuid.UUID] = Field(
        ..., min_length=1, description="List of task IDs to delete"
    )


class TaskBulkOperationResponse(BaseModel):
    affected_count: int
    task_ids: list[uuid.UUID]


class TaskStatisticsResponse(BaseModel):
    total: int
    by_status: dict[str, int]
    by_priority: dict[str, int]
    completed_count: int
    pending_count: int
    overdue_count: int


__all__ = [
    "TaskStatus",
    "TaskPriority",
    "TaskBase",
    "TaskCreate",
    "TaskUpdate",
    "TaskResponse",
    "TaskStatusUpdate",
    "TaskPriorityUpdate",
    "TaskBulkStatusUpdate",
    "TaskBulkDelete",
    "TaskBulkOperationResponse",
    "TaskStatisticsResponse",
]
