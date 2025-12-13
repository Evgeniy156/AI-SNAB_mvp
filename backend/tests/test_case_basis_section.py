"""Тесты для секции "Основание закупки" на странице кейса."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.case import Case
from app.models.checklist_template import ChecklistTemplate, ChecklistTemplateItem
from app.models.case_checklist import CaseChecklistItem
from app.services.checklist import ensure_case_checklist, split_checklist_items_by_basis


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


@pytest.fixture
def test_case(db, test_template_with_basis):
    """Создать тестовый кейс с привязанным шаблоном."""
    case = Case(
        code="TEST-BASIS-001",
        title="Тестовая закупка",
        checklist_template_id=test_template_with_basis.id
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@pytest.fixture
def test_template_with_basis(db):
    """Создать тестовый шаблон с пунктами основания."""
    import uuid
    template = ChecklistTemplate(
        key=f"TEST_BASIS_{uuid.uuid4().hex[:8]}",
        name="Тестовый шаблон",
        is_active=True,
        is_default=True
    )
    db.add(template)
    db.flush()
    
    # Пункт с group_title "Основание закупки"
    item1 = ChecklistTemplateItem(
        template_id=template.id,
        section="I. Подготовительный этап",
        group_title="1. Основание закупки",
        title="Пункт основания 1",
        is_required=True,
        sort_order=1
    )
    db.add(item1)
    
    # Пункт без основания
    item2 = ChecklistTemplateItem(
        template_id=template.id,
        section="II. Анализ рынка",
        group_title="2. Анализ рынка",
        title="Пункт анализа",
        is_required=True,
        sort_order=2
    )
    db.add(item2)
    
    db.commit()
    return template


def test_basis_section_rendered_first(client, db, test_case, test_template_with_basis):
    """Тест: секция '0. Основание закупки' должна быть первой на странице."""
    # Инициализируем чек-лист
    ensure_case_checklist(db, test_case.id)
    
    response = client.get(f"/ui/cases/{test_case.id}")
    assert response.status_code == 200
    
    html = response.text
    
    # Проверяем, что "0. Основание закупки" присутствует
    assert "0. Основание закупки" in html
    
    # Проверяем, что "0. Основание закупки" идёт раньше "1. Параметры закупки"
    basis_pos = html.find("0. Основание закупки")
    params_pos = html.find("1. Параметры закупки")
    
    assert basis_pos != -1, "Секция '0. Основание закупки' не найдена"
    assert params_pos != -1, "Секция '1. Параметры закупки' не найдена"
    assert basis_pos < params_pos, "Секция '0. Основание закупки' должна быть раньше '1. Параметры закупки'"


def test_supplier_not_shown_in_header(client, db, test_case):
    """Тест: в шапке страницы не должно быть строки 'Поставщик:'."""
    response = client.get(f"/ui/cases/{test_case.id}")
    assert response.status_code == 200
    
    html = response.text
    
    # Проверяем, что "Поставщик:" не присутствует в шапке
    # Ищем в блоке card-body заголовка
    header_start = html.find('<div class="card-body">')
    if header_start != -1:
        header_end = html.find('</div>', header_start + 1)
        header_section = html[header_start:header_end] if header_end != -1 else html[header_start:]
        
        # В заголовке не должно быть "Поставщик:"
        assert "Поставщик:" not in header_section, "В шапке не должно быть 'Поставщик:'"


def test_basis_items_not_duplicated_in_checklist(client, db, test_case, test_template_with_basis):
    """Тест: пункты основания не должны дублироваться в общем чек-листе."""
    # Инициализируем чек-лист
    ensure_case_checklist(db, test_case.id)
    
    # Получаем все пункты
    all_items = db.query(CaseChecklistItem).filter(
        CaseChecklistItem.case_id == test_case.id
    ).all()
    
    # Разделяем на основание и остальные
    basis_items, other_items = split_checklist_items_by_basis(all_items)
    
    # Проверяем, что пункты основания не входят в остальные
    basis_ids = {item.id for item in basis_items}
    other_ids = {item.id for item in other_items}
    
    assert len(basis_ids & other_ids) == 0, "Пункты основания не должны дублироваться в остальных"
    
    # Проверяем через UI
    response = client.get(f"/ui/cases/{test_case.id}")
    assert response.status_code == 200
    
    html = response.text
    
    # Считаем количество вхождений "Пункт основания 1"
    count = html.count("Пункт основания 1")
    
    # Должно быть только одно вхождение (в блоке основания)
    assert count == 1, f"Пункт 'Пункт основания 1' должен встречаться только один раз, найдено: {count}"


def test_split_checklist_items_by_basis(db, test_case, test_template_with_basis):
    """Тест: функция split_checklist_items_by_basis корректно разделяет пункты."""
    # Инициализируем чек-лист
    ensure_case_checklist(db, test_case.id)
    
    # Получаем все пункты
    all_items = db.query(CaseChecklistItem).options(
        lambda q: q.joinedload(CaseChecklistItem.template_item)
    ).filter(
        CaseChecklistItem.case_id == test_case.id
    ).all()
    
    # Разделяем
    basis_items, other_items = split_checklist_items_by_basis(all_items)
    
    # Проверяем, что пункт с "Основание закупки" в basis_items
    basis_titles = [item.template_item.title for item in basis_items if item.template_item]
    assert "Пункт основания 1" in basis_titles
    
    # Проверяем, что пункт без основания в other_items
    other_titles = [item.template_item.title for item in other_items if item.template_item]
    assert "Пункт анализа" in other_titles
    
    # Проверяем, что все пункты учтены
    assert len(basis_items) + len(other_items) == len(all_items)

