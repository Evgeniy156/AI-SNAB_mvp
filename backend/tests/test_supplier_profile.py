"""Тесты для профиля поставщика (карточка предприятия)."""
import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.models.supplier import Supplier
from app.models.supplier_profile import SupplierProfile, OkvedCode, SupplierEquipment, SupplierCertificate
from app.models.document import Document
from app.models.document_category import DocumentCategory
from app.services.supplier_profile import (
    get_or_create_supplier_profile,
    update_supplier_profile,
    set_supplier_okved,
    get_supplier_okved,
    add_supplier_equipment,
    add_supplier_certificate,
    get_supplier_context
)
from app.services.documents import create_document_with_file
from io import BytesIO


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
def test_category(db):
    """Создать тестовую категорию документов для поставщика."""
    category = DocumentCategory(key="SUPPLIER_CHARTER", name="Устав", is_active=True)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def test_supplier_profile_created_on_open(db, test_supplier):
    """Тест: профиль создается при открытии карточки."""
    # Профиля еще нет
    profile = db.query(SupplierProfile).filter(
        SupplierProfile.supplier_id == test_supplier.id
    ).first()
    assert profile is None
    
    # Создаем профиль
    profile = get_or_create_supplier_profile(db, test_supplier.id)
    assert profile is not None
    assert profile.supplier_id == test_supplier.id
    
    # Повторный вызов не создает дубликат
    profile2 = get_or_create_supplier_profile(db, test_supplier.id)
    assert profile.id == profile2.id


def test_update_supplier_profile_persists(db, test_supplier):
    """Тест: обновление профиля сохраняется."""
    profile = get_or_create_supplier_profile(db, test_supplier.id)
    
    # Обновляем поля
    update_supplier_profile(
        db, test_supplier.id,
        headcount_total=100,
        has_qms=True,
        qms_standards="ISO 9001:2015",
        business_description="Тестовое описание"
    )
    
    # Проверяем в БД
    db.refresh(profile)
    assert profile.headcount_total == 100
    assert profile.has_qms is True
    assert profile.qms_standards == "ISO 9001:2015"
    assert profile.business_description == "Тестовое описание"


def test_set_supplier_okved_creates_codes_and_links(db, test_supplier):
    """Тест: установка ОКВЭД создает коды и связи."""
    # Устанавливаем коды
    codes = set_supplier_okved(db, test_supplier.id, ["25.11", "25.12", "25.13"])
    assert len(codes) == 3
    
    # Проверяем, что коды созданы
    okved_codes = get_supplier_okved(db, test_supplier.id)
    assert len(okved_codes) == 3
    assert {code.code for code in okved_codes} == {"25.11", "25.12", "25.13"}
    
    # Повторная установка заменяет старые
    codes2 = set_supplier_okved(db, test_supplier.id, ["25.20", "25.30"])
    okved_codes2 = get_supplier_okved(db, test_supplier.id)
    assert len(okved_codes2) == 2
    assert {code.code for code in okved_codes2} == {"25.20", "25.30"}


def test_supplier_doc_upload_sets_supplier_id_and_enqueues(db, test_supplier, test_category):
    """Тест: загрузка документа поставщика устанавливает supplier_id и ставит в очередь."""
    # Создаем мок файл
    file_content = b"test file content"
    file = BytesIO(file_content)
    file.name = "test_document.pdf"
    
    from fastapi import UploadFile
    upload_file = UploadFile(file=file, filename="test_document.pdf")
    
    # Мокаем очередь
    from unittest.mock import patch, Mock
    with patch('app.services.documents.get_queue') as mock_queue:
        mock_queue_instance = Mock()
        mock_queue.return_value = mock_queue_instance
        
        # Загружаем документ
        document = create_document_with_file(
            db=db,
            category_id=test_category.id,
            file=upload_file,
            supplier_id=test_supplier.id
        )
        
        # Проверяем, что документ создан с supplier_id
        assert document.supplier_id == test_supplier.id
        assert document.case_id is None
        assert document.status == "IN_PROGRESS"
        assert "suppliers" in document.storage_key
        
        # Проверяем, что задача поставлена в очередь
        mock_queue_instance.enqueue.assert_called_once()


def test_supplier_context_api_returns_full_payload(db, test_supplier, client):
    """Тест: API контекста возвращает полный payload."""
    # Создаем профиль с данными
    profile = get_or_create_supplier_profile(db, test_supplier.id)
    profile.headcount_total = 150
    profile.has_qms = True
    profile.works_with_goz = True
    db.commit()
    
    # Добавляем ОКВЭД
    set_supplier_okved(db, test_supplier.id, ["25.11", "25.12"])
    
    # Добавляем оборудование
    add_supplier_equipment(db, test_supplier.id, "Станок", "Model-1", 5)
    
    # Добавляем сертификат
    from datetime import date
    add_supplier_certificate(
        db, test_supplier.id, "ISO 9001", "ISO-001",
        "Орган", "2023-01-01", "2026-01-01"
    )
    
    # Получаем контекст через API
    response = client.get(f"/api/suppliers/{test_supplier.id}/context")
    assert response.status_code == 200
    
    data = response.json()
    
    # Проверяем структуру
    assert "supplier" in data
    assert "profile" in data
    assert "okved_codes" in data
    assert "equipment" in data
    assert "certificates" in data
    assert "flags" in data
    assert "documents" in data
    
    # Проверяем данные
    assert data["supplier"]["id"] == str(test_supplier.id)
    assert data["profile"]["headcount_total"] == 150
    assert data["profile"]["has_qms"] is True
    assert len(data["okved_codes"]) == 2
    assert len(data["equipment"]) == 1
    assert len(data["certificates"]) == 1
    assert data["flags"]["has_qms"] is True
    assert data["flags"]["works_with_goz"] is True

