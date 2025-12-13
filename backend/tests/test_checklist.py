"""Тесты для чек-листа закупочной процедуры."""
import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.models.case import Case
from app.models.supplier import Supplier
from app.models.document import Document
from app.models.document_category import DocumentCategory
from app.models.checklist_template import ChecklistTemplate, ChecklistTemplateItem
from app.models.case_checklist import CaseChecklistItem, CaseChecklistItemDocument
from app.services.checklist import (
    ensure_case_checklist,
    update_checklist_item_status,
    attach_document_to_checklist_item,
    detach_document_from_checklist_item
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
def test_case(db, test_supplier, test_template):
    """Создать тестовый кейс с привязанным шаблоном."""
    unique_code = f"TEST-{uuid.uuid4().hex[:8]}"
    case = Case(
        code=unique_code,
        title="Тестовый кейс",
        supplier_id=test_supplier.id,
        checklist_template_id=test_template.id
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@pytest.fixture
def test_template(db):
    """Создать тестовый шаблон чек-листа с 3 пунктами."""
    import uuid
    template = ChecklistTemplate(
        key=f"TEST_TEMPLATE_{uuid.uuid4().hex[:8]}",
        name="Тестовый шаблон",
        is_active=True,
        is_default=True
    )
    db.add(template)
    db.flush()
    
    items = [
        ChecklistTemplateItem(
            template_id=template.id,
            section="I. Тестовая секция",
            group_title="1. Группа 1",
            title="Пункт 1",
            is_required=True,
            sort_order=1
        ),
        ChecklistTemplateItem(
            template_id=template.id,
            section="I. Тестовая секция",
            group_title="1. Группа 1",
            title="Пункт 2",
            is_required=True,
            sort_order=2
        ),
        ChecklistTemplateItem(
            template_id=template.id,
            section="II. Вторая секция",
            group_title=None,
            title="Пункт 3",
            is_required=False,
            sort_order=3
        ),
    ]
    db.add_all(items)
    db.commit()
    db.refresh(template)
    return template


@pytest.fixture
def test_category(db):
    """Создать тестовую категорию документов."""
    import uuid
    category = DocumentCategory(key=f"TEST_{uuid.uuid4().hex[:8]}", name="Тестовая категория", is_active=True)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def test_ensure_case_checklist_creates_items_idempotent(db, test_case, test_template):
    """Тест: ensure_case_checklist создает items идемпотентно."""
    # Первый вызов - создает 3 items
    items1 = ensure_case_checklist(db, test_case.id)
    assert len(items1) == 3
    
    # Второй вызов - не создает дубликаты
    items2 = ensure_case_checklist(db, test_case.id)
    assert len(items2) == 3
    
    # Проверяем, что в БД ровно 3 записи
    count = db.query(CaseChecklistItem).filter(
        CaseChecklistItem.case_id == test_case.id
    ).count()
    assert count == 3
    
    # Проверяем, что все items имеют статус TODO
    for item in items2:
        assert item.status == "TODO"
        assert item.template_item is not None


def test_checklist_update_status_changes_row(db, test_case, test_template):
    """Тест: update_checklist_item_status изменяет статус и комментарий."""
    # Инициализируем чек-лист
    items = ensure_case_checklist(db, test_case.id)
    assert len(items) > 0
    item = items[0]
    
    # Обновляем статус и комментарий
    updated = update_checklist_item_status(
        db, test_case.id, item.id, "DONE", "Тестовый комментарий"
    )
    
    assert updated.status == "DONE"
    assert updated.comment == "Тестовый комментарий"
    
    # Проверяем в БД
    db_item = db.query(CaseChecklistItem).filter(
        CaseChecklistItem.id == item.id
    ).first()
    assert db_item.status == "DONE"
    assert db_item.comment == "Тестовый комментарий"


def test_attach_document_only_same_case(db, test_case, test_template, test_category):
    """Тест: attach_document разрешает только документы того же кейса."""
    # Инициализируем чек-лист
    items = ensure_case_checklist(db, test_case.id)
    item = items[0]
    
    # Создаем документ в этом кейсе
    doc1 = Document(
        case_id=test_case.id,
        category_id=test_category.id,
        doc_type="CASE",
        original_filename="test1.pdf",
        storage_bucket="test-bucket",
        storage_key="test1.pdf",
        status="DONE"
    )
    db.add(doc1)
    db.commit()
    db.refresh(doc1)
    
    # Создаем другой кейс и документ в нем
    other_case = Case(code=f"OTHER-{uuid.uuid4().hex[:8]}", title="Другой кейс")
    db.add(other_case)
    db.commit()
    db.refresh(other_case)
    
    doc2 = Document(
        case_id=other_case.id,
        category_id=test_category.id,
        doc_type="CASE",
        original_filename="test2.pdf",
        storage_bucket="test-bucket",
        storage_key="test2.pdf",
        status="DONE"
    )
    db.add(doc2)
    db.commit()
    db.refresh(doc2)
    
    # Прикрепляем документ из того же кейса - должно работать
    attach_document_to_checklist_item(db, test_case.id, item.id, doc1.id)
    
    link = db.query(CaseChecklistItemDocument).filter(
        CaseChecklistItemDocument.case_checklist_item_id == item.id,
        CaseChecklistItemDocument.document_id == doc1.id
    ).first()
    assert link is not None
    
    # Пытаемся прикрепить документ из другого кейса - должно выбросить ошибку
    with pytest.raises(ValueError, match="не принадлежит кейсу"):
        attach_document_to_checklist_item(db, test_case.id, item.id, doc2.id)
    
    # Проверяем идемпотентность - повторное прикрепление не создает дубликат
    attach_document_to_checklist_item(db, test_case.id, item.id, doc1.id)
    count = db.query(CaseChecklistItemDocument).filter(
        CaseChecklistItemDocument.case_checklist_item_id == item.id,
        CaseChecklistItemDocument.document_id == doc1.id
    ).count()
    assert count == 1


def test_epoz_clause_saved_on_case(db, test_case, client):
    """Тест: epoz_clause сохраняется на кейсе через UI endpoint."""
    # Проверяем, что поле пустое
    assert test_case.epoz_clause is None
    
    # Обновляем через POST
    response = client.post(
        f"/ui/cases/{test_case.id}/epoz/update",
        data={"epoz_clause": "6.6.2.1"},
        follow_redirects=False
    )
    assert response.status_code == 303
    
    # Проверяем в БД
    db.refresh(test_case)
    assert test_case.epoz_clause == "6.6.2.1"
    
    # Обновляем на другое значение
    response = client.post(
        f"/ui/cases/{test_case.id}/epoz/update",
        data={"epoz_clause": "6.6.2.3 (1)"},
        follow_redirects=False
    )
    assert response.status_code == 303
    
    db.refresh(test_case)
    assert test_case.epoz_clause == "6.6.2.3 (1)"


def test_detach_document(db, test_case, test_template, test_category):
    """Тест: detach_document открепляет документ от пункта."""
    # Инициализируем чек-лист
    items = ensure_case_checklist(db, test_case.id)
    item = items[0]
    
    # Создаем и прикрепляем документ
    doc = Document(
        case_id=test_case.id,
        category_id=test_category.id,
        doc_type="CASE",
        original_filename="test.pdf",
        storage_bucket="test-bucket",
        storage_key="test.pdf",
        status="DONE"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    attach_document_to_checklist_item(db, test_case.id, item.id, doc.id)
    
    # Проверяем, что связь создана
    link = db.query(CaseChecklistItemDocument).filter(
        CaseChecklistItemDocument.case_checklist_item_id == item.id,
        CaseChecklistItemDocument.document_id == doc.id
    ).first()
    assert link is not None
    
    # Открепляем
    detach_document_from_checklist_item(db, test_case.id, item.id, doc.id)
    
    # Проверяем, что связь удалена
    link = db.query(CaseChecklistItemDocument).filter(
        CaseChecklistItemDocument.case_checklist_item_id == item.id,
        CaseChecklistItemDocument.document_id == doc.id
    ).first()
    assert link is None

