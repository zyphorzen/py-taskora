import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.reminder import Reminder
from app.models.schedule import Schedule
from app.models.task import Task
from app.models.user import User
from app.schemas.reminder import (
    ReminderCreate,
    ReminderResponse,
    ReminderUpdate,
)

router = APIRouter(prefix="/reminders", tags=["Reminders"])


async def _validate_task_ownership(
    task_id: uuid.UUID | None,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    if task_id is None:
        return
    query = select(Task).where(
        Task.id == task_id,
        Task.user_id == user_id,
    )
    result = await db.execute(query)
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task not found or does not belong to user",
        )


async def _validate_schedule_ownership(
    schedule_id: uuid.UUID | None,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    if schedule_id is None:
        return
    query = select(Schedule).where(
        Schedule.id == schedule_id,
        Schedule.user_id == user_id,
    )
    result = await db.execute(query)
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Schedule not found or does not belong to user",
        )


@router.post(
    "",
    response_model=ReminderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new reminder",
)
async def create_reminder(
    reminder_in: ReminderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Reminder:
    await _validate_task_ownership(reminder_in.task_id, current_user.id, db)
    await _validate_schedule_ownership(reminder_in.schedule_id, current_user.id, db)

    type_val = (
        reminder_in.notification_type.value
        if hasattr(reminder_in.notification_type, "value")
        else reminder_in.notification_type
    )

    reminder = Reminder(
        user_id=current_user.id,
        task_id=reminder_in.task_id,
        schedule_id=reminder_in.schedule_id,
        title=reminder_in.title.strip(),
        remind_at=reminder_in.remind_at,
        notification_type=type_val,
    )
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    return reminder


@router.get(
    "/due",
    response_model=list[ReminderResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all unsent due reminders",
)
async def get_due_reminders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Reminder]:
    now = datetime.now(timezone.utc)
    query = (
        select(Reminder)
        .where(
            Reminder.user_id == current_user.id,
            Reminder.is_sent == False,
            Reminder.remind_at <= now,
        )
        .order_by(Reminder.remind_at.asc())
    )
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get(
    "",
    response_model=list[ReminderResponse],
    status_code=status.HTTP_200_OK,
    summary="List reminders with filters",
)
async def get_reminders(
    is_sent: bool | None = Query(default=None),
    task_id: uuid.UUID | None = Query(default=None),
    schedule_id: uuid.UUID | None = Query(default=None),
    upcoming: bool | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Reminder]:
    query = select(Reminder).where(Reminder.user_id == current_user.id)

    if is_sent is not None:
        query = query.where(Reminder.is_sent == is_sent)
    if task_id is not None:
        query = query.where(Reminder.task_id == task_id)
    if schedule_id is not None:
        query = query.where(Reminder.schedule_id == schedule_id)
    if upcoming is True:
        now = datetime.now(timezone.utc)
        query = query.where(Reminder.remind_at >= now)

    query = query.order_by(Reminder.remind_at.asc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get(
    "/{reminder_id}",
    response_model=ReminderResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a reminder by ID",
)
async def get_reminder(
    reminder_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Reminder:
    query = select(Reminder).where(
        Reminder.id == reminder_id,
        Reminder.user_id == current_user.id,
    )
    result = await db.execute(query)
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder not found",
        )
    return reminder


@router.patch(
    "/{reminder_id}",
    response_model=ReminderResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a reminder",
)
async def update_reminder(
    reminder_id: uuid.UUID,
    reminder_in: ReminderUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Reminder:
    query = select(Reminder).where(
        Reminder.id == reminder_id,
        Reminder.user_id == current_user.id,
    )
    result = await db.execute(query)
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder not found",
        )

    update_data = reminder_in.model_dump(exclude_unset=True)

    if "task_id" in update_data:
        await _validate_task_ownership(update_data["task_id"], current_user.id, db)
    if "schedule_id" in update_data:
        await _validate_schedule_ownership(
            update_data["schedule_id"], current_user.id, db
        )

    for field, value in update_data.items():
        if field == "title" and value is not None:
            setattr(reminder, field, value.strip())
        elif field == "notification_type" and value is not None:
            type_val = value.value if hasattr(value, "value") else value
            setattr(reminder, field, type_val)
        else:
            setattr(reminder, field, value)

    await db.commit()
    await db.refresh(reminder)
    return reminder


@router.post(
    "/{reminder_id}/mark-sent",
    response_model=ReminderResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark reminder as sent",
)
async def mark_reminder_sent(
    reminder_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Reminder:
    query = select(Reminder).where(
        Reminder.id == reminder_id,
        Reminder.user_id == current_user.id,
    )
    result = await db.execute(query)
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder not found",
        )

    reminder.is_sent = True
    reminder.sent_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(reminder)
    return reminder


@router.delete(
    "/{reminder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a reminder",
)
async def delete_reminder(
    reminder_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    query = select(Reminder).where(
        Reminder.id == reminder_id,
        Reminder.user_id == current_user.id,
    )
    result = await db.execute(query)
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder not found",
        )

    await db.delete(reminder)
    await db.commit()
