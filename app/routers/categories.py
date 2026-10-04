import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.category import Category
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new category",
)
async def create_category(
    category_in: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Category:
    name_clean = category_in.name.strip()
    query = select(Category).where(
        Category.user_id == current_user.id,
        Category.name == name_clean,
    )
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category with name '{name_clean}' already exists",
        )

    category = Category(
        user_id=current_user.id,
        name=name_clean,
        color=category_in.color,
        icon=category_in.icon,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@router.get(
    "",
    response_model=list[CategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="List all categories for the authenticated user",
)
async def list_categories(
    q: str | None = Query(None, description="Search category by name substring"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Category]:
    stmt = select(Category).where(Category.user_id == current_user.id)
    if q:
        stmt = stmt.where(Category.name.ilike(f"%{q.strip()}%"))
    stmt = stmt.order_by(Category.name.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a category by ID",
)
async def get_category(
    category_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Category:
    stmt = select(Category).where(
        Category.id == category_id,
        Category.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return category


@router.patch(
    "/{category_id}",
    response_model=CategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a category (partial update)",
)
async def update_category(
    category_id: uuid.UUID,
    category_in: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Category:
    stmt = select(Category).where(
        Category.id == category_id,
        Category.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    update_data = category_in.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"] is not None:
        name_clean = update_data["name"].strip()
        conflict_stmt = select(Category).where(
            Category.user_id == current_user.id,
            Category.name == name_clean,
            Category.id != category_id,
        )
        conflict = (await db.execute(conflict_stmt)).scalar_one_or_none()
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Category with name '{name_clean}' already exists",
            )
        category.name = name_clean

    if "color" in update_data:
        category.color = update_data["color"]

    if "icon" in update_data:
        category.icon = update_data["icon"]

    await db.commit()
    await db.refresh(category)
    return category


@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a category (full update)",
)
async def update_category_put(
    category_id: uuid.UUID,
    category_in: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Category:
    return await update_category(
        category_id=category_id,
        category_in=CategoryUpdate(**category_in.model_dump()),
        current_user=current_user,
        db=db,
    )


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a category",
)
async def delete_category(
    category_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    stmt = select(Category).where(
        Category.id == category_id,
        Category.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    await db.delete(category)
    await db.commit()
