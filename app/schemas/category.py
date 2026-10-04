import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Category name")
    color: str | None = Field(
        default=None, max_length=20, description="Hex color code or name"
    )
    icon: str | None = Field(
        default=None, max_length=50, description="Icon name or identifier"
    )


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = Field(
        default=None, min_length=1, max_length=100, description="Category name"
    )
    color: str | None = Field(
        default=None, max_length=20, description="Hex color code or name"
    )
    icon: str | None = Field(
        default=None, max_length=50, description="Icon name or identifier"
    )


class CategoryResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    color: str | None = None
    icon: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "CategoryBase",
    "CategoryCreate",
    "CategoryUpdate",
    "CategoryResponse",
]
