"""Тесты для гейта активации закупки."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.case import Case
from app.models.checklist_template import ChecklistTemplate, ChecklistTemplateItem
from app.models.case_checklist import CaseChecklistItem
from app.models.document import Document
from app.models.document_category import DocumentCategory
from app.models.case_checklist import CaseChecklistItemDocument
from app.services.checklist import ensure_case_checklist
from app.services.procurement_activation import validate_basis_ready, activate_case


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


@pytest.fixture
def test_case(db, test_template_with_basis):
    """Создать тестовый кейс с привязанным шаблоном."""
    case = Case(
        code="TEST-ACT-001",
        title="Тестовая закупка",
        checklist_template_id=test_template_with_basis.id
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@pytest.fixture
def test_template_with_basis(db):
    """Создать тестовый шаблон с обязательными пунктами основания."""
    import uuid
    template = ChecklistTemplate(
        key=f"TEST_ACTIVATION_{uuid.uuid4().hex[:8]}",
        name="Тестовый шаблон активации",
        is_active=True,
        is_default=True
    )
    db.add(template)
    db.flush()
    
    # Обязательный пункт основания
    item1 = ChecklistTemplateItem(
        template_id=template.id,
        section="I. Подготовительный этап",
        group_title="1. Основание закупки",
        title="Служебная записка",
        is_required=True,
        sort_order=1
    )
    db.add(item1)
    
    # Второй обязательный пункт основания
    item2 = ChecklistTemplateItem(
        template_id=template.id,
        section="I. Подготовительный этап",
        group_title="1. Основание закупки",
        title="Техническое задание",
        is_required=True,
        sort_order=2
    )
    db.add(item2)
    
    db.commit()
    return template


def test_case_not_activated_by_default(db, test_case):
    """Тест: закупка создаётся как не активированная."""
    assert test_case.is_activated is False
    assert test_case.activated_at is None


def test_activate_fails_without_doc_number_date_or_attachment(db, test_case, test_template_with_basis):
    """Тест: активация не проходит без номера/даты документа или прикреплённого документа."""
    # Инициализируем чек-лист
    ensure_case_checklist(db, test_case.id)
    
    # Пытаемся активировать без заполнения
    with pytest.raises(Exception):  # HTTPException или ValueError
        activate_case(db, test_case.id)
    
    # Проверяем валидацию
    ok, errors = validate_basis_ready(db, test_case.id)
    assert ok is False
    assert len(errors) > 0
    
    # Проверяем, что ошибки содержат нужные тексты
    error_text = " ".join(errors).lower()
    assert "нет номера" in error_text or "не прикреплён" in error_text or "нет даты" in error_text


def test_activate_success_when_basis_ready(db, test_case, test_template_with_basis):
    """Тест: активация проходит, когда основание заполнено."""
    from datetime import date
    
    # Инициализируем чек-лист
    ensure_case_checklist(db, test_case.id)
    
    # Получаем пункты основания
    from app.services.procurement_activation import get_basis_items
    basis_items = get_basis_items(db, test_case.id)
    
    # Создаём категорию и документ
    category = DocumentCategory(key="OTHER", name="Прочее", is_active=True)
    db.add(category)
    db.flush()
    
    # Заполняем каждый обязательный пункт
    for item in basis_items:
        if not item.template_item or not item.template_item.is_required:
            continue
        
        # Заполняем номер и дату
        item.doc_number = f"DOC-{item.template_item.title[:3].upper()}-001"
        item.doc_date = date.today()
        
        # Создаём и прикрепляем документ
        document = Document(
            case_id=test_case.id,
            category_id=category.id,
            doc_type="CASE",
            original_filename=f"{item.template_item.title}.pdf",
            storage_bucket="test-bucket",
            storage_key=f"test_{item.id}.pdf",
            status="DONE"
        )
        db.add(document)
        db.flush()
        
        link = CaseChecklistItemDocument(
            case_checklist_item_id=item.id,
            document_id=document.id
        )
        db.add(link)
    
    db.commit()
    
    # Проверяем валидацию
    ok, errors = validate_basis_ready(db, test_case.id)
    assert ok is True, f"Ошибки валидации: {errors}"
    
    # Активируем
    case = activate_case(db, test_case.id)
    
    assert case.is_activated is True
    assert case.activated_at is not None


def test_ui_hides_market_blocks_when_not_activated(client, db, test_case):
    """Тест: UI скрывает блоки анализа рынка, если закупка не активирована."""
    response = client.get(f"/ui/cases/{test_case.id}")
    assert response.status_code == 200
    
    html = response.text
    
    # Должна быть кнопка активации
    assert "Активировать закупку" in html
    
    # Не должно быть секции "Кандидаты и ранк-анализ" (или должно быть сообщение о недоступности)
    # Проверяем, что либо секция скрыта, либо есть предупреждение
    if "Кандидаты и ранк-анализ" not in html:
        # Секция скрыта - это нормально
        assert True
    else:
        # Если секция есть, должна быть недоступна
        assert "недоступно" in html.lower() or "не активирована" in html.lower()


def test_ui_shows_market_blocks_when_activated(client, db, test_case, test_template_with_basis):
    """Тест: UI показывает блоки анализа рынка, если закупка активирована."""
    from datetime import date
    
    # Инициализируем и заполняем основание
    ensure_case_checklist(db, test_case.id)
    
    from app.services.procurement_activation import get_basis_items
    basis_items = get_basis_items(db, test_case.id)
    
    category = DocumentCategory(key="OTHER", name="Прочее", is_active=True)
    db.add(category)
    db.flush()
    
    for item in basis_items:
        if not item.template_item or not item.template_item.is_required:
            continue
        
        item.doc_number = "DOC-001"
        item.doc_date = date.today()
        
        document = Document(
            case_id=test_case.id,
            category_id=category.id,
            doc_type="CASE",
            original_filename="test.pdf",
            storage_bucket="test-bucket",
            storage_key="test.pdf",
            status="DONE"
        )
        db.add(document)
        db.flush()
        
        link = CaseChecklistItemDocument(
            case_checklist_item_id=item.id,
            document_id=document.id
        )
        db.add(link)
    
    db.commit()
    
    # Активируем
    activate_case(db, test_case.id)
    
    # Проверяем UI
    response = client.get(f"/ui/cases/{test_case.id}")
    assert response.status_code == 200
    
    html = response.text
    
    # Должна быть информация об активации
    assert "Закупка активирована" in html
    
    # Должны быть секции анализа рынка
    assert "Параметры закупки" in html
    assert "Кандидаты и ранк-анализ" in html or "Анализ рынка" in html

