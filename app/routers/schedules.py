import uuid
from datetime import datetime
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
    ScheduleResponse,
    ScheduleUpdate,
)

router = APIRouter(prefix="/schedules", tags=["Schedules"])


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
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return schedule


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
