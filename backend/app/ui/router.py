from fastapi import APIRouter, Request, Form, Depends, UploadFile, File, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.suppliers import list_suppliers, create_supplier
from app.services.supplier_profile import (
    get_or_create_supplier_profile,
    update_supplier_profile,
    set_supplier_okved,
    get_supplier_okved,
    add_supplier_equipment,
    delete_supplier_equipment,
    add_supplier_certificate,
    delete_supplier_certificate
)
from app.services.cases import list_cases, create_case, get_case, get_case_by_code
from app.services.documents import list_documents, create_document_with_file
from app.services.document_category import list_categories, create_category, archive_category
from app.services.checklist import (
    get_case_checklist_with_documents,
    update_checklist_item_status,
    attach_document_to_checklist_item,
    detach_document_from_checklist_item,
    split_checklist_items_by_basis
)
from app.services.procurement import (
    recompute_case_pricing,
    recompute_all_candidates_rank,
    add_candidate_to_case,
    select_supplier_for_case
)
from app.services.procurement_activation import (
    validate_basis_ready,
    activate_case
)
from app.models.procurement import (
    CaseCandidate,
    RfqRequest,
    CommercialOffer,
    SupplierSecurityReview
)
from app.models.case import Case
from app.models.supplier import Supplier
from app.models.document_category import DocumentCategory
from app.models.supplier_profile import SupplierEquipment, SupplierCertificate
from fastapi.exceptions import HTTPException
import uuid

templates = Jinja2Templates(directory="app/templates")
ui_router = APIRouter(prefix="/ui", tags=["ui"])


@ui_router.get("/chat", response_class=HTMLResponse)
def ui_chat(request: Request):
    """Страница для тестирования чата с LLM."""
    return templates.TemplateResponse(request, "ui_chat.html")


@ui_router.get("", response_class=HTMLResponse)
def ui_home(request: Request):
    return templates.TemplateResponse(request, "ui_home.html")


@ui_router.get("/suppliers", response_class=HTMLResponse)
def ui_suppliers(request: Request, db: Session = Depends(get_db)):
    """Страница списка поставщиков."""
    suppliers = list_suppliers(db)
    return templates.TemplateResponse(
        request,
        "ui_suppliers.html",
        {"suppliers": suppliers}
    )


@ui_router.post("/suppliers", response_class=HTMLResponse)
def ui_suppliers_create(
    request: Request,
    name: str = Form(...),
    inn: str | None = Form(None),
    kpp: str | None = Form(None),
    address_index: str | None = Form(None),
    address: str | None = Form(None),
    db: Session = Depends(get_db)
):
    """Создание нового поставщика через форму."""
    create_supplier(
        db=db,
        name=name,
        inn=inn if inn else None,
        kpp=kpp if kpp else None,
        address_index=address_index if address_index else None,
        address=address if address else None,
    )
    return RedirectResponse(url="/ui/suppliers", status_code=303)


@ui_router.get("/suppliers/{supplier_id}", response_class=HTMLResponse)
def ui_supplier_detail(
    request: Request,
    supplier_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Страница карточки поставщика."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        return RedirectResponse(url="/ui/suppliers", status_code=303)
    
    # Получаем или создаем профиль
    profile = get_or_create_supplier_profile(db, supplier_id)
    
    # Получаем связанные данные
    okved_codes = get_supplier_okved(db, supplier_id)
    equipment = db.query(SupplierEquipment).filter(
        SupplierEquipment.supplier_id == supplier_id
    ).all()
    certificates = db.query(SupplierCertificate).filter(
        SupplierCertificate.supplier_id == supplier_id
    ).all()
    
    # Категории документов для поставщиков
    supplier_categories = db.query(DocumentCategory).filter(
        DocumentCategory.is_active == True,
        DocumentCategory.key.like("SUPPLIER_%")
    ).all()
    
    # Документы поставщика
    supplier_documents = list_documents(db, supplier_id=supplier_id)
    
    return templates.TemplateResponse(
        request,
        "ui_supplier_detail.html",
        {
            "supplier": supplier,
            "profile": profile,
            "okved_codes": okved_codes,
            "equipment": equipment,
            "certificates": certificates,
            "supplier_categories": supplier_categories,
            "supplier_documents": supplier_documents
        }
    )


@ui_router.post("/suppliers/{supplier_id}/profile", response_class=RedirectResponse, status_code=303)
def ui_supplier_profile_update(
    request: Request,
    supplier_id: uuid.UUID,
    db: Session = Depends(get_db),
    **kwargs
):
    """Обновление профиля поставщика."""
    try:
        # Собираем все поля формы
        form_data = {}
        for key in [
            'full_name', 'short_name', 'ogrn', 'okpo', 'okato', 'kpp', 'inn',
            'legal_address', 'fact_address', 'mail_address', 'postal_code',
            'website', 'email', 'phone', 'contact_person', 'contact_position',
            'business_description', 'main_products_services', 'industries',
            'production_sites', 'capacity_description', 'equipment_summary',
            'headcount_total', 'headcount_engineering', 'headcount_production',
            'headcount_quality', 'key_specialists',
            'qms_standards', 'certifications_summary',
            'goz_experience', 'executed_contracts_count', 'key_customers',
            'similar_deliveries',
            'bank_name', 'bank_bik', 'bank_account', 'corr_account',
            'signatory_fio', 'signatory_position', 'signatory_basis'
        ]:
            value = request.form.get(key)
            if value is not None:
                if key in ['headcount_total', 'headcount_engineering', 'headcount_production',
                          'headcount_quality', 'executed_contracts_count']:
                    form_data[key] = int(value) if value else None
                elif key == 'has_qms':
                    form_data[key] = value == 'on'
                elif key == 'works_with_goz':
                    form_data[key] = value == 'on'
                elif key == 'goz_secret_clearance':
                    if value == 'true':
                        form_data[key] = True
                    elif value == 'false':
                        form_data[key] = False
                    else:
                        form_data[key] = None
                else:
                    form_data[key] = value if value else None
        
        # Обработка checkbox
        form_data['has_qms'] = request.form.get('has_qms') == 'on'
        form_data['works_with_goz'] = request.form.get('works_with_goz') == 'on'
        
        update_supplier_profile(db, supplier_id, **form_data)
        return RedirectResponse(url=f"/ui/suppliers/{supplier_id}", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/ui/suppliers/{supplier_id}?error={str(e)}", status_code=303)


@ui_router.post("/suppliers/{supplier_id}/okved", response_class=RedirectResponse, status_code=303)
def ui_supplier_okved_update(
    request: Request,
    supplier_id: uuid.UUID,
    codes: str = Form(...),
    db: Session = Depends(get_db)
):
    """Обновление кодов ОКВЭД."""
    try:
        codes_list = [c.strip() for c in codes.split('\n') if c.strip()]
        set_supplier_okved(db, supplier_id, codes_list)
        return RedirectResponse(url=f"/ui/suppliers/{supplier_id}", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/ui/suppliers/{supplier_id}?error={str(e)}", status_code=303)


@ui_router.post("/suppliers/{supplier_id}/equipment/add", response_class=RedirectResponse, status_code=303)
def ui_supplier_equipment_add(
    request: Request,
    supplier_id: uuid.UUID,
    name: str = Form(...),
    model: str | None = Form(None),
    qty: str | None = Form(None),
    notes: str | None = Form(None),
    db: Session = Depends(get_db)
):
    """Добавление оборудования."""
    try:
        qty_int = int(qty) if qty else None
        add_supplier_equipment(db, supplier_id, name, model, qty_int, notes)
        return RedirectResponse(url=f"/ui/suppliers/{supplier_id}", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/ui/suppliers/{supplier_id}?error={str(e)}", status_code=303)


@ui_router.post("/suppliers/{supplier_id}/equipment/delete", response_class=RedirectResponse, status_code=303)
def ui_supplier_equipment_delete(
    request: Request,
    supplier_id: uuid.UUID,
    equipment_id: str = Form(...),
    db: Session = Depends(get_db)
):
    """Удаление оборудования."""
    try:
        eq_id = uuid.UUID(equipment_id)
        delete_supplier_equipment(db, eq_id, supplier_id)
        return RedirectResponse(url=f"/ui/suppliers/{supplier_id}", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/ui/suppliers/{supplier_id}?error={str(e)}", status_code=303)


@ui_router.post("/suppliers/{supplier_id}/certificates/add", response_class=RedirectResponse, status_code=303)
def ui_supplier_certificate_add(
    request: Request,
    supplier_id: uuid.UUID,
    cert_type: str = Form(...),
    number: str | None = Form(None),
    issued_by: str | None = Form(None),
    valid_from: str | None = Form(None),
    valid_to: str | None = Form(None),
    notes: str | None = Form(None),
    db: Session = Depends(get_db)
):
    """Добавление сертификата."""
    try:
        add_supplier_certificate(
            db, supplier_id, cert_type, number, issued_by,
            valid_from, valid_to, notes
        )
        return RedirectResponse(url=f"/ui/suppliers/{supplier_id}", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/ui/suppliers/{supplier_id}?error={str(e)}", status_code=303)


@ui_router.post("/suppliers/{supplier_id}/certificates/delete", response_class=RedirectResponse, status_code=303)
def ui_supplier_certificate_delete(
    request: Request,
    supplier_id: uuid.UUID,
    certificate_id: str = Form(...),
    db: Session = Depends(get_db)
):
    """Удаление сертификата."""
    try:
        cert_id = uuid.UUID(certificate_id)
        delete_supplier_certificate(db, cert_id, supplier_id)
        return RedirectResponse(url=f"/ui/suppliers/{supplier_id}", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/ui/suppliers/{supplier_id}?error={str(e)}", status_code=303)


@ui_router.post("/suppliers/{supplier_id}/documents/upload", response_class=RedirectResponse, status_code=303)
def ui_supplier_documents_upload(
    request: Request,
    supplier_id: uuid.UUID,
    category_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Загрузка документа поставщика."""
    try:
        create_document_with_file(
            db=db,
            category_id=category_id,
            file=file,
            supplier_id=supplier_id
        )
        return RedirectResponse(url=f"/ui/suppliers/{supplier_id}", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/ui/suppliers/{supplier_id}?error={str(e)}", status_code=303)


@ui_router.get("/cases", response_class=HTMLResponse)
def ui_cases(request: Request, db: Session = Depends(get_db), error: str | None = None):
    """Страница списка закупок."""
    cases = list_cases(db)
    return templates.TemplateResponse(
        request,
        "ui_cases.html",
        {"cases": cases, "error": error}
    )


@ui_router.post("/cases", response_class=HTMLResponse)
def ui_cases_create(
    request: Request,
    code: str = Form(...),
    title: str = Form(...),
    db: Session = Depends(get_db)
):
    """Создание новой закупки через форму."""
    try:
        case = create_case(
            db=db,
            code=code,
            title=title,
            supplier_id=None  # Не выбираем поставщика при создании
        )
        return RedirectResponse(url=f"/ui/cases/{case.id}#basis", status_code=303)
    except HTTPException as e:
        # Возвращаем страницу с ошибкой
        cases = list_cases(db)
        return templates.TemplateResponse(
            request,
            "ui_cases.html",
            {"cases": cases, "error": e.detail},
            status_code=400
        )
    except Exception as e:
        # Обработка других ошибок
        cases = list_cases(db)
        return templates.TemplateResponse(
            request,
            "ui_cases.html",
            {"cases": cases, "error": f"Ошибка: {str(e)}"},
            status_code=400
        )


@ui_router.get("/cases/{case_id}", response_class=HTMLResponse)
def ui_case_detail(
    request: Request,
    case_id: str,
    status: str | None = Query(None),
    db: Session = Depends(get_db)
):
    """Детальная страница кейса с чек-листом. Принимает UUID или код кейса."""
    try:
        # Пытаемся парсить как UUID
        try:
            case_uuid = uuid.UUID(case_id)
            case = get_case(db, case_uuid)
        except ValueError:
            # Если не UUID, ищем по коду
            case = get_case_by_code(db, case_id)
    except HTTPException:
        return RedirectResponse(url="/ui/cases", status_code=303)
    
    # Получаем чек-лист с фильтром по статусу
    all_checklist_items = get_case_checklist_with_documents(db, case.id, status_filter=status)
    
    # Разделяем на основание и остальные
    basis_items, other_items = split_checklist_items_by_basis(all_checklist_items)
    
    # Получаем документы кейса для dropdown
    case_documents = list_documents(db, case_id=case.id)
    
    # Подсчитываем прогресс (для всех пунктов)
    total_required = sum(1 for item in all_checklist_items if item.template_item and item.template_item.is_required)
    done_required = sum(1 for item in all_checklist_items if item.template_item and item.template_item.is_required and item.status == "DONE")
    
    # Группируем остальные пункты по секциям (без основания)
    sections = {}
    for item in other_items:
        if not item.template_item:
            continue
        section_key = item.template_item.section
        if section_key not in sections:
            sections[section_key] = []
        sections[section_key].append(item)
    
    # Находим пункты "Проверьте закупку на ошибки" (по ключевым словам в title)
    error_items = [
        item for item in all_checklist_items
        if item.template_item and ("ошибк" in item.template_item.title.lower() or "риск" in item.template_item.title.lower())
    ]
    error_todo_count = sum(1 for item in error_items if item.status == "TODO")
    
    # Проверяем, есть ли незаполненные пункты основания
    basis_has_todo = any(item.status == "TODO" for item in basis_items if item.template_item and item.template_item.is_required)
    
    # Данные для закупки
    candidates = db.query(CaseCandidate).filter(
        CaseCandidate.case_id == case.id
    ).all()
    
    rfq_requests = db.query(RfqRequest).filter(
        RfqRequest.case_id == case.id
    ).order_by(RfqRequest.sent_at.desc()).all()
    
    commercial_offers = db.query(CommercialOffer).filter(
        CommercialOffer.case_id == case.id
    ).order_by(CommercialOffer.price_total).all()
    
    security_reviews = db.query(SupplierSecurityReview).filter(
        SupplierSecurityReview.case_id == case.id
    ).all()
    
    # Список поставщиков для выбора кандидата
    from app.services.suppliers import list_suppliers
    all_suppliers = list_suppliers(db)
    
    # Категории документов для RFQ и КП
    from app.models.document_category import DocumentCategory
    rfq_category = db.query(DocumentCategory).filter(
        DocumentCategory.key == "RFQ_EVIDENCE"
    ).first()
    kp_category = db.query(DocumentCategory).filter(
        DocumentCategory.key == "KP"
    ).first()
    sb_category = db.query(DocumentCategory).filter(
        DocumentCategory.key == "SB_CONCLUSION"
    ).first()
    
    return templates.TemplateResponse(
        request,
        "ui_case_detail.html",
        {
            "case": case,
            "basis_items": basis_items,
            "other_checklist_items": other_items,
            "sections": sections,
            "case_documents": case_documents,
            "status_filter": status,
            "total_required": total_required,
            "done_required": done_required,
            "error_items": error_items,
            "error_todo_count": error_todo_count,
            "basis_has_todo": basis_has_todo,
            "case": case,  # Убеждаемся, что case передаётся в шаблон
            # Данные закупки
            "candidates": candidates,
            "rfq_requests": rfq_requests,
            "commercial_offers": commercial_offers,
            "security_reviews": security_reviews,
            "all_suppliers": all_suppliers,
            "rfq_category": rfq_category,
            "kp_category": kp_category,
            "sb_category": sb_category
        }
    )


@ui_router.post("/cases/{case_id}/checklist/update", response_class=RedirectResponse, status_code=303)
def ui_checklist_update(
    request: Request,
    case_id: uuid.UUID,
    case_checklist_item_id: str = Form(...),
    status: str = Form(...),
    comment: str | None = Form(None),
    status_filter: str | None = Form(None),
    db: Session = Depends(get_db)
):
    """Обновление статуса и комментария пункта чек-листа."""
    try:
        item_id = uuid.UUID(case_checklist_item_id)
        update_checklist_item_status(db, case_id, item_id, status, comment)
        
        # Редирект обратно с сохранением фильтра
        url = f"/ui/cases/{case_id}"
        if status_filter:
            url += f"?status={status_filter}"
        return RedirectResponse(url=url, status_code=303)
    except Exception as e:
        url = f"/ui/cases/{case_id}?error={str(e)}"
        if status_filter:
            url += f"&status={status_filter}"
        return RedirectResponse(url=url, status_code=303)


@ui_router.post("/cases/{case_id}/checklist/attach", response_class=RedirectResponse, status_code=303)
def ui_checklist_attach(
    request: Request,
    case_id: uuid.UUID,
    case_checklist_item_id: str = Form(...),
    document_id: str = Form(...),
    status_filter: str | None = Form(None),
    db: Session = Depends(get_db)
):
    """Прикрепление документа к пункту чек-листа."""
    try:
        item_id = uuid.UUID(case_checklist_item_id)
        doc_id = uuid.UUID(document_id)
        attach_document_to_checklist_item(db, case_id, item_id, doc_id)
        
        url = f"/ui/cases/{case_id}"
        if status_filter:
            url += f"?status={status_filter}"
        return RedirectResponse(url=url, status_code=303)
    except Exception as e:
        url = f"/ui/cases/{case_id}?error={str(e)}"
        if status_filter:
            url += f"&status={status_filter}"
        return RedirectResponse(url=url, status_code=303)


@ui_router.post("/cases/{case_id}/checklist/detach", response_class=RedirectResponse, status_code=303)
def ui_checklist_detach(
    request: Request,
    case_id: uuid.UUID,
    case_checklist_item_id: str = Form(...),
    document_id: str = Form(...),
    status_filter: str | None = Form(None),
    db: Session = Depends(get_db)
):
    """Открепление документа от пункта чек-листа."""
    try:
        item_id = uuid.UUID(case_checklist_item_id)
        doc_id = uuid.UUID(document_id)
        detach_document_from_checklist_item(db, case_id, item_id, doc_id)
        
        url = f"/ui/cases/{case_id}"
        if status_filter:
            url += f"?status={status_filter}"
        return RedirectResponse(url=url, status_code=303)
    except Exception as e:
        url = f"/ui/cases/{case_id}?error={str(e)}"
        if status_filter:
            url += f"&status={status_filter}"
        return RedirectResponse(url=url, status_code=303)


@ui_router.post("/cases/{case_id}/procurement/update", response_class=RedirectResponse, status_code=303)
def ui_case_procurement_update(
    request: Request,
    case_id: uuid.UUID,
    procurement_type: str = Form(...),
    subject: str | None = Form(None),
    initiator_department: str | None = Form(None),
    planned_deadline: str | None = Form(None),
    status_filter: str | None = Form(None),
    db: Session = Depends(get_db)
):
    """Обновление параметров закупки."""
    try:
        from datetime import datetime
        case = get_case(db, case_id)
        case.procurement_type = procurement_type
        case.subject = subject if subject else None
        case.initiator_department = initiator_department if initiator_department else None
        
        if planned_deadline:
            try:
                case.planned_deadline = datetime.strptime(planned_deadline, "%Y-%m-%d").date()
            except ValueError:
                pass
        
        db.commit()
        
        url = f"/ui/cases/{case_id}"
        if status_filter:
            url += f"?status={status_filter}"
        return RedirectResponse(url=url, status_code=303)
    except Exception as e:
        url = f"/ui/cases/{case_id}?error={str(e)}"
        if status_filter:
            url += f"&status={status_filter}"
        return RedirectResponse(url=url, status_code=303)


@ui_router.post("/cases/{case_id}/candidates/add", response_class=RedirectResponse, status_code=303)
def ui_case_candidate_add(
    request: Request,
    case_id: uuid.UUID,
    supplier_id: str | None = Form(None),
    org_name: str | None = Form(None),
    inn: str | None = Form(None),
    contact_email: str | None = Form(None),
    contact_phone: str | None = Form(None),
    status_filter: str | None = Form(None),
    db: Session = Depends(get_db)
):
    """Добавление кандидата в закупку."""
    try:
        supplier_uuid = uuid.UUID(supplier_id) if supplier_id else None
        add_candidate_to_case(
            db, case_id,
            supplier_id=supplier_uuid,
            org_name=org_name if org_name else None,
            inn=inn if inn else None,
            contact_email=contact_email if contact_email else None,
            contact_phone=contact_phone if contact_phone else None
        )
        
        url = f"/ui/cases/{case_id}"
        if status_filter:
            url += f"?status={status_filter}"
        return RedirectResponse(url=url, status_code=303)
    except Exception as e:
        url = f"/ui/cases/{case_id}?error={str(e)}"
        if status_filter:
            url += f"&status={status_filter}"
        return RedirectResponse(url=url, status_code=303)


@ui_router.post("/cases/{case_id}/candidates/recompute-rank", response_class=RedirectResponse, status_code=303)
def ui_case_candidates_recompute_rank(
    request: Request,
    case_id: uuid.UUID,
    status_filter: str | None = Form(None),
    db: Session = Depends(get_db)
):
    """Пересчёт ранка для всех кандидатов."""
    try:
        recompute_all_candidates_rank(db, case_id)
        
        url = f"/ui/cases/{case_id}"
        if status_filter:
            url += f"?status={status_filter}"
        return RedirectResponse(url=url, status_code=303)
    except Exception as e:
        url = f"/ui/cases/{case_id}?error={str(e)}"
        if status_filter:
            url += f"&status={status_filter}"
        return RedirectResponse(url=url, status_code=303)


@ui_router.post("/cases/{case_id}/rfq/create", response_class=RedirectResponse, status_code=303)
def ui_case_rfq_create(
    request: Request,
    case_id: uuid.UUID,
    candidate_id: str = Form(...),
    channel: str = Form(...),
    result: str = Form("SENT"),
    sent_at: str | None = Form(None),
    notes: str | None = Form(None),
    evidence_document_id: str | None = Form(None),
    status_filter: str | None = Form(None),
    db: Session = Depends(get_db)
):
    """Создание записи об отправке запроса КП."""
    try:
        from datetime import datetime
        candidate_uuid = uuid.UUID(candidate_id)
        sent_at_dt = datetime.utcnow()
        if sent_at:
            try:
                sent_at_dt = datetime.strptime(sent_at, "%Y-%m-%dT%H:%M")
            except ValueError:
                pass
        
        evidence_doc_uuid = uuid.UUID(evidence_document_id) if evidence_document_id else None
        
        rfq = RfqRequest(
            case_id=case_id,
            candidate_id=candidate_uuid,
            channel=channel,
            result=result,
            sent_at=sent_at_dt,
            notes=notes if notes else None,
            evidence_document_id=evidence_doc_uuid
        )
        db.add(rfq)
        
        # Обновляем статус кандидата
        candidate = db.query(CaseCandidate).filter(CaseCandidate.id == candidate_uuid).first()
        if candidate:
            if result == "RECEIVED_OFFER":
                candidate.status = "OFFER_RECEIVED"
            elif result == "REFUSAL":
                candidate.status = "REFUSED"
            elif result == "NO_RESPONSE":
                candidate.status = "NO_RESPONSE"
            else:
                candidate.status = "RFQ_SENT"
        
        # Обновляем stage кейса
        case = get_case(db, case_id)
        if case.procedure_stage == "DRAFT":
            case.procedure_stage = "RFQ_SENT"
        
        db.commit()
        
        url = f"/ui/cases/{case_id}"
        if status_filter:
            url += f"?status={status_filter}"
        return RedirectResponse(url=url, status_code=303)
    except Exception as e:
        url = f"/ui/cases/{case_id}?error={str(e)}"
        if status_filter:
            url += f"&status={status_filter}"
        return RedirectResponse(url=url, status_code=303)


@ui_router.post("/cases/{case_id}/offers/add", response_class=RedirectResponse, status_code=303)
def ui_case_offer_add(
    request: Request,
    case_id: uuid.UUID,
    candidate_id: str = Form(...),
    price_total: str = Form(...),
    lead_time_days: str | None = Form(None),
    valid_until: str | None = Form(None),
    delivery_terms: str | None = Form(None),
    payment_terms: str | None = Form(None),
    document_id: str | None = Form(None),
    status_filter: str | None = Form(None),
    db: Session = Depends(get_db)
):
    """Добавление коммерческого предложения."""
    try:
        from decimal import Decimal
        from datetime import datetime, date
        
        candidate_uuid = uuid.UUID(candidate_id)
        candidate = db.query(CaseCandidate).filter(CaseCandidate.id == candidate_uuid).first()
        if not candidate:
            raise HTTPException(status_code=404, detail="Кандидат не найден")
        
        valid_until_date = None
        if valid_until:
            try:
                valid_until_date = datetime.strptime(valid_until, "%Y-%m-%d").date()
            except ValueError:
                pass
        
        doc_uuid = uuid.UUID(document_id) if document_id else None
        
        offer = CommercialOffer(
            case_id=case_id,
            candidate_id=candidate_uuid,
            supplier_id=candidate.supplier_id,
            price_total=Decimal(price_total),
            lead_time_days=int(lead_time_days) if lead_time_days else None,
            valid_until=valid_until_date,
            delivery_terms=delivery_terms if delivery_terms else None,
            payment_terms=payment_terms if payment_terms else None,
            document_id=doc_uuid
        )
        db.add(offer)
        
        # Обновляем статус кандидата
        candidate.status = "OFFER_RECEIVED"
        
        db.commit()
        
        # Пересчитываем НМЦ
        recompute_case_pricing(db, case_id)
        
        url = f"/ui/cases/{case_id}"
        if status_filter:
            url += f"?status={status_filter}"
        return RedirectResponse(url=url, status_code=303)
    except Exception as e:
        url = f"/ui/cases/{case_id}?error={str(e)}"
        if status_filter:
            url += f"&status={status_filter}"
        return RedirectResponse(url=url, status_code=303)


@ui_router.post("/cases/{case_id}/security-review/update", response_class=RedirectResponse, status_code=303)
def ui_case_security_review_update(
    request: Request,
    case_id: uuid.UUID,
    supplier_id: str = Form(...),
    status: str = Form(...),
    comment: str | None = Form(None),
    document_id: str | None = Form(None),
    status_filter: str | None = Form(None),
    db: Session = Depends(get_db)
):
    """Обновление проверки СБ."""
    try:
        from datetime import datetime
        supplier_uuid = uuid.UUID(supplier_id)
        doc_uuid = uuid.UUID(document_id) if document_id else None
        
        review = db.query(SupplierSecurityReview).filter(
            SupplierSecurityReview.case_id == case_id,
            SupplierSecurityReview.supplier_id == supplier_uuid
        ).first()
        
        if review:
            review.status = status
            review.comment = comment if comment else None
            review.document_id = doc_uuid
            if status in ("APPROVED", "REJECTED"):
                review.reviewed_at = datetime.utcnow()
        else:
            review = SupplierSecurityReview(
                case_id=case_id,
                supplier_id=supplier_uuid,
                status=status,
                comment=comment if comment else None,
                document_id=doc_uuid
            )
            if status in ("APPROVED", "REJECTED"):
                review.reviewed_at = datetime.utcnow()
            db.add(review)
        
        # Обновляем stage кейса
        case = get_case(db, case_id)
        if status == "APPROVED" and case.procedure_stage == "OFFERS_COLLECTED":
            case.procedure_stage = "SB_REVIEW"
        
        db.commit()
        
        url = f"/ui/cases/{case_id}"
        if status_filter:
            url += f"?status={status_filter}"
        return RedirectResponse(url=url, status_code=303)
    except Exception as e:
        url = f"/ui/cases/{case_id}?error={str(e)}"
        if status_filter:
            url += f"&status={status_filter}"
        return RedirectResponse(url=url, status_code=303)


@ui_router.post("/cases/{case_id}/select-supplier", response_class=RedirectResponse, status_code=303)
def ui_case_select_supplier(
    request: Request,
    case_id: uuid.UUID,
    supplier_id: str = Form(...),
    note: str | None = Form(None),
    status_filter: str | None = Form(None),
    db: Session = Depends(get_db)
):
    """Выбор поставщика-победителя."""
    try:
        supplier_uuid = uuid.UUID(supplier_id)
        select_supplier_for_case(db, case_id, supplier_uuid, note)
        
        url = f"/ui/cases/{case_id}"
        if status_filter:
            url += f"?status={status_filter}"
        return RedirectResponse(url=url, status_code=303)
    except HTTPException as e:
        url = f"/ui/cases/{case_id}?error={e.detail}"
        if status_filter:
            url += f"&status={status_filter}"
        return RedirectResponse(url=url, status_code=303)
    except Exception as e:
        url = f"/ui/cases/{case_id}?error={str(e)}"
        if status_filter:
            url += f"&status={status_filter}"
        return RedirectResponse(url=url, status_code=303)


@ui_router.post("/cases/{case_id}/activate", response_class=RedirectResponse, status_code=303)
def ui_case_activate(
    request: Request,
    case_id: str,
    db: Session = Depends(get_db)
):
    """Активация закупки после проверки основания."""
    try:
        from app.services.cases import get_case_by_code
        
        # Получаем кейс по ID или коду
        try:
            case_uuid = uuid.UUID(case_id)
            case = get_case(db, case_uuid)
        except ValueError:
            case = get_case_by_code(db, case_id)
        
        activate_case(db, case.id)
        
        return RedirectResponse(url=f"/ui/cases/{case.id}#basis", status_code=303)
    except HTTPException as e:
        return RedirectResponse(url=f"/ui/cases/{case_id}?error={e.detail}#basis", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/ui/cases/{case_id}?error={str(e)}#basis", status_code=303)


@ui_router.post("/cases/{case_id}/epoz/update", response_class=RedirectResponse, status_code=303)
def ui_epoz_update(
    request: Request,
    case_id: uuid.UUID,
    epoz_clause: str | None = Form(None),
    status_filter: str | None = Form(None),
    db: Session = Depends(get_db)
):
    """Обновление пункта ЕПоЗ для кейса."""
    try:
        case = get_case(db, case_id)
        case.epoz_clause = epoz_clause if epoz_clause else None
        db.commit()
        
        url = f"/ui/cases/{case_id}"
        if status_filter:
            url += f"?status={status_filter}"
        return RedirectResponse(url=url, status_code=303)
    except Exception as e:
        url = f"/ui/cases/{case_id}?error={str(e)}"
        if status_filter:
            url += f"&status={status_filter}"
        return RedirectResponse(url=url, status_code=303)


@ui_router.get("/documents", response_class=HTMLResponse)
def ui_documents(
    request: Request,
    case_id: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db)
):
    """Страница списка документов."""
    case_uuid = None
    case_obj = None
    if case_id:
        try:
            case_uuid = uuid.UUID(case_id)
            case_obj = db.query(Case).filter(Case.id == case_uuid).first()
            if not case_obj:
                error = "Кейс не найден"
        except ValueError:
            error = "Неверный формат ID кейса"
    
    documents = list_documents(db, case_id=case_uuid)
    cases = list_cases(db)
    categories = list_categories(db, include_inactive=False)  # Только активные для dropdown
    return templates.TemplateResponse(
        request,
        "ui_documents.html",
        {
            "documents": documents,
            "cases": cases,
            "categories": categories,
            "selected_case_id": case_id,
            "selected_case": case_obj,
            "error": error
        }
    )


@ui_router.post("/documents/upload", response_class=RedirectResponse, status_code=303)
def ui_documents_upload(
    request: Request,
    case_id: str = Form(...),
    category_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Загрузка документа через форму."""
    try:
        create_document_with_file(
            db=db,
            case_id=case_id,
            category_id=category_id,
            file=file,
        )
        # Редирект обратно с case_id для сохранения контекста
        return RedirectResponse(url=f"/ui/documents?case_id={case_id}", status_code=303)
    except HTTPException as e:
        # Сохраняем case_id в редиректе даже при ошибке
        return RedirectResponse(url=f"/ui/documents?case_id={case_id}&error={e.detail}", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/ui/documents?case_id={case_id}&error={str(e)}", status_code=303)


@ui_router.get("/documents/{doc_id}/download", response_class=RedirectResponse, status_code=302)
def ui_documents_download(
    doc_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Скачать документ через presigned URL."""
    from app.models.document import Document
    from app.services.storage import presigned_get_url
    
    document = db.query(Document).filter(Document.id == doc_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")
    
    if document.status != "DONE":
        raise HTTPException(status_code=400, detail=f"Документ не готов к скачиванию (статус: {document.status})")
    
    try:
        url = presigned_get_url(document.storage_bucket, document.storage_key, expires=3600)
        return RedirectResponse(url=url, status_code=302)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации ссылки: {str(e)}")


@ui_router.get("/document-categories", response_class=HTMLResponse)
def ui_document_categories(request: Request, db: Session = Depends(get_db), error: str | None = None):
    """Страница управления категориями документов."""
    categories = list_categories(db, include_inactive=True)  # Все категории, включая архивные
    return templates.TemplateResponse(
        request,
        "ui_categories.html",
        {"categories": categories, "error": error}
    )


@ui_router.get("/categories", response_class=HTMLResponse)
def ui_categories_redirect(request: Request):
    """Редирект со старого пути на новый."""
    return RedirectResponse(url="/ui/document-categories", status_code=301)


@ui_router.post("/document-categories", response_class=RedirectResponse, status_code=303)
def ui_document_categories_create(
    request: Request,
    name: str = Form(...),
    key: str | None = Form(None),
    db: Session = Depends(get_db)
):
    """Создание новой категории через форму."""
    try:
        create_category(db=db, name=name, key=key)
        return RedirectResponse(url="/ui/document-categories", status_code=303)
    except HTTPException as e:
        documents = list_documents(db)
        cases = list_cases(db)
        categories = list_categories(db, include_inactive=False)
        return templates.TemplateResponse(
            request,
            "ui_documents.html",
            {"documents": documents, "cases": cases, "categories": categories, "error": e.detail},
            status_code=400
        )
    except Exception as e:
        documents = list_documents(db)
        cases = list_cases(db)
        categories = list_categories(db, include_inactive=False)
        return templates.TemplateResponse(
            request,
            "ui_documents.html",
            {"documents": documents, "cases": cases, "categories": categories, "error": f"Ошибка: {str(e)}"},
            status_code=400
        )


@ui_router.post("/document-categories/{category_id}/archive", response_class=HTMLResponse)
def ui_document_categories_archive(
    request: Request,
    category_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Архивирование категории."""
    try:
        archive_category(db, category_id)
        return RedirectResponse(url="/ui/document-categories", status_code=303)
    except HTTPException as e:
        categories = list_categories(db, include_inactive=True)
        return templates.TemplateResponse(
            request,
            "ui_categories.html",
            {"categories": categories, "error": e.detail},
            status_code=400
        )
