"""API роутер для чата с LLM."""
import uuid
from typing import Dict, Any
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.core.settings import settings
from app.models.case import Case
from app.models.supplier import Supplier
from app.models.procurement import CaseCandidate, CommercialOffer
from app.services.agent_tools import validate_procurement
from app.services.supplier_profile import get_supplier_context

router = APIRouter(prefix="/chat", tags=["chat"])


def gather_case_context(db: Session, case_id: uuid.UUID) -> Dict[str, Any]:
    """Собрать контекст кейса из БД (строго факты)."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        return {}
    
    # Базовые данные кейса
    context = {
        "case": {
            "id": str(case.id),
            "code": case.code,
            "title": case.title,
            "status": case.status,
            "procurement_type": case.procurement_type,
            "subject": case.subject,
            "initiator_department": case.initiator_department,
            "planned_deadline": case.planned_deadline.isoformat() if case.planned_deadline else None,
            "procedure_stage": case.procedure_stage,
            "nmc_avg_price": float(case.nmc_avg_price) if case.nmc_avg_price else None,
            "validation_coeff": float(case.validation_coeff) if case.validation_coeff else None,
            "offers_count": case.offers_count,
            "is_validation_ok": case.is_validation_ok,
            "selected_supplier_id": str(case.selected_supplier_id) if case.selected_supplier_id else None,
        }
    }
    
    # Поставщик кейса
    if case.supplier:
        context["case"]["supplier"] = {
            "id": str(case.supplier.id),
            "name": case.supplier.name,
            "inn": case.supplier.inn,
        }
    
    # Кандидаты
    candidates = db.query(CaseCandidate).filter(
        CaseCandidate.case_id == case_id
    ).all()
    
    context["case"]["candidates"] = [
        {
            "id": str(c.id),
            "org_name": c.org_name,
            "inn": c.inn,
            "status": c.status,
            "rank_score": float(c.rank_score) if c.rank_score else None,
        }
        for c in candidates
    ]
    
    # Коммерческие предложения
    offers = db.query(CommercialOffer).filter(
        CommercialOffer.case_id == case_id
    ).all()
    
    context["case"]["commercial_offers"] = [
        {
            "id": str(o.id),
            "candidate_id": str(o.candidate_id),
            "price_total": float(o.price_total),
            "currency": o.currency,
            "lead_time_days": o.lead_time_days,
            "valid_until": o.valid_until.isoformat() if o.valid_until else None,
        }
        for o in offers
    ]
    
    return context


def gather_supplier_context(db: Session, supplier_id: uuid.UUID) -> Dict[str, Any]:
    """Собрать контекст поставщика из БД (строго факты)."""
    try:
        return get_supplier_context(db, supplier_id)
    except HTTPException:
        return {}


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Чат с LLM через Ollama.
    
    Собирает контекст из БД на основе case_id и supplier_id,
    затем отправляет запрос в Ollama.
    """
    context = {}
    missing_data = []
    
    # Собираем контекст кейса
    if request.case_id:
        case_context = gather_case_context(db, request.case_id)
        if case_context:
            context.update(case_context)
        else:
            missing_data.append(f"Кейс с ID {request.case_id} не найден")
    
    # Собираем контекст поставщика
    if request.supplier_id:
        supplier_context = gather_supplier_context(db, request.supplier_id)
        if supplier_context:
            context["supplier"] = supplier_context.get("supplier", {})
            context["supplier_profile"] = supplier_context.get("profile")
            context["supplier_okved"] = supplier_context.get("okved_codes", [])
        else:
            missing_data.append(f"Поставщик с ID {request.supplier_id} не найден")
    
    # Guardrails: если данных нет, отвечаем напрямую
    if missing_data:
        return ChatResponse(
            response=f"Нет данных в системе. Отсутствует: {', '.join(missing_data)}",
            context_used={}
        )
    
    # Если контекст пустой, но нет ошибок - это нормально (общий вопрос)
    # Формируем системный промпт с контекстом
    system_prompt = "Ты помощник для системы управления закупками. Отвечай строго на основе предоставленных фактов из базы данных. Не выдумывай информацию."
    
    if context:
        context_str = f"\n\nКонтекст из базы данных:\n{str(context)}"
        system_prompt += context_str
    
    # Вызываем Ollama
    try:
        async with httpx.AsyncClient(timeout=60.0) as httpx_client:
            ollama_url = f"{settings.ollama_url}/api/chat"
            
            payload = {
                "model": settings.chat_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": request.message}
                ],
                "stream": False
            }
            
            response = await httpx_client.post(ollama_url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            llm_response = result.get("message", {}).get("content", "Ошибка: не получен ответ от LLM")
            
            return ChatResponse(
                response=llm_response,
                context_used=context
            )
    
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Ошибка подключения к Ollama: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обработке запроса: {str(e)}"
        )

