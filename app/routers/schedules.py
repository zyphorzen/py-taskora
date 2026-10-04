import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.category import Category
from app.models.schedule import Schedule
from app.models.user import User
from app.schemas.schedule import (
    ScheduleCreate,
    ScheduleOccurrence,
    ScheduleResponse,
    ScheduleUpdate,
)

router = APIRouter(prefix="/schedules", tags=["Schedules"])


def add_months(dt: datetime, months: int) -> datetime:
    year = dt.year + (dt.month + months - 1) // 12
    month = (dt.month + months - 1) % 12 + 1
    is_leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    month_days = [31, 29 if is_leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    day = min(dt.day, month_days[month - 1])
    return dt.replace(year=year, month=month, day=day)


def add_years(dt: datetime, years: int) -> datetime:
    year = dt.year + years
    is_leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    day = dt.day
    if dt.month == 2 and dt.day == 29 and not is_leap:
        day = 28
    return dt.replace(year=year, day=day)


def generate_schedule_occurrences(
    schedule: Schedule,
    window_start: datetime,
    window_end: datetime,
) -> list[ScheduleOccurrence]:
    duration = schedule.end_time - schedule.start_time
    occurrences: list[ScheduleOccurrence] = []

    if not schedule.is_recurring:
        if schedule.start_time <= window_end and schedule.end_time >= window_start:
            occurrences.append(
                ScheduleOccurrence(
                    schedule_id=schedule.id,
                    title=schedule.title,
                    description=schedule.description,
                    start_time=schedule.start_time,
                    end_time=schedule.end_time,
                    is_all_day=schedule.is_all_day,
                    location=schedule.location,
                    status=schedule.status,
                    category_id=schedule.category_id,
                    is_recurring=False,
                    recurrence_pattern=None,
                )
            )
        return occurrences

    cur_start = schedule.start_time
    interval = max(schedule.recurrence_interval, 1)
    pattern = (schedule.recurrence_pattern or "daily").lower()
    end_limit = schedule.recurrence_end_date
    max_occurrences = 500
    count = 0

    while cur_start <= window_end and count < max_occurrences:
        if end_limit is not None and cur_start > end_limit:
            break

        cur_end = cur_start + duration
        if cur_start <= window_end and cur_end >= window_start:
            occurrences.append(
                ScheduleOccurrence(
                    schedule_id=schedule.id,
                    title=schedule.title,
                    description=schedule.description,
                    start_time=cur_start,
                    end_time=cur_end,
                    is_all_day=schedule.is_all_day,
                    location=schedule.location,
                    status=schedule.status,
                    category_id=schedule.category_id,
                    is_recurring=True,
                    recurrence_pattern=pattern,
                )
            )

        if pattern == "daily":
            cur_start = cur_start + timedelta(days=interval)
        elif pattern == "weekly":
            cur_start = cur_start + timedelta(days=7 * interval)
        elif pattern == "monthly":
            cur_start = add_months(cur_start, interval)
        elif pattern == "yearly":
            cur_start = add_years(cur_start, interval)
        else:
            cur_start = cur_start + timedelta(days=interval)

        count += 1

    return occurrences


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
    response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new schedule",
)
async def create_schedule(
    schedule_in: ScheduleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Schedule:
    await _validate_category_ownership(schedule_in.category_id, current_user.id, db)

    pattern_val = (
        schedule_in.recurrence_pattern.value
        if hasattr(schedule_in.recurrence_pattern, "value")
        else schedule_in.recurrence_pattern
    )

    schedule = Schedule(
        user_id=current_user.id,
        category_id=schedule_in.category_id,
        title=schedule_in.title.strip(),
        description=schedule_in.description,
        start_time=schedule_in.start_time,
        end_time=schedule_in.end_time,
        is_all_day=schedule_in.is_all_day,
        location=schedule_in.location,
        status=schedule_in.status,
        is_recurring=schedule_in.is_recurring,
        recurrence_pattern=pattern_val,
        recurrence_interval=schedule_in.recurrence_interval,
        recurrence_end_date=schedule_in.recurrence_end_date,
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return schedule


@router.get(
    "/occurrences",
    response_model=list[ScheduleOccurrence],
    status_code=status.HTTP_200_OK,
    summary="Get schedule occurrences within a date window including recurring expansions",
)
async def get_schedule_occurrences(
    start_date: datetime = Query(
        ..., description="Window start timestamp with timezone"
    ),
    end_date: datetime = Query(..., description="Window end timestamp with timezone"),
    category_id: uuid.UUID | None = Query(None, description="Optional category filter"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ScheduleOccurrence]:
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="end_date must be greater than or equal to start_date",
        )

    stmt = select(Schedule).where(Schedule.user_id == current_user.id)
    if category_id:
        stmt = stmt.where(Schedule.category_id == category_id)

    result = await db.execute(stmt)
    schedules = list(result.scalars().all())

    all_occurrences: list[ScheduleOccurrence] = []
    for sch in schedules:
        expanded = generate_schedule_occurrences(sch, start_date, end_date)
        all_occurrences.extend(expanded)

    all_occurrences.sort(key=lambda occ: occ.start_time)
    return all_occurrences


@router.get(
    "",
    response_model=list[ScheduleResponse],
    status_code=status.HTTP_200_OK,
    summary="List all schedules for the authenticated user",
)
async def list_schedules(
    start_date: datetime | None = Query(
        None, description="Filter schedules starting on or after this timestamp"
    ),
    end_date: datetime | None = Query(
        None, description="Filter schedules ending on or before this timestamp"
    ),
    category_id: uuid.UUID | None = Query(None, description="Filter by category ID"),
    status_filter: str | None = Query(
        None, alias="status", description="Filter by status"
    ),
    is_recurring: bool | None = Query(None, description="Filter by recurrence flag"),
    q: str | None = Query(
        None, description="Search keyword in title, description, or location"
    ),
    sort_by: str = Query(
        "start_time", description="Sort field: start_time, end_time, created_at, title"
    ),
    order: str = Query("asc", description="Sort direction: asc or desc"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Schedule]:
    stmt = select(Schedule).where(Schedule.user_id == current_user.id)

    if q:
        search = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Schedule.title.ilike(search),
                Schedule.description.ilike(search),
                Schedule.location.ilike(search),
            )
        )

    if start_date:
        stmt = stmt.where(Schedule.end_time >= start_date)

    if end_date:
        stmt = stmt.where(Schedule.start_time <= end_date)

    if category_id:
        stmt = stmt.where(Schedule.category_id == category_id)

    if status_filter:
        stmt = stmt.where(Schedule.status == status_filter)

    if is_recurring is not None:
        stmt = stmt.where(Schedule.is_recurring == is_recurring)

    allowed_sort_fields = {
        "start_time": Schedule.start_time,
        "end_time": Schedule.end_time,
        "created_at": Schedule.created_at,
        "title": Schedule.title,
    }
    sort_column = allowed_sort_fields.get(sort_by, Schedule.start_time)
    if order.lower() == "desc":
        stmt = stmt.order_by(sort_column.desc())
    else:
        stmt = stmt.order_by(sort_column.asc())

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get(
    "/{schedule_id}",
    response_model=ScheduleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a schedule by ID",
)
async def get_schedule(
    schedule_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Schedule:
    stmt = select(Schedule).where(
        Schedule.id == schedule_id,
        Schedule.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found",
        )
    return schedule


@router.patch(
    "/{schedule_id}",
    response_model=ScheduleResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a schedule (partial update)",
)
async def update_schedule(
    schedule_id: uuid.UUID,
    schedule_in: ScheduleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Schedule:
    stmt = select(Schedule).where(
        Schedule.id == schedule_id,
        Schedule.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found",
        )

    update_data = schedule_in.model_dump(exclude_unset=True)

    if "category_id" in update_data:
        await _validate_category_ownership(
            update_data["category_id"], current_user.id, db
        )
        schedule.category_id = update_data["category_id"]

    new_start = update_data.get("start_time", schedule.start_time)
    new_end = update_data.get("end_time", schedule.end_time)
    if new_end < new_start:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="end_time must be greater than or equal to start_time",
        )

    if "title" in update_data and update_data["title"] is not None:
        schedule.title = update_data["title"].strip()

    if "description" in update_data:
        schedule.description = update_data["description"]

    if "start_time" in update_data:
        schedule.start_time = update_data["start_time"]

    if "end_time" in update_data:
        schedule.end_time = update_data["end_time"]

    if "is_all_day" in update_data:
        schedule.is_all_day = update_data["is_all_day"]

    if "location" in update_data:
        schedule.location = update_data["location"]

    if "status" in update_data:
        schedule.status = update_data["status"]

    if "is_recurring" in update_data:
        schedule.is_recurring = update_data["is_recurring"]

    if "recurrence_pattern" in update_data:
        pat = update_data["recurrence_pattern"]
        schedule.recurrence_pattern = pat.value if hasattr(pat, "value") else pat

    if (
        "recurrence_interval" in update_data
        and update_data["recurrence_interval"] is not None
    ):
        schedule.recurrence_interval = update_data["recurrence_interval"]

    if "recurrence_end_date" in update_data:
        schedule.recurrence_end_date = update_data["recurrence_end_date"]

    await db.commit()
    await db.refresh(schedule)
    return schedule


@router.post(
    "/{schedule_id}/stop-recurrence",
    response_model=ScheduleResponse,
    status_code=status.HTTP_200_OK,
    summary="Stop recurrence for a recurring schedule",
)
async def stop_recurrence(
    schedule_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Schedule:
    stmt = select(Schedule).where(
        Schedule.id == schedule_id,
        Schedule.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found",
        )

    schedule.is_recurring = False
    schedule.recurrence_end_date = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(schedule)
    return schedule


@router.put(
    "/{schedule_id}",
    response_model=ScheduleResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a schedule (full update)",
)
async def update_schedule_put(
    schedule_id: uuid.UUID,
    schedule_in: ScheduleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Schedule:
    return await update_schedule(
        schedule_id=schedule_id,
        schedule_in=ScheduleUpdate(**schedule_in.model_dump()),
        current_user=current_user,
        db=db,
    )


@router.delete(
    "/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a schedule",
)
async def delete_schedule(
    schedule_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    stmt = select(Schedule).where(
        Schedule.id == schedule_id,
        Schedule.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found",
        )

    await db.delete(schedule)
    await db.commit()
