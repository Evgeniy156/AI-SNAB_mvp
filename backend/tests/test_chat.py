"""Тесты для API чата с LLM."""
import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.models.case import Case
from app.models.supplier import Supplier
from app.models.procurement import CaseCandidate, CommercialOffer
from decimal import Decimal


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


@pytest.fixture
def test_supplier(db):
    """Создать тестового поставщика."""
    supplier = Supplier(name="Тестовый поставщик", inn="1234567890")
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@pytest.fixture
def test_case(db):
    """Создать тестовый кейс."""
    case = Case(
        code="TEST-CASE-001",
        title="Тестовая закупка",
        subject="Тестовый предмет закупки",
        initiator_department="Отдел тестирования"
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@pytest.fixture
def test_case_with_supplier(db, test_supplier):
    """Создать тестовый кейс с поставщиком."""
    case = Case(
        code="TEST-CASE-002",
        title="Тестовая закупка с поставщиком",
        supplier_id=test_supplier.id,
        subject="Тестовый предмет закупки",
        initiator_department="Отдел тестирования"
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def test_chat_without_context(client):
    """Тест: чат без контекста (общий вопрос)."""
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "message": {
            "content": "Это тестовый ответ от LLM"
        }
    }
    mock_response.raise_for_status = lambda: None
    
    mock_client_instance = MagicMock()
    mock_client_instance.post = AsyncMock(return_value=mock_response)
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
    
    with patch("httpx.AsyncClient", return_value=mock_client_instance):
        response = client.post(
            "/api/chat",
            json={
                "message": "Привет, как дела?"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert data["response"] == "Это тестовый ответ от LLM"
        assert "context_used" in data


def test_chat_with_case_id(client, db, test_case):
    """Тест: чат с контекстом кейса."""
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "message": {
            "content": "Вот информация о кейсе"
        }
    }
    mock_response.raise_for_status = lambda: None
    
    mock_client_instance = MagicMock()
    mock_client_instance.post = AsyncMock(return_value=mock_response)
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
    
    with patch("httpx.AsyncClient", return_value=mock_client_instance):
        response = client.post(
            "/api/chat",
            json={
                "message": "Расскажи о кейсе",
                "case_id": str(test_case.id)
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "context_used" in data
        assert "case" in data["context_used"]
        assert data["context_used"]["case"]["code"] == "TEST-CASE-001"


def test_chat_with_supplier_id(client, db, test_supplier):
    """Тест: чат с контекстом поставщика."""
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "message": {
            "content": "Вот информация о поставщике"
        }
    }
    mock_response.raise_for_status = lambda: None
    
    mock_client_instance = MagicMock()
    mock_client_instance.post = AsyncMock(return_value=mock_response)
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
    
    with patch("httpx.AsyncClient", return_value=mock_client_instance):
        response = client.post(
            "/api/chat",
            json={
                "message": "Расскажи о поставщике",
                "supplier_id": str(test_supplier.id)
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "context_used" in data


def test_chat_with_missing_case_id(client):
    """Тест: чат с несуществующим case_id - должен вернуть guardrail ответ."""
    response = client.post(
        "/api/chat",
        json={
            "message": "Расскажи о кейсе",
            "case_id": str(uuid.uuid4())
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "нет данных в системе" in data["response"].lower() or "отсутствует" in data["response"].lower()


def test_chat_with_missing_supplier_id(client):
    """Тест: чат с несуществующим supplier_id - должен вернуть guardrail ответ."""
    response = client.post(
        "/api/chat",
        json={
            "message": "Расскажи о поставщике",
            "supplier_id": str(uuid.uuid4())
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "нет данных в системе" in data["response"].lower() or "отсутствует" in data["response"].lower()


def test_chat_with_case_and_supplier(client, db, test_case, test_supplier):
    """Тест: чат с контекстом кейса и поставщика."""
    test_case.supplier_id = test_supplier.id
    db.commit()
    
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "message": {
            "content": "Вот информация о кейсе и поставщике"
        }
    }
    mock_response.raise_for_status = lambda: None
    
    mock_client_instance = MagicMock()
    mock_client_instance.post = AsyncMock(return_value=mock_response)
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
    
    with patch("httpx.AsyncClient", return_value=mock_client_instance):
        response = client.post(
            "/api/chat",
            json={
                "message": "Расскажи о кейсе и поставщике",
                "case_id": str(test_case.id),
                "supplier_id": str(test_supplier.id)
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "context_used" in data
        assert "case" in data["context_used"]
        assert "supplier" in data["context_used"]


def test_chat_with_case_candidates(client, db, test_case):
    """Тест: чат с кейсом, содержащим кандидатов."""
    # Добавляем кандидата
    candidate = CaseCandidate(
        case_id=test_case.id,
        org_name="Кандидат 1",
        inn="9876543210",
        status="NEW"
    )
    db.add(candidate)
    db.commit()
    
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "message": {
            "content": "Вот информация о кандидатах"
        }
    }
    mock_response.raise_for_status = lambda: None
    
    mock_client_instance = MagicMock()
    mock_client_instance.post = AsyncMock(return_value=mock_response)
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
    
    with patch("httpx.AsyncClient", return_value=mock_client_instance):
        response = client.post(
            "/api/chat",
            json={
                "message": "Сколько кандидатов в кейсе?",
                "case_id": str(test_case.id)
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "context_used" in data
        assert "case" in data["context_used"]
        assert len(data["context_used"]["case"]["candidates"]) == 1


def test_chat_with_commercial_offers(client, db, test_case):
    """Тест: чат с кейсом, содержащим коммерческие предложения."""
    # Добавляем кандидата
    candidate = CaseCandidate(
        case_id=test_case.id,
        org_name="Кандидат 1",
        status="NEW"
    )
    db.add(candidate)
    db.flush()
    
    # Добавляем КП
    offer = CommercialOffer(
        case_id=test_case.id,
        candidate_id=candidate.id,
        price_total=Decimal("100000.00"),
        currency="RUB"
    )
    db.add(offer)
    db.commit()
    
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "message": {
            "content": "Вот информация о коммерческих предложениях"
        }
    }
    mock_response.raise_for_status = lambda: None
    
    mock_client_instance = MagicMock()
    mock_client_instance.post = AsyncMock(return_value=mock_response)
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
    
    with patch("httpx.AsyncClient", return_value=mock_client_instance):
        response = client.post(
            "/api/chat",
            json={
                "message": "Какие коммерческие предложения есть?",
                "case_id": str(test_case.id)
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "context_used" in data
        assert "case" in data["context_used"]
        assert len(data["context_used"]["case"]["commercial_offers"]) == 1


def test_chat_ollama_error(client):
    """Тест: обработка ошибки подключения к Ollama."""
    mock_client_instance = MagicMock()
    mock_client_instance.post = AsyncMock(side_effect=Exception("Connection error"))
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
    
    with patch("httpx.AsyncClient", return_value=mock_client_instance):
        response = client.post(
            "/api/chat",
            json={
                "message": "Привет"
            }
        )
        
        # Должна быть ошибка 500 или 503
        assert response.status_code in [500, 503]


def test_chat_empty_message(client):
    """Тест: валидация пустого сообщения."""
    response = client.post(
        "/api/chat",
        json={
            "message": ""
        }
    )
    
    # Должна быть ошибка валидации
    assert response.status_code == 422

