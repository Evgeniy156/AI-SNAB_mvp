"""Pydantic схемы для категорий документов."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
import re


class CategoryCreate(BaseModel):
    """Схема для создания категории."""
    name: str = Field(..., min_length=1, max_length=255, description="Название категории")
    key: str | None = Field(None, max_length=50, description="Машинный ключ (опционально, генерируется из name)")
    is_active: bool = Field(True, description="Активна ли категория")

    @field_validator("key")
    @classmethod
    def normalize_key(cls, v: str | None) -> str | None:
        """Нормализует key в uppercase."""
        if v:
            return v.upper()
        return v


class CategoryOut(BaseModel):
    """Схема для вывода категории."""
    id: UUID
    key: str
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

