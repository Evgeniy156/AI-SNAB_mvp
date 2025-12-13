"""API роутер для категорий документов."""
from typing import List
import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.document_category import CategoryCreate, CategoryOut
from app.services.document_category import list_categories, create_category, archive_category, delete_category

router = APIRouter(prefix="/document-categories", tags=["document-categories"])


@router.get("", response_model=List[CategoryOut])
def get_categories(
    include_inactive: bool = Query(False, description="Включить неактивные категории"),
    db: Session = Depends(get_db)
):
    """Получить список категорий документов."""
    return list_categories(db, include_inactive=include_inactive)


@router.post("", response_model=CategoryOut, status_code=201)
def create_category_endpoint(
    category_data: CategoryCreate,
    db: Session = Depends(get_db)
):
    """Создать новую категорию."""
    category = create_category(
        db=db,
        name=category_data.name,
        key=category_data.key,
        is_active=category_data.is_active,
    )
    return category


@router.post("/{category_id}/archive", response_model=CategoryOut)
def archive_category_endpoint(
    category_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Архивировать категорию (is_active=False)."""
    return archive_category(db, category_id)


@router.delete("/{category_id}")
def delete_category_endpoint(
    category_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Удалить категорию (только если не используется)."""
    delete_category(db, category_id)
    return {"message": "Категория удалена"}

