"""API роутер для кейсов."""
from typing import List, Dict, Any
import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.case import CaseCreate, CaseOut
from app.services.cases import list_cases, create_case
from app.services.procurement import (
    recompute_case_pricing,
    select_supplier_for_case,
    add_candidate_to_case
)
from app.models.case import Case
from app.models.procurement import RfqRequest, CommercialOffer
from app.schemas.document_generate import ExportZipRequest, ExportZipResponse
from app.services.agent_tools import export_zip

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("", response_model=List[CaseOut])
def get_cases(db: Session = Depends(get_db)):
    """Получить список всех кейсов."""
    cases = list_cases(db)
    # Преобразуем в CaseOut с supplier_name
    result = []
    for case in cases:
        case_dict = {
            "id": case.id,
            "code": case.code,
            "title": case.title,
            "status": case.status,
            "supplier_id": case.supplier_id,
            "supplier_name": case.supplier.name if case.supplier else None,
            "created_at": case.created_at,
            "updated_at": case.updated_at,
        }
        result.append(CaseOut(**case_dict))
    return result


@router.post("", response_model=CaseOut, status_code=201)
def create_case_endpoint(
    case_data: CaseCreate,
    db: Session = Depends(get_db)
):
    """Создать новый кейс."""
    case = create_case(
        db=db,
        code=case_data.code,
        title=case_data.title,
        supplier_id=case_data.supplier_id,
    )
    # Преобразуем в CaseOut
    return CaseOut(
        id=case.id,
        code=case.code,
        title=case.title,
        status=case.status,
        supplier_id=case.supplier_id,
        supplier_name=case.supplier.name if case.supplier else None,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


@router.get("/{case_id}/pricing", response_class=JSONResponse)
def get_case_pricing(
    case_id: uuid.UUID,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Получить расчёт НМЦ и коэффициент валидации для кейса."""
    return recompute_case_pricing(db, case_id)


@router.post("/{case_id}/offers", response_class=JSONResponse, status_code=201)
def create_offer(
    case_id: uuid.UUID,
    candidate_id: uuid.UUID,
    price_total: float,
    currency: str = "RUB",
    lead_time_days: int | None = None,
    delivery_terms: str | None = None,
    payment_terms: str | None = None,
    valid_until: str | None = None,
    document_id: uuid.UUID | None = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Создать коммерческое предложение."""
    from decimal import Decimal
    from datetime import datetime, date
    from app.models.procurement import CaseCandidate, CommercialOffer
    
    candidate = db.query(CaseCandidate).filter(
        CaseCandidate.id == candidate_id,
        CaseCandidate.case_id == case_id
    ).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Кандидат не найден")
    
    valid_until_date = None
    if valid_until:
        try:
            valid_until_date = datetime.strptime(valid_until, "%Y-%m-%d").date()
        except ValueError:
            pass
    
    offer = CommercialOffer(
        case_id=case_id,
        candidate_id=candidate_id,
        supplier_id=candidate.supplier_id,
        price_total=Decimal(str(price_total)),
        currency=currency,
        lead_time_days=lead_time_days,
        valid_until=valid_until_date,
        delivery_terms=delivery_terms,
        payment_terms=payment_terms,
        document_id=document_id
    )
    db.add(offer)
    candidate.status = "OFFER_RECEIVED"
    db.commit()
    
    # Пересчитываем НМЦ
    pricing = recompute_case_pricing(db, case_id)
    
    return {
        "id": str(offer.id),
        "pricing": pricing
    }


@router.post("/{case_id}/rfq", response_class=JSONResponse, status_code=201)
def create_rfq(
    case_id: uuid.UUID,
    candidate_id: uuid.UUID,
    channel: str,
    result: str = "SENT",
    notes: str | None = None,
    evidence_document_id: uuid.UUID | None = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Создать запись об отправке запроса КП."""
    from datetime import datetime
    from app.models.procurement import CaseCandidate
    
    candidate = db.query(CaseCandidate).filter(
        CaseCandidate.id == candidate_id,
        CaseCandidate.case_id == case_id
    ).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Кандидат не найден")
    
    rfq = RfqRequest(
        case_id=case_id,
        candidate_id=candidate_id,
        channel=channel,
        result=result,
        notes=notes,
        evidence_document_id=evidence_document_id
    )
    db.add(rfq)
    
    # Обновляем статус кандидата
    if result == "RECEIVED_OFFER":
        candidate.status = "OFFER_RECEIVED"
    elif result == "REFUSAL":
        candidate.status = "REFUSED"
    elif result == "NO_RESPONSE":
        candidate.status = "NO_RESPONSE"
    else:
        candidate.status = "RFQ_SENT"
    
    # Обновляем stage кейса
    case = db.query(Case).filter(Case.id == case_id).first()
    if case and case.procedure_stage == "DRAFT":
        case.procedure_stage = "RFQ_SENT"
    
    db.commit()
    
    return {
        "id": str(rfq.id),
        "candidate_id": str(candidate_id),
        "channel": channel,
        "result": result
    }


@router.post("/{case_id}/select-supplier", response_class=JSONResponse)
def select_supplier(
    case_id: uuid.UUID,
    supplier_id: uuid.UUID,
    note: str | None = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Выбрать поставщика-победителя для кейса."""
    case = select_supplier_for_case(db, case_id, supplier_id, note)
    return {
        "case_id": str(case.id),
        "selected_supplier_id": str(case.selected_supplier_id),
        "procedure_stage": case.procedure_stage
    }


@router.post("/{case_id}/export-zip", response_model=ExportZipResponse, status_code=201)
def export_zip_endpoint(
    case_id: uuid.UUID,
    request: ExportZipRequest,
    db: Session = Depends(get_db)
):
    """Экспортировать кейс в ZIP архив."""
    result = export_zip(db, case_id, request.mode)
    
    if not result["ok"]:
        raise HTTPException(
            status_code=400,
            detail=result.get("reason", "Ошибка экспорта ZIP")
        )
    
    return ExportZipResponse(
        document_id=result["document_id"],
        status="DONE"
    )

