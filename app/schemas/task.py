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


__all__ = [
    "TaskStatus",
    "TaskPriority",
    "TaskBase",
    "TaskCreate",
    "TaskUpdate",
    "TaskResponse",
]
