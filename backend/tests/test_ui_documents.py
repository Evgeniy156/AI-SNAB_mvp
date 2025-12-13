"""Тесты для UI документов."""
import pytest
import uuid
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from app.main import app
from app.models.case import Case
from app.models.document_category import DocumentCategory
from app.models.document import Document
from app.models.supplier import Supplier


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


@pytest.fixture
def test_case(db):
    """Создать тестовый кейс."""
    import uuid
    supplier = Supplier(name="Тестовый поставщик")
    db.add(supplier)
    db.commit()
    
    # Используем уникальный код для каждого теста
    unique_code = f"TEST-{uuid.uuid4().hex[:8]}"
    case = Case(code=unique_code, title="Тестовый кейс", supplier_id=supplier.id)
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@pytest.fixture
def test_categories(db):
    """Создать тестовые категории (активная и неактивная)."""
    import uuid
    unique_suffix = uuid.uuid4().hex[:8]
    active = DocumentCategory(key=f"ACTIVE_{unique_suffix}", name="Активная категория", is_active=True)
    inactive = DocumentCategory(key=f"INACTIVE_{unique_suffix}", name="Неактивная категория", is_active=False)
    db.add(active)
    db.add(inactive)
    db.commit()
    db.refresh(active)
    db.refresh(inactive)
    return {"active": active, "inactive": inactive}


def test_ui_documents_dropdown_only_active(client, db, test_case, test_categories):
    """Тест: dropdown показывает только активные категории."""
    response = client.get(f"/ui/documents?case_id={test_case.id}")
    assert response.status_code == 200
    html = response.text
    
    # Активная категория должна быть в HTML
    assert test_categories["active"].name in html
    assert test_categories["active"].id.hex in html
    
    # Неактивная категория НЕ должна быть в dropdown
    # (но может быть в других местах страницы, поэтому проверяем что её нет в select)
    select_start = html.find('<select')
    select_end = html.find('</select>', select_start)
    if select_start != -1 and select_end != -1:
        select_html = html[select_start:select_end]
        assert test_categories["inactive"].id.hex not in select_html


def test_ui_documents_context_mode_hides_case_dropdown(client, db, test_case, test_categories):
    """Тест: в контекстном режиме (case_id в query) скрыт dropdown кейса, используется hidden input."""
    response = client.get(f"/ui/documents?case_id={test_case.id}")
    assert response.status_code == 200
    html = response.text
    
    # Должен быть hidden input с case_id
    assert f'<input type="hidden" name="case_id" value="{test_case.id}">' in html or f'name="case_id" value="{test_case.id}"' in html
    
    # НЕ должно быть активного select для case_id в форме загрузки
    # Ищем форму загрузки
    form_start = html.find('<form', html.find('Загрузить документ'))
    form_end = html.find('</form>', form_start)
    if form_start != -1 and form_end != -1:
        form_html = html[form_start:form_end]
        # Проверяем что нет активного select для case_id (может быть disabled, но не active)
        # Или что есть hidden input вместо select
        assert 'type="hidden"' in form_html or '<select' not in form_html or 'disabled' in form_html
    
    # Должен показываться код кейса
    assert test_case.code in html
    
    # Документы должны фильтроваться по кейсу (если есть документы)
    # Это проверяется через то, что страница загружается без ошибок


def test_ui_documents_upload_creates_row_and_calls_storage(client, db, test_case, test_categories):
    """Тест: upload создает запись в БД и вызывает storage."""
    from unittest.mock import patch, MagicMock
    
    # Мокаем очередь чтобы не пытаться подключиться к Redis
    mock_queue = MagicMock()
    with patch('app.services.storage.upload_file') as mock_upload, \
         patch('app.services.storage.ensure_bucket_exists') as mock_ensure, \
         patch('app.services.documents.get_queue', return_value=mock_queue):
        
        # Подготовка файла
        file_content = b"test file content"
        files = {"file": ("test.txt", file_content, "text/plain")}
        data = {
            "case_id": str(test_case.id),
            "category_id": str(test_categories["active"].id)
        }
        
        response = client.post("/ui/documents/upload", files=files, data=data)
        
        # Проверяем redirect
        assert response.status_code == 303
        assert f"case_id={test_case.id}" in response.headers["location"]
        
        # Проверяем что документ создан в БД со статусом IN_PROGRESS (не DONE)
        doc = db.query(Document).filter(Document.case_id == test_case.id).first()
        assert doc is not None
        assert doc.original_filename == "test.txt"
        assert doc.status == "IN_PROGRESS"  # Должен быть IN_PROGRESS, обработка в воркере
        assert doc.storage_key.startswith(f"cases/{test_case.code}/")
        assert doc.size_bytes == len(file_content)
        assert doc.content_type == "text/plain"
        
        # Проверяем что storage был вызван
        mock_ensure.assert_called_once()
        mock_upload.assert_called_once()
        # Проверяем параметры вызова
        call_args = mock_upload.call_args
        assert call_args[0][0] == "aisnab-files"  # bucket
        assert call_args[0][1].startswith(f"cases/{test_case.code}/")  # storage_key
        assert call_args[0][2] == file_content  # content
        
        # Проверяем что задача поставлена в очередь
        mock_queue.enqueue.assert_called_once()


def test_ui_documents_download_redirects_to_presigned_url(client, db, test_case, test_categories):
    """Тест: download редиректит на presigned URL."""
    # Создаем документ вручную
    doc = Document(
        case_id=test_case.id,
        category_id=test_categories["active"].id,
        original_filename="test.txt",
        storage_bucket="aisnab-files",
        storage_key="cases/TEST-001/test_key.txt",
        status="DONE"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    with patch('app.services.storage.presigned_get_url') as mock_presign:
        mock_presign.return_value = "http://example.com/presigned-url"
        
        response = client.get(f"/ui/documents/{doc.id}/download", follow_redirects=False)
        
        assert response.status_code == 302
        assert response.headers["location"] == "http://example.com/presigned-url"
        mock_presign.assert_called_once_with("aisnab-files", "cases/TEST-001/test_key.txt", expires=3600)


def test_ui_documents_download_error_if_not_done(client, db, test_case, test_categories):
    """Тест: download возвращает ошибку если статус не DONE."""
    doc = Document(
        case_id=test_case.id,
        category_id=test_categories["active"].id,
        original_filename="test.txt",
        storage_bucket="aisnab-files",
        storage_key="cases/TEST-001/test_key.txt",
        status="IN_PROGRESS"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    response = client.get(f"/ui/documents/{doc.id}/download")
    assert response.status_code == 400


def test_ui_documents_upload_enqueues_job(client, db, test_case, test_categories):
    """Тест: upload создает документ со статусом IN_PROGRESS и ставит задачу в очередь."""
    from unittest.mock import patch, MagicMock
    
    # Мокаем очередь и storage
    mock_queue = MagicMock()
    with patch('app.services.storage.upload_file') as mock_upload, \
         patch('app.services.storage.ensure_bucket_exists') as mock_ensure, \
         patch('app.services.queue.get_queue', return_value=mock_queue):
        # Подготовка файла
        file_content = b"test file content"
        files = {"file": ("test.txt", file_content, "text/plain")}
        data = {
            "case_id": str(test_case.id),
            "category_id": str(test_categories["active"].id)
        }
        
        response = client.post("/ui/documents/upload", files=files, data=data)
        
        # Проверяем redirect
        assert response.status_code == 303
        assert f"case_id={test_case.id}" in response.headers["location"]
        
        # Проверяем что документ создан в БД со статусом IN_PROGRESS
        doc = db.query(Document).filter(Document.case_id == test_case.id).first()
        assert doc is not None
        assert doc.original_filename == "test.txt"
        assert doc.status == "IN_PROGRESS"  # Должен быть IN_PROGRESS, не DONE
        assert doc.storage_key.startswith(f"cases/{test_case.code}/")
        assert doc.size_bytes == len(file_content)
        
        # Проверяем что задача поставлена в очередь
        mock_queue.enqueue.assert_called_once()
        # Проверяем что вызван process_document с правильным ID
        call_args = mock_queue.enqueue.call_args
        assert call_args[0][0].__name__ == "process_document"  # Функция process_document
        assert call_args[0][1] == doc.id  # document_id


def test_process_document_changes_status_to_done(db, test_case, test_categories):
    """Тест: process_document меняет статус документа на DONE."""
    from app.jobs.documents import process_document
    
    # Создаем документ со статусом IN_PROGRESS (как после upload)
    doc = Document(
        case_id=test_case.id,
        category_id=test_categories["active"].id,
        original_filename="test.txt",
        storage_bucket="aisnab-files",
        storage_key="cases/TEST-001/test_key.txt",
        status="IN_PROGRESS",
        size_bytes=100,
        content_type="text/plain"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    doc_id = doc.id
    
    # Вызываем обработчик
    process_document(doc_id)
    
    # Проверяем что статус изменился на DONE
    db.refresh(doc)
    assert doc.status == "DONE"
    assert doc.error_message is None

