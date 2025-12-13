"""Pydantic схемы для поставщиков."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class SupplierCreate(BaseModel):
    """Схема для создания поставщика."""
    name: str = Field(..., min_length=1, max_length=255, description="Название поставщика")
    inn: str | None = Field(None, max_length=12, description="ИНН")
    kpp: str | None = Field(None, max_length=9, description="КПП")
    address_index: str | None = Field(None, max_length=10, description="Почтовый индекс")
    address: str | None = Field(None, max_length=500, description="Адрес")


class SupplierOut(BaseModel):
    """Схема для вывода поставщика."""
    id: UUID
    name: str
    inn: str | None
    kpp: str | None
    address_index: str | None
    address: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

