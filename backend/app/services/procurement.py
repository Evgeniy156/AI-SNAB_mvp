"""Сервисы для работы с закупкой (procurement workflow)."""
import uuid
from decimal import Decimal
from typing import Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from app.models.case import Case
from app.models.procurement import (
    CaseCandidate,
    RfqRequest,
    CommercialOffer,
    SupplierSecurityReview
)
from app.models.supplier_profile import SupplierProfile


def compute_candidate_rank(
    db: Session,
    candidate: CaseCandidate
) -> Tuple[Decimal, str]:
    """
    Вычислить ранк-оценку кандидата (MVP правила).
    
    Возвращает (score, explanation).
    """
    score = Decimal('0')
    reasons = []
    
    # Если есть supplier_id, используем профиль
    if candidate.supplier_id:
        profile = db.query(SupplierProfile).filter(
            SupplierProfile.supplier_id == candidate.supplier_id
        ).first()
        
        if profile:
            # +10 если есть СМК
            if profile.has_qms:
                score += Decimal('10')
                reasons.append("+10: есть СМК")
            
            # +10 если работает по ГОЗ
            if profile.works_with_goz:
                score += Decimal('10')
                reasons.append("+10: опыт работы по ГОЗ")
            
            # Опыт поставок: min(10, executed_contracts_count/5)
            if profile.executed_contracts_count:
                exp_bonus = min(10, profile.executed_contracts_count // 5)
                if exp_bonus > 0:
                    score += Decimal(str(exp_bonus))
                    reasons.append(f"+{exp_bonus}: опыт поставок ({profile.executed_contracts_count} контрактов)")
            
            # +5 если есть сертификаты
            from app.models.supplier_profile import SupplierCertificate
            cert_count = db.query(SupplierCertificate).filter(
                SupplierCertificate.supplier_id == candidate.supplier_id
            ).count()
            if cert_count > 0:
                score += Decimal('5')
                reasons.append(f"+5: есть сертификаты ({cert_count})")
            
            # -10 если нет контактов
            if not profile.contact_person and not profile.phone and not profile.email:
                score -= Decimal('10')
                reasons.append("-10: нет контактных данных")
    
    # Если нет supplier_id, но есть контакты в candidate
    else:
        if candidate.contact_email or candidate.contact_phone:
            score += Decimal('5')
            reasons.append("+5: есть контакты")
        else:
            score -= Decimal('10')
            reasons.append("-10: нет контактных данных")
    
    explanation = "; ".join(reasons) if reasons else "Базовый кандидат"
    
    return score, explanation


def recompute_case_pricing(db: Session, case_id: uuid.UUID) -> Dict[str, Any]:
    """
    Пересчитать НМЦ и коэффициент валидации для кейса.
    
    Правила:
    - Берём последнее КП для каждого кандидата
    - avg = mean(prices)
    - coeff = (max - min) / avg
    - ok = coeff <= 0.33 and offers_count >= 3
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Кейс с ID '{case_id}' не найден")
    
    # Получаем последнее КП для каждого кандидата
    subquery = db.query(
        CommercialOffer.candidate_id,
        func.max(CommercialOffer.created_at).label('max_created_at')
    ).filter(
        CommercialOffer.case_id == case_id
    ).group_by(CommercialOffer.candidate_id).subquery()
    
    latest_offers = db.query(CommercialOffer).join(
        subquery,
        (CommercialOffer.candidate_id == subquery.c.candidate_id) &
        (CommercialOffer.created_at == subquery.c.max_created_at)
    ).filter(
        CommercialOffer.case_id == case_id
    ).all()
    
    offers_count = len(latest_offers)
    
    if offers_count == 0:
        case.nmc_avg_price = None
        case.validation_coeff = None
        case.offers_count = 0
        case.is_validation_ok = False
        db.commit()
        return {
            "avg": None,
            "coeff": None,
            "offers_count": 0,
            "ok": False
        }
    
    # Вычисляем среднюю цену
    prices = [offer.price_total for offer in latest_offers]
    avg_price = sum(prices) / len(prices)
    
    # Вычисляем коэффициент валидации
    max_price = max(prices)
    min_price = min(prices)
    coeff = (max_price - min_price) / avg_price if avg_price > 0 else Decimal('0')
    
    # Проверка валидации
    is_ok = coeff <= Decimal('0.33') and offers_count >= 3
    
    # Сохраняем в кейс
    case.nmc_avg_price = avg_price
    case.validation_coeff = coeff
    case.offers_count = offers_count
    case.is_validation_ok = is_ok
    
    # Обновляем stage
    if offers_count >= 3:
        if case.procedure_stage == "RFQ_SENT":
            case.procedure_stage = "OFFERS_COLLECTED"
    
    db.commit()
    
    return {
        "avg": float(avg_price),
        "coeff": float(coeff),
        "offers_count": offers_count,
        "ok": is_ok
    }


def select_supplier_for_case(
    db: Session,
    case_id: uuid.UUID,
    supplier_id: uuid.UUID,
    note: str | None = None
) -> Case:
    """
    Выбрать поставщика-победителя для кейса.
    
    Гейт: требуется APPROVED от СБ.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Кейс с ID '{case_id}' не найден")
    
    # Проверяем, что есть APPROVED от СБ
    security_review = db.query(SupplierSecurityReview).filter(
        SupplierSecurityReview.case_id == case_id,
        SupplierSecurityReview.supplier_id == supplier_id,
        SupplierSecurityReview.status == "APPROVED"
    ).first()
    
    if not security_review:
        raise HTTPException(
            status_code=400,
            detail="Нельзя выбрать поставщика без APPROVED от СБ. Сначала получите одобрение службы безопасности."
        )
    
    # Обновляем кейс
    case.selected_supplier_id = supplier_id
    case.selection_note = note
    case.procedure_stage = "SUPPLIER_SELECTED"
    case.supplier_id = supplier_id  # Также обновляем основное поле для совместимости
    
    db.commit()
    db.refresh(case)
    
    return case


def add_candidate_to_case(
    db: Session,
    case_id: uuid.UUID,
    supplier_id: uuid.UUID | None = None,
    org_name: str | None = None,
    inn: str | None = None,
    contact_email: str | None = None,
    contact_phone: str | None = None
) -> CaseCandidate:
    """
    Добавить кандидата в закупку.
    
    Валидация: либо supplier_id, либо org_name должны быть указаны.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Кейс с ID '{case_id}' не найден")
    
    if not supplier_id and not org_name:
        raise HTTPException(status_code=400, detail="Необходимо указать либо supplier_id, либо org_name")
    
    # Если указан supplier_id, получаем название из supplier
    if supplier_id:
        from app.models.supplier import Supplier
        supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
        if not supplier:
            raise HTTPException(status_code=404, detail=f"Поставщик с ID '{supplier_id}' не найден")
        org_name = supplier.name
        
        # Проверяем, нет ли уже такого кандидата
        existing = db.query(CaseCandidate).filter(
            CaseCandidate.case_id == case_id,
            CaseCandidate.supplier_id == supplier_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Этот поставщик уже добавлен как кандидат")
    else:
        # Проверяем, нет ли уже кандидата с таким org_name
        existing = db.query(CaseCandidate).filter(
            CaseCandidate.case_id == case_id,
            CaseCandidate.supplier_id.is_(None),
            CaseCandidate.org_name == org_name
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Организация с таким названием уже добавлена")
    
    candidate = CaseCandidate(
        case_id=case_id,
        supplier_id=supplier_id,
        org_name=org_name,
        inn=inn,
        contact_email=contact_email,
        contact_phone=contact_phone
    )
    db.add(candidate)
    db.flush()
    
    # Вычисляем ранк
    score, explanation = compute_candidate_rank(db, candidate)
    candidate.rank_score = score
    candidate.rank_explanation = explanation
    
    db.commit()
    db.refresh(candidate)
    
    return candidate


def recompute_all_candidates_rank(db: Session, case_id: uuid.UUID) -> None:
    """Пересчитать ранк для всех кандидатов кейса."""
    candidates = db.query(CaseCandidate).filter(
        CaseCandidate.case_id == case_id
    ).all()
    
    for candidate in candidates:
        score, explanation = compute_candidate_rank(db, candidate)
        candidate.rank_score = score
        candidate.rank_explanation = explanation
    
    db.commit()

