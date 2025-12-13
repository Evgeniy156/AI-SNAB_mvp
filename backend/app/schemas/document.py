"""Pydantic схемы для документов."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class DocumentOut(BaseModel):
    """Схема для вывода документа."""
    id: UUID
    case_id: UUID
    case_code: str | None
    category_id: UUID
    category_key: str | None
    category_name: str | None
    original_filename: str
    storage_bucket: str
    storage_key: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

