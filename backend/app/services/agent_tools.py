"""Инструменты агента для работы с закупками."""
import uuid
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.case import Case
from app.models.procurement import (
    CaseCandidate,
    CommercialOffer,
    SupplierSecurityReview
)


def validate_procurement(db: Session, case_id: uuid.UUID) -> Dict[str, Any]:
    """
    Валидация закупки: проверка наличия необходимых данных.
    
    Возвращает:
    {
        "ok": bool,
        "missing": List[str],  # Что отсутствует
        "blockers": List[str]  # Критические проблемы, блокирующие процесс
    }
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        return {
            "ok": False,
            "missing": [f"Кейс с ID {case_id} не найден"],
            "blockers": [f"Кейс с ID {case_id} не найден"]
        }
    
    missing = []
    blockers = []
    
    # Базовые данные кейса
    if not case.subject:
        missing.append("Предмет закупки (subject)")
        blockers.append("Не указан предмет закупки")
    
    if not case.initiator_department:
        missing.append("Инициатор (initiator_department)")
    
    if not case.planned_deadline:
        missing.append("Плановый срок (planned_deadline)")
    
    # Кандидаты
    candidates_count = db.query(CaseCandidate).filter(
        CaseCandidate.case_id == case_id
    ).count()
    
    if candidates_count == 0:
        missing.append("Кандидаты (candidates)")
        blockers.append("Нет кандидатов для закупки")
    
    # Коммерческие предложения
    offers_count = db.query(CommercialOffer).filter(
        CommercialOffer.case_id == case_id
    ).count()
    
    if offers_count == 0:
        missing.append("Коммерческие предложения (commercial_offers)")
    elif offers_count < 3:
        missing.append(f"Недостаточно КП: {offers_count} из 3 минимум")
    
    # Валидация НМЦ
    if not case.is_validation_ok:
        if case.offers_count < 3:
            blockers.append(f"Недостаточно КП для валидации НМЦ: {case.offers_count} из 3")
        elif case.validation_coeff and case.validation_coeff > 0.33:
            blockers.append(f"Коэффициент валидации слишком высокий: {case.validation_coeff} (максимум 0.33)")
        else:
            missing.append("Валидация НМЦ не пройдена")
    
    # Проверка СБ (если выбран поставщик)
    if case.selected_supplier_id:
        security_review = db.query(SupplierSecurityReview).filter(
            SupplierSecurityReview.case_id == case_id,
            SupplierSecurityReview.supplier_id == case.selected_supplier_id
        ).first()
        
        if not security_review:
            blockers.append("Нет проверки СБ для выбранного поставщика")
        elif security_review.status != "APPROVED":
            blockers.append(f"Проверка СБ не пройдена: статус {security_review.status}")
    
    ok = len(blockers) == 0
    
    return {
        "ok": ok,
        "missing": missing,
        "blockers": blockers
    }


def export_zip(case_id: uuid.UUID, mode: str = "full") -> Dict[str, Any]:
    """
    Экспорт кейса в ZIP архив.
    
    Args:
        case_id: ID кейса
        mode: Режим экспорта ("full", "documents", "summary")
    
    Returns:
        {"ok": bool, "reason": str}
    """
    return {
        "ok": False,
        "reason": "not implemented"
    }


def generate_doc(template_key: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Генерация документа по шаблону.
    
    Args:
        template_key: Ключ шаблона
        context: Контекст для заполнения шаблона
    
    Returns:
        {"ok": bool, "document_id": str | None, "reason": str | None}
    """
    return {
        "ok": False,
        "document_id": None,
        "reason": "not implemented"
    }

