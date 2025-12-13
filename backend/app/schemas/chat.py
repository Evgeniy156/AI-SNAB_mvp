"""Pydantic схемы для чата."""
from uuid import UUID
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Схема для запроса чата."""
    message: str = Field(..., min_length=1, description="Сообщение пользователя")
    case_id: UUID | None = Field(None, description="ID кейса (опционально)")
    supplier_id: UUID | None = Field(None, description="ID поставщика (опционально)")


class ChatResponse(BaseModel):
    """Схема для ответа чата."""
    response: str = Field(..., description="Ответ от LLM")
    context_used: dict = Field(default_factory=dict, description="Использованный контекст из БД")

