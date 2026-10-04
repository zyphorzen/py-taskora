import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.category import Category
from app.models.task import Task
from app.models.user import User
from app.schemas.task import (
    TaskCreate,
    TaskPriority,
    TaskResponse,
    TaskStatus,
    TaskUpdate,
)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


async def _validate_category_ownership(
    category_id: uuid.UUID | None,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    if category_id is None:
        return
    query = select(Category).where(
        Category.id == category_id,
        Category.user_id == user_id,
    )
    result = await db.execute(query)
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not found or does not belong to user",
        )


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
)
async def create_task(
    task_in: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Task:
    await _validate_category_ownership(task_in.category_id, current_user.id, db)

    completed_at = None
    if task_in.status == TaskStatus.COMPLETED:
        completed_at = datetime.now(timezone.utc)

    task = Task(
        user_id=current_user.id,
        category_id=task_in.category_id,
        title=task_in.title.strip(),
        description=task_in.description,
        status=task_in.status.value,
        priority=task_in.priority.value,
        due_date=task_in.due_date,
        completed_at=completed_at,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.get(
    "",
    response_model=list[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="List all tasks for the authenticated user",
)
async def list_tasks(
    q: str | None = Query(None, description="Search substring in title or description"),
    status_filter: TaskStatus | None = Query(
        None, alias="status", description="Filter by status"
    ),
    priority_filter: TaskPriority | None = Query(
        None, alias="priority", description="Filter by priority"
    ),
    category_id: uuid.UUID | None = Query(None, description="Filter by category ID"),
    sort_by: str = Query(
        "created_at", description="Sort field: created_at, due_date, priority, title"
    ),
    order: str = Query("desc", description="Sort direction: asc or desc"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Task]:
    stmt = select(Task).where(Task.user_id == current_user.id)

    if q:
        search = f"%{q.strip()}%"
        stmt = stmt.where(or_(Task.title.ilike(search), Task.description.ilike(search)))

    if status_filter:
        stmt = stmt.where(Task.status == status_filter.value)

    if priority_filter:
        stmt = stmt.where(Task.priority == priority_filter.value)

    if category_id:
        stmt = stmt.where(Task.category_id == category_id)

    allowed_sort_fields = {
        "created_at": Task.created_at,
        "due_date": Task.due_date,
        "priority": Task.priority,
        "title": Task.title,
    }
    sort_column = allowed_sort_fields.get(sort_by, Task.created_at)
    if order.lower() == "asc":
        stmt = stmt.order_by(sort_column.asc().nulls_last())
    else:
        stmt = stmt.order_by(sort_column.desc().nulls_last())

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a task by ID",
)
async def get_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Task:
    stmt = select(Task).where(
        Task.id == task_id,
        Task.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return task


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a task (partial update)",
)
async def update_task(
    task_id: uuid.UUID,
    task_in: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Task:
    stmt = select(Task).where(
        Task.id == task_id,
        Task.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    update_data = task_in.model_dump(exclude_unset=True)

    if "category_id" in update_data:
        await _validate_category_ownership(
            update_data["category_id"], current_user.id, db
        )
        task.category_id = update_data["category_id"]

    if "title" in update_data and update_data["title"] is not None:
        task.title = update_data["title"].strip()

    if "description" in update_data:
        task.description = update_data["description"]

    if "priority" in update_data and update_data["priority"] is not None:
        task.priority = (
            update_data["priority"].value
            if hasattr(update_data["priority"], "value")
            else str(update_data["priority"])
        )

    if "due_date" in update_data:
        task.due_date = update_data["due_date"]

    if "status" in update_data and update_data["status"] is not None:
        new_status = (
            update_data["status"].value
            if hasattr(update_data["status"], "value")
            else str(update_data["status"])
        )
        old_status = task.status
        task.status = new_status
        if "completed_at" not in update_data:
            if (
                new_status == TaskStatus.COMPLETED.value
                and old_status != TaskStatus.COMPLETED.value
            ):
                task.completed_at = datetime.now(timezone.utc)
            elif new_status != TaskStatus.COMPLETED.value:
                task.completed_at = None

    if "completed_at" in update_data:
        task.completed_at = update_data["completed_at"]

    await db.commit()
    await db.refresh(task)
    return task


@router.put(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a task (full update)",
)
async def update_task_put(
    task_id: uuid.UUID,
    task_in: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Task:
    return await update_task(
        task_id=task_id,
        task_in=TaskUpdate(**task_in.model_dump()),
        current_user=current_user,
        db=db,
    )


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
)
async def delete_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    stmt = select(Task).where(
        Task.id == task_id,
        Task.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    await db.delete(task)
    await db.commit()
