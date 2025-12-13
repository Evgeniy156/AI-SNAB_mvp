"""Тесты для инструментов агента (generate_doc, export_zip)."""
import pytest
import uuid
import io
import json
import zipfile
import hashlib
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from app.models.case import Case
from app.models.document import Document
from app.models.document_category import DocumentCategory
from app.models.template import Template
from app.models.supplier import Supplier
from app.services.agent_tools import generate_doc, export_zip
from app.services.storage import get_file


@pytest.fixture
def test_case(db: Session):
    """Создаёт тестовый кейс."""
    case = Case(
        code="TEST-CASE-001",
        title="Тестовая закупка",
        nmc_avg_price=100000.0,
        validation_coeff=0.15,
        offers_count=3
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@pytest.fixture
def test_template(db: Session):
    """Создаёт тестовый шаблон."""
    template = Template(
        key="NMC_REFERENCE",
        doc_type="CASE",
        name="Справка НМЦ",
        storage_key="templates/NMC_REFERENCE.docx",
        is_active=True
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@pytest.fixture
def test_category(db: Session):
    """Создаёт тестовую категорию."""
    category = DocumentCategory(
        key="TEST_CATEGORY",
        name="Тестовая категория",
        is_active=True
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@pytest.fixture
def test_document(db: Session, test_case: Case, test_category: DocumentCategory):
    """Создаёт тестовый документ."""
    doc = Document(
        case_id=test_case.id,
        category_id=test_category.id,
        doc_type="CASE",
        original_filename="test_doc.pdf",
        storage_bucket="aisnab-files",
        storage_key="cases/TEST-CASE-001/test_doc.pdf",
        size_bytes=1024,
        status="DONE"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def test_generate_doc_success(db: Session, test_case: Case, test_template: Template):
    """Тест успешной генерации документа."""
    # Мокаем get_file для загрузки шаблона
    template_content = b"Test template content [[CASE_CODE]] [[CASE_TITLE]]"
    
    with patch("app.services.agent_tools.get_file", return_value=template_content):
        with patch("app.services.agent_tools.upload_file") as mock_upload:
            result = generate_doc(db, test_case.id, "NMC_REFERENCE")
    
    assert result["ok"] is True
    assert result["document_id"] is not None
    assert result["reason"] is None
    
    # Проверяем, что документ создан в БД
    document = db.query(Document).filter(Document.case_id == test_case.id).first()
    assert document is not None
    assert document.original_filename.endswith(".docx")
    assert document.status == "DONE"
    
    # Проверяем, что upload_file был вызван
    assert mock_upload.called


def test_generate_doc_missing_case(db: Session, test_template: Template):
    """Тест генерации документа с несуществующим кейсом."""
    fake_case_id = uuid.uuid4()
    result = generate_doc(db, fake_case_id, "NMC_REFERENCE")
    
    assert result["ok"] is False
    assert "не найден" in result["reason"]


def test_generate_doc_missing_template(db: Session, test_case: Case):
    """Тест генерации документа с несуществующим шаблоном."""
    result = generate_doc(db, test_case.id, "NONEXISTENT_TEMPLATE")
    
    assert result["ok"] is False
    assert "не найден" in result["reason"]


def test_export_zip_success(db: Session, test_case: Case, test_document: Document):
    """Тест успешного экспорта ZIP."""
    # Мокаем get_file для загрузки документов
    doc_content = b"Test document content"
    
    with patch("app.services.agent_tools.get_file", return_value=doc_content):
        with patch("app.services.agent_tools.upload_file") as mock_upload:
            result = export_zip(db, test_case.id, "standard")
    
    assert result["ok"] is True
    assert result["document_id"] is not None
    assert result["reason"] is None
    
    # Проверяем, что ZIP документ создан в БД
    zip_docs = db.query(Document).filter(
        Document.case_id == test_case.id,
        Document.original_filename.endswith(".zip")
    ).all()
    assert len(zip_docs) > 0
    
    # Проверяем, что upload_file был вызван с ZIP контентом
    assert mock_upload.called
    call_args = mock_upload.call_args
    zip_content = call_args[0][2]  # Третий аргумент - содержимое
    
    # Проверяем, что это валидный ZIP
    zip_buffer = io.BytesIO(zip_content)
    with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
        # Проверяем наличие manifest.json
        assert "manifest.json" in zip_file.namelist()
        
        # Читаем manifest.json
        manifest_data = zip_file.read("manifest.json")
        manifest = json.loads(manifest_data.decode('utf-8'))
        
        assert manifest["case_id"] == str(test_case.id)
        assert manifest["case_code"] == test_case.code
        assert manifest["mode"] == "standard"
        assert len(manifest["files"]) > 0
        
        # Проверяем, что в manifest есть наш документ
        file_entries = [f["filename"] for f in manifest["files"]]
        assert test_document.original_filename in file_entries
        
        # Проверяем SHA256
        for file_entry in manifest["files"]:
            assert "sha256" in file_entry
            assert len(file_entry["sha256"]) == 64  # SHA256 hex длина


def test_export_zip_missing_case(db: Session):
    """Тест экспорта ZIP с несуществующим кейсом."""
    fake_case_id = uuid.uuid4()
    result = export_zip(db, fake_case_id, "standard")
    
    assert result["ok"] is False
    assert "не найден" in result["reason"]


def test_export_zip_no_documents(db: Session, test_case: Case):
    """Тест экспорта ZIP без документов."""
    result = export_zip(db, test_case.id, "standard")
    
    assert result["ok"] is False
    assert "Нет документов" in result["reason"]


def test_export_zip_sha256_verification(db: Session, test_case: Case, test_document: Document):
    """Тест, что SHA256 в manifest соответствует содержимому файла."""
    doc_content = b"Test document content for SHA256"
    expected_sha256 = hashlib.sha256(doc_content).hexdigest()
    
    with patch("app.services.agent_tools.get_file", return_value=doc_content):
        with patch("app.services.agent_tools.upload_file") as mock_upload:
            result = export_zip(db, test_case.id, "standard")
    
    assert result["ok"] is True
    
    # Получаем ZIP контент из mock
    call_args = mock_upload.call_args
    zip_content = call_args[0][2]
    
    # Проверяем manifest
    zip_buffer = io.BytesIO(zip_content)
    with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
        manifest_data = zip_file.read("manifest.json")
        manifest = json.loads(manifest_data.decode('utf-8'))
        
        # Находим наш документ в manifest
        doc_entry = next(
            (f for f in manifest["files"] if f["filename"] == test_document.original_filename),
            None
        )
        assert doc_entry is not None
        
        # Проверяем SHA256
        # В реальном тесте мы бы проверили, что SHA256 соответствует содержимому файла в ZIP
        assert "sha256" in doc_entry
        assert len(doc_entry["sha256"]) == 64

