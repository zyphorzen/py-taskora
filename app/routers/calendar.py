import calendar as py_calendar
import uuid
from datetime import date as date_type, datetime, time, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.reminder import Reminder
from app.models.schedule import Schedule
from app.models.task import Task
from app.models.user import User
from app.routers.schedules import generate_schedule_occurrences
from app.schemas.calendar import (
    CalendarDaySummary,
    CalendarReminderItem,
    CalendarTaskItem,
    CalendarViewResponse,
)
from app.schemas.schedule import ScheduleOccurrence

router = APIRouter(prefix="/calendar", tags=["Calendar"])


async def _fetch_calendar_view(
    user_id: uuid.UUID,
    window_start: datetime,
    window_end: datetime,
    category_id: uuid.UUID | None,
    include_schedules: bool,
    include_tasks: bool,
    include_reminders: bool,
    db: AsyncSession,
) -> CalendarViewResponse:
    schedules_res: list[ScheduleOccurrence] = []
    tasks_res: list[CalendarTaskItem] = []
    reminders_res: list[CalendarReminderItem] = []

    if include_schedules:
        schedules_query = select(Schedule).where(
            Schedule.user_id == user_id,
            or_(
                Schedule.is_recurring == True,
                Schedule.start_time <= window_end,
            ),
        )
        if category_id is not None:
            schedules_query = schedules_query.where(Schedule.category_id == category_id)

        exec_res = await db.execute(schedules_query)
        schedules = exec_res.scalars().all()

        for sched in schedules:
            occurrences = generate_schedule_occurrences(sched, window_start, window_end)
            schedules_res.extend(occurrences)

        schedules_res.sort(key=lambda s: s.start_time)

    if include_tasks:
        tasks_query = select(Task).where(
            Task.user_id == user_id,
            Task.due_date.is_not(None),
            Task.due_date >= window_start,
            Task.due_date <= window_end,
        )
        if category_id is not None:
            tasks_query = tasks_query.where(Task.category_id == category_id)

        tasks_query = tasks_query.order_by(Task.due_date.asc())
        exec_res = await db.execute(tasks_query)
        tasks = exec_res.scalars().all()

        for t in tasks:
            tasks_res.append(
                CalendarTaskItem(
                    id=t.id,
                    title=t.title,
                    description=t.description,
                    status=t.status,
                    priority=t.priority,
                    due_date=t.due_date,
                    completed_at=t.completed_at,
                    category_id=t.category_id,
                )
            )

    if include_reminders:
        reminders_query = (
            select(Reminder)
            .where(
                Reminder.user_id == user_id,
                Reminder.remind_at >= window_start,
                Reminder.remind_at <= window_end,
            )
            .order_by(Reminder.remind_at.asc())
        )
        exec_res = await db.execute(reminders_query)
        reminders = exec_res.scalars().all()

        for r in reminders:
            reminders_res.append(
                CalendarReminderItem(
                    id=r.id,
                    title=r.title,
                    remind_at=r.remind_at,
                    notification_type=r.notification_type,
                    is_sent=r.is_sent,
                    task_id=r.task_id,
                    schedule_id=r.schedule_id,
                )
            )

    total_s = len(schedules_res)
    total_t = len(tasks_res)
    total_r = len(reminders_res)

    return CalendarViewResponse(
        start_date=window_start,
        end_date=window_end,
        schedules=schedules_res,
        tasks=tasks_res,
        reminders=reminders_res,
        total_schedules=total_s,
        total_tasks=total_t,
        total_reminders=total_r,
        total_items=total_s + total_t + total_r,
    )


@router.get(
    "/events",
    response_model=CalendarViewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get aggregated calendar items within a date range",
)
async def get_calendar_events(
    start_date: datetime = Query(..., description="Window start datetime"),
    end_date: datetime = Query(..., description="Window end datetime"),
    category_id: uuid.UUID | None = Query(default=None),
    include_schedules: bool = Query(default=True),
    include_tasks: bool = Query(default=True),
    include_reminders: bool = Query(default=True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CalendarViewResponse:
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be greater than or equal to start_date",
        )

    return await _fetch_calendar_view(
        user_id=current_user.id,
        window_start=start_date,
        window_end=end_date,
        category_id=category_id,
        include_schedules=include_schedules,
        include_tasks=include_tasks,
        include_reminders=include_reminders,
        db=db,
    )


@router.get(
    "/day",
    response_model=CalendarViewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get calendar items for a single day",
)
async def get_calendar_day(
    target_date: date_type = Query(..., description="Target date in YYYY-MM-DD format"),
    category_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CalendarViewResponse:
    window_start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
    window_end = datetime.combine(target_date, time.max, tzinfo=timezone.utc)

    return await _fetch_calendar_view(
        user_id=current_user.id,
        window_start=window_start,
        window_end=window_end,
        category_id=category_id,
        include_schedules=True,
        include_tasks=True,
        include_reminders=True,
        db=db,
    )


@router.get(
    "/month-summary",
    response_model=list[CalendarDaySummary],
    status_code=status.HTTP_200_OK,
    summary="Get item counts per day for a specific month",
)
async def get_month_summary(
    year: int = Query(..., ge=1970, le=2100),
    month: int = Query(..., ge=1, le=12),
    category_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CalendarDaySummary]:
    _, last_day = py_calendar.monthrange(year, month)
    window_start = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
    window_end = datetime(
        year, month, last_day, 23, 59, 59, 999999, tzinfo=timezone.utc
    )

    cal_view = await _fetch_calendar_view(
        user_id=current_user.id,
        window_start=window_start,
        window_end=window_end,
        category_id=category_id,
        include_schedules=True,
        include_tasks=True,
        include_reminders=True,
        db=db,
    )

    day_data: dict[str, dict[str, int]] = {}
    for day in range(1, last_day + 1):
        date_str = f"{year:04d}-{month:02d}-{day:02d}"
        day_data[date_str] = {
            "schedules": 0,
            "tasks": 0,
            "reminders": 0,
        }

    for s in cal_view.schedules:
        s_date = s.start_time.date()
        s_str = s_date.isoformat()
        if s_str in day_data:
            day_data[s_str]["schedules"] += 1

    for t in cal_view.tasks:
        t_date = t.due_date.date()
        t_str = t_date.isoformat()
        if t_str in day_data:
            day_data[t_str]["tasks"] += 1

    for r in cal_view.reminders:
        r_date = r.remind_at.date()
        r_str = r_date.isoformat()
        if r_str in day_data:
            day_data[r_str]["reminders"] += 1

    summaries: list[CalendarDaySummary] = []
    for date_str in sorted(day_data.keys()):
        counts = day_data[date_str]
        tot = counts["schedules"] + counts["tasks"] + counts["reminders"]
        summaries.append(
            CalendarDaySummary(
                date=date_str,
                schedules_count=counts["schedules"],
                tasks_count=counts["tasks"],
                reminders_count=counts["reminders"],
                total_count=tot,
            )
        )

    return summaries
