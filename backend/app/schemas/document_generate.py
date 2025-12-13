"""Pydantic схемы для генерации документов."""
from uuid import UUID
from pydantic import BaseModel, Field


class DocumentGenerateRequest(BaseModel):
    """Схема для запроса генерации документа."""
    case_id: UUID = Field(..., description="ID кейса")
    template_key: str = Field(..., description="Ключ шаблона (например, NMC_REFERENCE)")


class DocumentGenerateResponse(BaseModel):
    """Схема для ответа генерации документа."""
    document_id: str = Field(..., description="ID созданного документа")
    status: str = Field(default="DONE", description="Статус генерации")


class ExportZipRequest(BaseModel):
    """Схема для запроса экспорта ZIP."""
    mode: str = Field(default="standard", description="Режим экспорта (standard, full)")


class ExportZipResponse(BaseModel):
    """Схема для ответа экспорта ZIP."""
    document_id: str = Field(..., description="ID созданного ZIP документа")
    status: str = Field(default="DONE", description="Статус экспорта")

