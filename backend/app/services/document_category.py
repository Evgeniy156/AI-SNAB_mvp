"""Service слой для работы с категориями документов."""
from typing import List
import re
import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.document_category import DocumentCategory
from app.models.document import Document


def generate_key_from_name(name: str) -> str:
    """Генерирует key из name: uppercase, пробелы/дефисы -> underscore, убрать спецсимволы."""
    # Нормализуем: uppercase, заменяем пробелы и дефисы на underscore
    key = re.sub(r'[\s\-]+', '_', name.upper())
    # Убираем все спецсимволы, оставляем только буквы, цифры и underscore
    key = re.sub(r'[^A-Z0-9_]', '', key)
    # Убираем множественные подчеркивания
    key = re.sub(r'_+', '_', key)
    # Убираем подчеркивания в начале и конце
    key = key.strip('_')
    return key if key else 'CATEGORY'


def find_unique_key(db: Session, base_key: str) -> str:
    """Находит уникальный key, добавляя суффикс _2, _3... если нужно."""
    key = base_key
    counter = 1
    while db.query(DocumentCategory).filter(DocumentCategory.key == key).first():
        counter += 1
        key = f"{base_key}_{counter}"
    return key


def list_categories(db: Session, include_inactive: bool = False) -> List[DocumentCategory]:
    """Получить список категорий."""
    query = db.query(DocumentCategory)
    if not include_inactive:
        query = query.filter(DocumentCategory.is_active == True)
    return query.order_by(DocumentCategory.name).all()


def create_category(db: Session, name: str, key: str | None = None, is_active: bool = True) -> DocumentCategory:
    """Создать новую категорию."""
    # Генерируем key если не передан
    if not key:
        key = generate_key_from_name(name)
    else:
        key = key.upper()
    
    # Проверяем уникальность и находим свободный key
    key = find_unique_key(db, key)
    
    category = DocumentCategory(
        key=key,
        name=name,
        is_active=is_active,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def archive_category(db: Session, category_id: uuid.UUID) -> DocumentCategory:
    """Архивировать категорию (is_active=False)."""
    category = db.query(DocumentCategory).filter(DocumentCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    
    category.is_active = False
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: uuid.UUID) -> None:
    """Удалить категорию (только если не используется)."""
    category = db.query(DocumentCategory).filter(DocumentCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    
    # Проверяем, используется ли категория
    doc_count = db.query(Document).filter(Document.category_id == category_id).count()
    if doc_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Категория используется {doc_count} документом(ами). Архивируйте её вместо удаления."
        )
    
    db.delete(category)
    db.commit()

