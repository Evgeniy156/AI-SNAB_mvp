"""Service слой для работы с кейсами."""
from typing import List
import uuid
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from app.models.case import Case
from app.models.supplier import Supplier


def list_cases(db: Session) -> List[Case]:
    """Получить список всех кейсов, отсортированных по дате создания (новые первые), с подгрузкой supplier."""
    return (
        db.query(Case)
        .options(joinedload(Case.supplier))
        .order_by(Case.created_at.desc())
        .all()
    )


def get_case(db: Session, case_id: uuid.UUID) -> Case:
    """Получить кейс по ID с подгрузкой supplier."""
    case = (
        db.query(Case)
        .options(joinedload(Case.supplier))
        .filter(Case.id == case_id)
        .first()
    )
    if not case:
        raise HTTPException(status_code=404, detail=f"Кейс с ID '{case_id}' не найден")
    return case


def get_case_by_code(db: Session, code: str) -> Case:
    """Получить кейс по коду с подгрузкой supplier."""
    case = (
        db.query(Case)
        .options(joinedload(Case.supplier))
        .filter(Case.code == code)
        .first()
    )
    if not case:
        raise HTTPException(status_code=404, detail=f"Кейс с кодом '{code}' не найден")
    return case


def create_case(db: Session, code: str, title: str, supplier_id: uuid.UUID | str | None = None) -> Case:
    """Создать новый кейс. Проверяет уникальность code."""
    # Проверяем уникальность code
    existing = db.query(Case).filter(Case.code == code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Кейс с кодом '{code}' уже существует")
    
    # Преобразуем supplier_id в UUID если это строка
    supplier_uuid = None
    if supplier_id:
        if isinstance(supplier_id, str):
            supplier_uuid = uuid.UUID(supplier_id)
        else:
            supplier_uuid = supplier_id
    
    case = Case(
        code=code,
        title=title,
        supplier_id=supplier_uuid,
    )
    db.add(case)
    try:
        db.commit()
        db.refresh(case)
        # Подгружаем supplier для возврата
        if case.supplier_id:
            db.refresh(case, ["supplier"])
        return case
    except IntegrityError as e:
        db.rollback()
        if "unique constraint" in str(e).lower() or "duplicate key" in str(e).lower():
            raise HTTPException(status_code=400, detail=f"Кейс с кодом '{code}' уже существует")
        raise HTTPException(status_code=400, detail=f"Ошибка создания кейса: {str(e)}")

