"""Сервис для работы с чек-листами закупочных процедур."""
from typing import List
from datetime import date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
import uuid
from app.models.checklist_template import ChecklistTemplate, ChecklistTemplateItem
from app.models.case_checklist import CaseChecklistItem
from app.models.case import Case


def ensure_case_checklist(db: Session, case_id: uuid.UUID) -> List[CaseChecklistItem]:
    """
    Применяет шаблон чек-листа к кейсу (lazy init).
    
    Использует checklist_template_id из кейса, если указан.
    Иначе находит default template (is_default=true AND is_active=true).
    Создает case_checklist_items для всех template_items, если их еще нет.
    
    Возвращает список CaseChecklistItem с загруженными template_item.
    """
    # Проверяем существование кейса
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise ValueError(f"Кейс с ID {case_id} не найден")
    
    # Определяем шаблон: сначала из кейса, потом default
    template = None
    if case.checklist_template_id:
        template = db.query(ChecklistTemplate).filter(
            ChecklistTemplate.id == case.checklist_template_id
        ).first()
    
    if not template:
        # Находим default template
        template = db.query(ChecklistTemplate).filter(
            and_(
                ChecklistTemplate.is_default == True,
                ChecklistTemplate.is_active == True
            )
        ).first()
    
    if not template:
        return []  # Нет шаблона - возвращаем пустой список
    
    # Получаем все template_items по sort_order
    template_items = db.query(ChecklistTemplateItem).filter(
        ChecklistTemplateItem.template_id == template.id
    ).order_by(ChecklistTemplateItem.sort_order).all()
    
    # Получаем существующие case_checklist_items для этого кейса
    existing_items = {
        item.template_item_id: item
        for item in db.query(CaseChecklistItem).filter(
            CaseChecklistItem.case_id == case_id
        ).all()
    }
    
    # Создаем недостающие items
    created_items = []
    for template_item in template_items:
        if template_item.id not in existing_items:
            case_item = CaseChecklistItem(
                case_id=case_id,
                template_item_id=template_item.id,
                status="TODO"
            )
            db.add(case_item)
            created_items.append(case_item)
    
    if created_items:
        db.commit()
        # Перезагружаем с relationships
        for item in created_items:
            db.refresh(item)
    
    # Возвращаем все items с загруженными template_item
    all_items = db.query(CaseChecklistItem).options(
        joinedload(CaseChecklistItem.template_item)
    ).filter(
        CaseChecklistItem.case_id == case_id
    ).all()
    
    # Сортируем по sort_order template_item
    all_items.sort(key=lambda x: x.template_item.sort_order if x.template_item else 999)
    
    return all_items


def get_case_checklist_with_documents(
    db: Session,
    case_id: uuid.UUID,
    status_filter: str | None = None
) -> List[CaseChecklistItem]:
    """
    Получает чек-лист кейса с документами, опционально фильтруя по статусу.
    
    status_filter: None (все), "TODO", "DONE", "NA"
    """
    # Убеждаемся, что чек-лист инициализирован
    ensure_case_checklist(db, case_id)
    
    # Загружаем items с relationships
    from app.models.case_checklist import CaseChecklistItemDocument
    query = db.query(CaseChecklistItem).options(
        joinedload(CaseChecklistItem.template_item),
        joinedload(CaseChecklistItem.documents).joinedload(CaseChecklistItemDocument.document)
    ).filter(
        CaseChecklistItem.case_id == case_id
    )
    
    if status_filter and status_filter in ("TODO", "DONE", "NA"):
        query = query.filter(CaseChecklistItem.status == status_filter)
    
    items = query.all()
    
    # Сортируем по sort_order template_item
    items.sort(key=lambda x: x.template_item.sort_order if x.template_item else 999)
    
    return items


def split_checklist_items_by_basis(items: List[CaseChecklistItem]) -> tuple[List[CaseChecklistItem], List[CaseChecklistItem]]:
    """
    Разделяет пункты чек-листа на основание закупки и остальные.
    
    Возвращает (basis_items, other_items).
    
    Критерий для "Основание закупки":
    - group_title содержит "Основание закупки"
    - или section == "I" (fallback)
    """
    basis_items = []
    other_items = []
    
    for item in items:
        if not item.template_item:
            other_items.append(item)
            continue
        
        is_basis = False
        
        # Проверяем group_title
        if item.template_item.group_title:
            if "основание закупки" in item.template_item.group_title.lower():
                is_basis = True
        
        # Fallback: проверяем section
        if not is_basis and item.template_item.section:
            if item.template_item.section.strip().upper() in ("I", "1"):
                is_basis = True
        
        if is_basis:
            basis_items.append(item)
        else:
            other_items.append(item)
    
    return basis_items, other_items


def update_checklist_item_status(
    db: Session,
    case_id: uuid.UUID,
    checklist_item_id: uuid.UUID,
    status: str,
    comment: str | None = None,
    doc_number: str | None = None,
    doc_date: date | None = None
) -> CaseChecklistItem:
    """
    Обновляет статус, комментарий, номер и дату документа пункта чек-листа.
    
    Валидация: item должен принадлежать case_id, status должен быть в допустимых значениях.
    """
    if status not in ("TODO", "DONE", "NA"):
        raise ValueError(f"Недопустимый статус: {status}")
    
    item = db.query(CaseChecklistItem).filter(
        and_(
            CaseChecklistItem.id == checklist_item_id,
            CaseChecklistItem.case_id == case_id
        )
    ).first()
    
    if not item:
        raise ValueError(f"Пункт чек-листа не найден или не принадлежит кейсу")
    
    item.status = status
    if comment is not None:
        item.comment = comment
    if doc_number is not None:
        item.doc_number = doc_number if doc_number.strip() else None
    if doc_date is not None:
        item.doc_date = doc_date
    
    db.commit()
    db.refresh(item)
    return item


def attach_document_to_checklist_item(
    db: Session,
    case_id: uuid.UUID,
    checklist_item_id: uuid.UUID,
    document_id: uuid.UUID
) -> None:
    """
    Прикрепляет документ к пункту чек-листа.
    
    Валидация: item и document должны принадлежать case_id.
    Идемпотентно: если связь уже есть, ничего не делает.
    """
    from app.models.document import Document
    from app.models.case_checklist import CaseChecklistItemDocument
    
    # Проверяем, что item принадлежит кейсу
    item = db.query(CaseChecklistItem).filter(
        and_(
            CaseChecklistItem.id == checklist_item_id,
            CaseChecklistItem.case_id == case_id
        )
    ).first()
    
    if not item:
        raise ValueError(f"Пункт чек-листа не найден или не принадлежит кейсу")
    
    # Проверяем, что document принадлежит кейсу
    document = db.query(Document).filter(
        and_(
            Document.id == document_id,
            Document.case_id == case_id
        )
    ).first()
    
    if not document:
        raise ValueError(f"Документ не найден или не принадлежит кейсу")
    
    # Проверяем, нет ли уже связи
    existing = db.query(CaseChecklistItemDocument).filter(
        and_(
            CaseChecklistItemDocument.case_checklist_item_id == checklist_item_id,
            CaseChecklistItemDocument.document_id == document_id
        )
    ).first()
    
    if existing:
        return  # Уже прикреплен, идемпотентно
    
    # Создаем связь
    link = CaseChecklistItemDocument(
        case_checklist_item_id=checklist_item_id,
        document_id=document_id
    )
    db.add(link)
    db.commit()


def detach_document_from_checklist_item(
    db: Session,
    case_id: uuid.UUID,
    checklist_item_id: uuid.UUID,
    document_id: uuid.UUID
) -> None:
    """
    Открепляет документ от пункта чек-листа.
    
    Валидация: item должен принадлежать case_id.
    """
    from app.models.case_checklist import CaseChecklistItemDocument
    
    # Проверяем, что item принадлежит кейсу
    item = db.query(CaseChecklistItem).filter(
        and_(
            CaseChecklistItem.id == checklist_item_id,
            CaseChecklistItem.case_id == case_id
        )
    ).first()
    
    if not item:
        raise ValueError(f"Пункт чек-листа не найден или не принадлежит кейсу")
    
    # Удаляем связь
    link = db.query(CaseChecklistItemDocument).filter(
        and_(
            CaseChecklistItemDocument.case_checklist_item_id == checklist_item_id,
            CaseChecklistItemDocument.document_id == document_id
        )
    ).first()
    
    if link:
        db.delete(link)
        db.commit()

