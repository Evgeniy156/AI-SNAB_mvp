"""Сервис для активации закупки на основе заполнения основания."""
import uuid
from datetime import datetime
from typing import Tuple, List
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.case import Case
from app.models.case_checklist import CaseChecklistItem
from app.services.checklist import split_checklist_items_by_basis, get_case_checklist_with_documents


def get_basis_items(db: Session, case_id: uuid.UUID) -> List[CaseChecklistItem]:
    """
    Получить пункты основания закупки.
    
    Основание = checklist items, у которых:
    - group_title содержит "Основание закупки"
    - или section "I" (fallback)
    """
    all_items = get_case_checklist_with_documents(db, case_id)
    basis_items, _ = split_checklist_items_by_basis(all_items)
    return basis_items


def validate_basis_ready(db: Session, case_id: uuid.UUID) -> Tuple[bool, List[str]]:
    """
    Проверяет готовность основания закупки для активации.
    
    Для каждого обязательного пункта основания (is_required=true):
    - doc_number не пустой
    - doc_date не пустая
    - есть хотя бы 1 прикреплённый документ
    
    Возвращает (ok: bool, errors: list[str]).
    """
    basis_items = get_basis_items(db, case_id)
    errors = []
    
    for item in basis_items:
        if not item.template_item:
            continue
        
        # Проверяем только обязательные пункты
        if not item.template_item.is_required:
            continue
        
        item_title = item.template_item.title
        
        # Проверка номера документа
        if not item.doc_number or not item.doc_number.strip():
            errors.append(f"Нет номера документа для: {item_title}")
        
        # Проверка даты документа
        if not item.doc_date:
            errors.append(f"Нет даты документа для: {item_title}")
        
        # Проверка прикреплённых документов
        if not item.documents or len(item.documents) == 0:
            errors.append(f"Не прикреплён документ для: {item_title}")
    
    return len(errors) == 0, errors


def activate_case(db: Session, case_id: uuid.UUID) -> Case:
    """
    Активирует закупку после проверки готовности основания.
    
    Вызывает validate_basis_ready.
    Если ok=false → бросает HTTPException(400) с понятным текстом.
    Если ok=true → ставит is_activated=true, activated_at=now().
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Кейс с ID '{case_id}' не найден")
    
    if case.is_activated:
        return case  # Уже активирована
    
    # Проверяем готовность основания
    ok, errors = validate_basis_ready(db, case_id)
    
    if not ok:
        error_text = "Нельзя активировать закупку. Ошибки:\n" + "\n".join(f"- {e}" for e in errors)
        raise HTTPException(status_code=400, detail=error_text)
    
    # Активируем
    case.is_activated = True
    case.activated_at = datetime.utcnow()
    
    # Обновляем статус и stage
    if case.status == "DRAFT":
        case.status = "ACTIVE"
    if case.procedure_stage == "DRAFT":
        case.procedure_stage = "RFQ_SENT"
    
    db.commit()
    db.refresh(case)
    
    return case

