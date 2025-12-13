"""Pydantic схемы для кейсов."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class CaseCreate(BaseModel):
    """Схема для создания кейса."""
    code: str = Field(..., min_length=1, max_length=50, description="Код кейса (уникальный)")
    title: str = Field(..., min_length=1, max_length=500, description="Название кейса")
    supplier_id: UUID | None = Field(None, description="ID поставщика (опционально)")


class CaseOut(BaseModel):
    """Схема для вывода кейса."""
    id: UUID
    code: str
    title: str
    status: str
    supplier_id: UUID | None
    supplier_name: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

