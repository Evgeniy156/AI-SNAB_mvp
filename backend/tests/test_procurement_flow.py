"""Тесты для workflow закупки (procurement flow)."""
import pytest
import uuid
from decimal import Decimal
from fastapi.testclient import TestClient
from app.main import app
from app.models.case import Case
from app.models.supplier import Supplier
from app.models.procurement import (
    CaseCandidate,
    CommercialOffer,
    SupplierSecurityReview
)
from app.services.procurement import (
    recompute_case_pricing,
    select_supplier_for_case,
    add_candidate_to_case
)


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


@pytest.fixture
def test_supplier(db):
    """Создать тестового поставщика."""
    supplier = Supplier(name="Тестовый поставщик")
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@pytest.fixture
def test_case(db, test_supplier):
    """Создать тестовый кейс."""
    case = Case(code="TEST-CASE-001", title="Тестовая закупка")
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def test_recompute_case_pricing_avg_and_coeff(db, test_case):
    """Тест: пересчёт НМЦ вычисляет среднюю цену и коэффициент валидации."""
    # Создаём 3 кандидатов
    candidate1 = add_candidate_to_case(db, test_case.id, org_name="Кандидат 1")
    candidate2 = add_candidate_to_case(db, test_case.id, org_name="Кандидат 2")
    candidate3 = add_candidate_to_case(db, test_case.id, org_name="Кандидат 3")
    
    # Создаём 3 КП с разными ценами
    offer1 = CommercialOffer(
        case_id=test_case.id,
        candidate_id=candidate1.id,
        price_total=Decimal("1000000.00")
    )
    offer2 = CommercialOffer(
        case_id=test_case.id,
        candidate_id=candidate2.id,
        price_total=Decimal("1050000.00")
    )
    offer3 = CommercialOffer(
        case_id=test_case.id,
        candidate_id=candidate3.id,
        price_total=Decimal("1020000.00")
    )
    db.add_all([offer1, offer2, offer3])
    db.commit()
    
    # Пересчитываем
    result = recompute_case_pricing(db, test_case.id)
    
    # Проверяем расчёты
    assert result["offers_count"] == 3
    assert result["avg"] == pytest.approx(1023333.33, rel=0.01)  # (1000000+1050000+1020000)/3
    assert result["coeff"] == pytest.approx(0.0488, rel=0.01)  # (1050000-1000000)/1023333.33
    assert result["ok"] is True  # coeff < 0.33 and count >= 3
    
    # Проверяем, что сохранилось в кейс
    db.refresh(test_case)
    assert test_case.nmc_avg_price == pytest.approx(Decimal("1023333.33"), rel=Decimal("0.01"))
    assert test_case.validation_coeff == pytest.approx(Decimal("0.0488"), rel=Decimal("0.01"))
    assert test_case.offers_count == 3
    assert test_case.is_validation_ok is True


def test_validation_requires_3_offers(db, test_case):
    """Тест: валидация требует минимум 3 КП."""
    # Создаём 2 кандидатов и 2 КП
    candidate1 = add_candidate_to_case(db, test_case.id, org_name="Кандидат 1")
    candidate2 = add_candidate_to_case(db, test_case.id, org_name="Кандидат 2")
    
    offer1 = CommercialOffer(
        case_id=test_case.id,
        candidate_id=candidate1.id,
        price_total=Decimal("1000000.00")
    )
    offer2 = CommercialOffer(
        case_id=test_case.id,
        candidate_id=candidate2.id,
        price_total=Decimal("1050000.00")
    )
    db.add_all([offer1, offer2])
    db.commit()
    
    # Пересчитываем
    result = recompute_case_pricing(db, test_case.id)
    
    # Проверяем, что валидация не пройдена
    assert result["offers_count"] == 2
    assert result["ok"] is False
    
    db.refresh(test_case)
    assert test_case.is_validation_ok is False


def test_select_supplier_requires_sb_approved(db, test_case, test_supplier):
    """Тест: выбор поставщика требует APPROVED от СБ."""
    # Добавляем кандидата
    candidate = add_candidate_to_case(db, test_case.id, supplier_id=test_supplier.id)
    
    # Пытаемся выбрать без СБ APPROVED
    with pytest.raises(Exception):  # HTTPException или ValueError
        select_supplier_for_case(db, test_case.id, test_supplier.id)
    
    # Создаём проверку СБ со статусом APPROVED
    security_review = SupplierSecurityReview(
        case_id=test_case.id,
        supplier_id=test_supplier.id,
        status="APPROVED"
    )
    db.add(security_review)
    db.commit()
    
    # Теперь выбор должен пройти
    case = select_supplier_for_case(db, test_case.id, test_supplier.id, "Тестовое примечание")
    
    assert case.selected_supplier_id == test_supplier.id
    assert case.selection_note == "Тестовое примечание"
    assert case.procedure_stage == "SUPPLIER_SELECTED"


def test_rfq_log_created_and_links_document(db, test_case):
    """Тест: создание RFQ запроса и связь с документом."""
    from app.models.procurement import RfqRequest
    from app.models.document import Document
    from app.models.document_category import DocumentCategory
    
    # Создаём категорию и документ
    category = DocumentCategory(key="RFQ_EVIDENCE", name="Подтверждение RFQ", is_active=True)
    db.add(category)
    db.flush()
    
    document = Document(
        case_id=test_case.id,
        category_id=category.id,
        doc_type="CASE",
        original_filename="rfq_evidence.pdf",
        storage_bucket="test-bucket",
        storage_key="test.pdf",
        status="DONE"
    )
    db.add(document)
    db.flush()
    
    # Создаём кандидата
    candidate = add_candidate_to_case(db, test_case.id, org_name="Кандидат")
    
    # Создаём RFQ запрос с документом
    rfq = RfqRequest(
        case_id=test_case.id,
        candidate_id=candidate.id,
        channel="EMAIL",
        result="SENT",
        evidence_document_id=document.id
    )
    db.add(rfq)
    db.commit()
    
    # Проверяем связь
    db.refresh(rfq)
    assert rfq.evidence_document_id == document.id
    assert rfq.evidence_document is not None
    assert rfq.evidence_document.original_filename == "rfq_evidence.pdf"


def test_ui_case_detail_contains_procurement_sections(client, db, test_case):
    """Тест: UI страница кейса содержит секции закупки."""
    response = client.get(f"/ui/cases/{test_case.id}")
    assert response.status_code == 200
    
    # Проверяем наличие секций
    assert "Параметры закупки" in response.text
    assert "Кандидаты и ранк-анализ" in response.text
    assert "Запрос КП (RFQ журнал)" in response.text
    assert "Коммерческие предложения (КП)" in response.text
    assert "НМЦ и валидация" in response.text
    assert "Проверка СБ" in response.text
    assert "Выбор победителя" in response.text

