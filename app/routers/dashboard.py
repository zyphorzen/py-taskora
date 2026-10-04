import uuid
from datetime import datetime, time, timedelta, timezone
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.category import Category
from app.models.reminder import Reminder
from app.models.schedule import Schedule
from app.models.task import Task
from app.models.user import User
from app.routers.schedules import generate_schedule_occurrences
from app.schemas.dashboard import (
    CategoryDashboardItem,
    DashboardResponse,
    QuickStatsResponse,
    ReminderDashboardSummary,
    ScheduleDashboardSummary,
    TaskDashboardSummary,
)
from app.schemas.reminder import ReminderResponse
from app.schemas.schedule import ScheduleOccurrence
from app.schemas.task import TaskResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "",
    response_model=DashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get aggregated user dashboard metrics and upcoming items",
)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    now = datetime.now(timezone.utc)
    today_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    today_end = datetime.combine(now.date(), time.max, tzinfo=timezone.utc)
    month_ahead = now + timedelta(days=30)

    task_stmt = select(Task).where(Task.user_id == current_user.id)
    task_res = await db.execute(task_stmt)
    tasks = list(task_res.scalars().all())

    by_status = {"todo": 0, "in_progress": 0, "completed": 0, "cancelled": 0}
    by_priority = {"low": 0, "medium": 0, "high": 0, "urgent": 0}
    completed_tasks = 0
    pending_tasks = 0
    overdue_tasks = 0

    for t in tasks:
        st = t.status.lower()
        pr = t.priority.lower()
        if st in by_status:
            by_status[st] += 1
        if pr in by_priority:
            by_priority[pr] += 1

        if st == "completed":
            completed_tasks += 1
        elif st != "cancelled":
            pending_tasks += 1
            if t.due_date and t.due_date < now:
                overdue_tasks += 1

    total_tasks = len(tasks)
    completion_rate = (
        round((completed_tasks / total_tasks) * 100, 2) if total_tasks > 0 else 0.0
    )

    priority_weight = {"urgent": 4, "high": 3, "medium": 2, "low": 1}
    urgent_candidates = [t for t in tasks if t.status not in ("completed", "cancelled")]
    urgent_candidates.sort(
        key=lambda x: (
            -priority_weight.get(x.priority.lower(), 0),
            x.due_date if x.due_date else datetime.max.replace(tzinfo=timezone.utc),
        )
    )
    recent_urgent_tasks = [
        TaskResponse.model_validate(t) for t in urgent_candidates[:5]
    ]

    sched_stmt = select(Schedule).where(Schedule.user_id == current_user.id)
    sched_res = await db.execute(sched_stmt)
    schedules = list(sched_res.scalars().all())

    today_occurrences: list[ScheduleOccurrence] = []
    month_occurrences: list[ScheduleOccurrence] = []

    for s in schedules:
        today_occurrences.extend(
            generate_schedule_occurrences(s, today_start, today_end)
        )
        month_occurrences.extend(generate_schedule_occurrences(s, now, month_ahead))

    month_occurrences.sort(key=lambda s: s.start_time)
    upcoming_schedules = month_occurrences[:5]

    rem_stmt = (
        select(Reminder)
        .where(Reminder.user_id == current_user.id)
        .order_by(Reminder.remind_at.asc())
    )
    rem_res = await db.execute(rem_stmt)
    reminders = list(rem_res.scalars().all())

    pending_reminders = [r for r in reminders if not r.is_sent]
    due_reminders_list = [r for r in pending_reminders if r.remind_at <= now]

    cat_stmt = (
        select(Category)
        .where(Category.user_id == current_user.id)
        .order_by(Category.name.asc())
    )
    cat_res = await db.execute(cat_stmt)
    categories = list(cat_res.scalars().all())

    cat_items: list[CategoryDashboardItem] = []
    for c in categories:
        t_cnt = sum(1 for t in tasks if t.category_id == c.id)
        s_cnt = sum(1 for s in schedules if s.category_id == c.id)
        cat_items.append(
            CategoryDashboardItem(
                id=c.id,
                name=c.name,
                color=c.color,
                task_count=t_cnt,
                schedule_count=s_cnt,
            )
        )

    return DashboardResponse(
        tasks=TaskDashboardSummary(
            total=total_tasks,
            completed=completed_tasks,
            pending=pending_tasks,
            overdue=overdue_tasks,
            completion_rate=completion_rate,
            by_status=by_status,
            by_priority=by_priority,
        ),
        schedules=ScheduleDashboardSummary(
            total=len(schedules),
            upcoming_count=len(month_occurrences),
            today_count=len(today_occurrences),
        ),
        reminders=ReminderDashboardSummary(
            total=len(reminders),
            pending_count=len(pending_reminders),
            due_count=len(due_reminders_list),
        ),
        categories=cat_items,
        recent_urgent_tasks=recent_urgent_tasks,
        upcoming_schedules=upcoming_schedules,
        due_reminders=[
            ReminderResponse.model_validate(r) for r in due_reminders_list[:5]
        ],
    )


@router.get(
    "/quick-stats",
    response_model=QuickStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lightweight high-level statistics for dashboard widgets",
)
async def get_quick_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuickStatsResponse:
    now = datetime.now(timezone.utc)
    today_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    today_end = datetime.combine(now.date(), time.max, tzinfo=timezone.utc)
    month_ahead = now + timedelta(days=30)

    task_stmt = select(Task).where(Task.user_id == current_user.id)
    task_res = await db.execute(task_stmt)
    tasks = list(task_res.scalars().all())

    completed_tasks = 0
    pending_tasks = 0
    overdue_tasks = 0

    for t in tasks:
        st = t.status.lower()
        if st == "completed":
            completed_tasks += 1
        elif st != "cancelled":
            pending_tasks += 1
            if t.due_date and t.due_date < now:
                overdue_tasks += 1

    sched_stmt = select(Schedule).where(Schedule.user_id == current_user.id)
    sched_res = await db.execute(sched_stmt)
    schedules = list(sched_res.scalars().all())

    today_count = 0
    upcoming_count = 0
    for s in schedules:
        today_count += len(generate_schedule_occurrences(s, today_start, today_end))
        upcoming_count += len(generate_schedule_occurrences(s, now, month_ahead))

    rem_stmt = select(Reminder).where(Reminder.user_id == current_user.id)
    rem_res = await db.execute(rem_stmt)
    reminders = list(rem_res.scalars().all())

    pending_reminders = sum(1 for r in reminders if not r.is_sent)
    due_reminders = sum(1 for r in reminders if not r.is_sent and r.remind_at <= now)

    return QuickStatsResponse(
        total_tasks=len(tasks),
        completed_tasks=completed_tasks,
        pending_tasks=pending_tasks,
        overdue_tasks=overdue_tasks,
        total_schedules=len(schedules),
        upcoming_schedules=upcoming_count,
        today_schedules=today_count,
        pending_reminders=pending_reminders,
        due_reminders=due_reminders,
    )
