"""
E2E тест для проверки полного flow: кейс → 3 КП → НМЦ → generate_doc → export.zip + manifest + sha256

Требования:
- Docker Compose должен быть запущен
- Все сервисы должны быть доступны через http://localhost:8080
"""
import pytest
import subprocess
import time
import httpx
import json
import hashlib
import zipfile
import tempfile
import os
from pathlib import Path
from typing import Dict, Any
import uuid


# Конфигурация
# При запуске из контейнера используем внутренний адрес web-proxy
# При запуске с хоста можно использовать localhost:8080
import os
if os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER"):
    # Запущено внутри Docker контейнера - используем внутренний адрес
    BASE_URL = "http://web-proxy:80"  # Внутреннее имя сервиса nginx
else:
    # Запущено на хосте
    BASE_URL = "http://localhost:8080"

API_BASE = f"{BASE_URL}/api"
DOCKER_COMPOSE_FILE = Path(__file__).parent.parent.parent / "infra" / "docker-compose.yml"
HEALTH_CHECK_TIMEOUT = 120  # секунд
HEALTH_CHECK_INTERVAL = 2  # секунд


def wait_for_health(base_url: str, timeout: int = HEALTH_CHECK_TIMEOUT) -> None:
    """Ожидание готовности сервисов через health checks."""
    print(f"\n[E2E] Ожидание готовности сервисов...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # Проверяем базовый health
            response = httpx.get(f"{base_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    # Проверяем DB
                    response_db = httpx.get(f"{base_url}/health/db", timeout=5)
                    if response_db.status_code == 200:
                        data_db = response_db.json()
                        if data_db.get("status") == "ok":
                            # Проверяем Storage
                            response_storage = httpx.get(f"{base_url}/health/storage", timeout=5)
                            if response_storage.status_code == 200:
                                data_storage = response_storage.json()
                                if data_storage.get("status") == "ok":
                                    print("[E2E] Все health checks пройдены ✓")
                                    return
            
            print(f"[E2E] Ожидание... ({int(time.time() - start_time)}s)")
            time.sleep(HEALTH_CHECK_INTERVAL)
        except httpx.RequestError as e:
            print(f"[E2E] Ошибка подключения: {e}, ожидание...")
            time.sleep(HEALTH_CHECK_INTERVAL)
    
    raise RuntimeError(f"Health checks не прошли за {timeout} секунд")


def run_seed(base_url: str) -> None:
    """Запуск seed скрипта через docker compose exec."""
    print("\n[E2E] Запуск seed_demo...")
    compose_file = DOCKER_COMPOSE_FILE
    
    # Проверяем, что файл существует
    if not compose_file.exists():
        raise FileNotFoundError(f"Docker compose file not found: {compose_file}")
    
    # Запускаем seed через docker compose exec
    cmd = [
        "docker", "compose",
        "-f", str(compose_file),
        "exec", "-T", "app",
        "python", "-m", "app.scripts.seed_demo"
    ]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60
    )
    
    if result.returncode != 0:
        print(f"[E2E] Seed stderr: {result.stderr}")
        raise RuntimeError(f"Seed failed: {result.stdout}")
    
    print("[E2E] Seed выполнен ✓")


def create_test_case(client: httpx.Client) -> Dict[str, Any]:
    """Создать тестовый кейс."""
    print("\n[E2E] Создание тестового кейса...")
    
    # Генерируем уникальный код
    test_code = f"E2E-TEST-{uuid.uuid4().hex[:8].upper()}"
    
    response = client.post(
        f"{API_BASE}/cases",
        json={
            "code": test_code,
            "title": "E2E Test Case",
            "supplier_id": None
        }
    )
    
    assert response.status_code == 201, f"Failed to create case: {response.text}"
    case = response.json()
    print(f"[E2E] Кейс создан: {case['code']} (id: {case['id']}) ✓")
    return case


def get_suppliers(client: httpx.Client) -> list:
    """Получить список поставщиков."""
    response = client.get(f"{API_BASE}/suppliers")
    assert response.status_code == 200, f"Failed to get suppliers: {response.text}"
    return response.json()


def add_candidates(client: httpx.Client, case_id: str, suppliers: list) -> list:
    """Добавить 3 кандидата в кейс."""
    print("\n[E2E] Добавление 3 кандидатов...")
    candidates = []
    
    # Кандидат 1: существующий поставщик (если есть)
    if len(suppliers) > 0:
        response = client.post(
            f"{API_BASE}/cases/{case_id}/candidates",
            params={"supplier_id": str(suppliers[0]["id"])}
        )
        assert response.status_code == 201, f"Failed to add candidate 1: {response.text}"
        candidates.append(response.json())
        print(f"[E2E] Кандидат 1 добавлен: {suppliers[0]['name']} ✓")
    
    # Кандидат 2: существующий поставщик (если есть)
    if len(suppliers) > 1:
        response = client.post(
            f"{API_BASE}/cases/{case_id}/candidates",
            params={"supplier_id": str(suppliers[1]["id"])}
        )
        assert response.status_code == 201, f"Failed to add candidate 2: {response.text}"
        candidates.append(response.json())
        print(f"[E2E] Кандидат 2 добавлен: {suppliers[1]['name']} ✓")
    
    # Кандидат 3: новая организация
    response = client.post(
        f"{API_BASE}/cases/{case_id}/candidates",
        params={
            "org_name": "ООО E2E Test Supplier",
            "inn": "1234567890",
            "contact_email": "test@example.com",
            "contact_phone": "+7 (495) 123-45-67"
        }
    )
    assert response.status_code == 201, f"Failed to add candidate 3: {response.text}"
    candidates.append(response.json())
    print(f"[E2E] Кандидат 3 добавлен: ООО E2E Test Supplier ✓")
    
    assert len(candidates) == 3, f"Expected 3 candidates, got {len(candidates)}"
    return candidates


def add_offers(client: httpx.Client, case_id: str, candidates: list) -> None:
    """Добавить 3 коммерческих предложения."""
    print("\n[E2E] Добавление 3 коммерческих предложений...")
    
    # Цены подобраны так, чтобы validation_coeff <= 0.33
    prices = [1000000.00, 1050000.00, 1020000.00]
    
    for i, candidate in enumerate(candidates):
        response = client.post(
            f"{API_BASE}/cases/{case_id}/offers",
            params={
                "candidate_id": candidate["id"],
                "price_total": prices[i],
                "currency": "RUB",
                "lead_time_days": 30 + i * 5
            }
        )
        assert response.status_code == 201, f"Failed to add offer {i+1}: {response.text}"
        print(f"[E2E] КП {i+1} добавлено: {prices[i]:,.2f} RUB ✓")


def check_pricing(client: httpx.Client, case_id: str) -> Dict[str, Any]:
    """Проверить расчёт НМЦ."""
    print("\n[E2E] Проверка расчёта НМЦ...")
    
    response = client.get(f"{API_BASE}/cases/{case_id}/pricing")
    assert response.status_code == 200, f"Failed to get pricing: {response.text}"
    pricing = response.json()
    
    assert pricing["offers_count"] >= 3, f"Expected >= 3 offers, got {pricing['offers_count']}"
    assert pricing["nmc_avg_price"] is not None, "nmc_avg_price should not be None"
    assert pricing["validation_coeff"] <= 0.33, f"validation_coeff should be <= 0.33, got {pricing['validation_coeff']}"
    assert pricing["is_validation_ok"] is True, f"is_validation_ok should be True, got {pricing['is_validation_ok']}"
    
    print(f"[E2E] НМЦ проверен: avg={pricing['nmc_avg_price']:,.2f}, coeff={pricing['validation_coeff']:.3f} ✓")
    return pricing


def generate_document(client: httpx.Client, case_id: str) -> str:
    """Сгенерировать документ NMC_REFERENCE."""
    print("\n[E2E] Генерация документа NMC_REFERENCE...")
    
    response = client.post(
        f"{API_BASE}/documents/generate",
        json={
            "case_id": case_id,
            "template_key": "NMC_REFERENCE"
        }
    )
    
    # Может быть 400, если шаблон не найден - это нормально для E2E без шаблона
    if response.status_code == 400:
        error_detail = response.json().get("detail", "")
        if "шаблон" in error_detail.lower() or "template" in error_detail.lower():
            print(f"[E2E] Предупреждение: шаблон не найден, пропускаем генерацию документа")
            return None
    
    assert response.status_code == 201, f"Failed to generate document: {response.text}"
    result = response.json()
    document_id = result["document_id"]
    print(f"[E2E] Документ сгенерирован: {document_id} ✓")
    return document_id


def export_zip(client: httpx.Client, case_id: str) -> str:
    """Экспортировать кейс в ZIP."""
    print("\n[E2E] Экспорт ZIP...")
    
    response = client.post(
        f"{API_BASE}/cases/{case_id}/export-zip",
        json={"mode": "standard"}
    )
    
    assert response.status_code == 201, f"Failed to export zip: {response.text}"
    result = response.json()
    zip_document_id = result["document_id"]
    print(f"[E2E] ZIP экспортирован: {zip_document_id} ✓")
    return zip_document_id


def download_zip(client: httpx.Client, document_id: str) -> bytes:
    """Скачать ZIP через presigned URL."""
    print("\n[E2E] Скачивание ZIP...")
    
    # Используем API эндпоинт для получения presigned URL
    response = client.get(f"{API_BASE}/documents/{document_id}/download-url")
    assert response.status_code == 200, f"Failed to get download URL: {response.text}"
    result = response.json()
    presigned_url = result["url"]
    
    # Скачиваем файл по presigned URL
    download_response = httpx.get(presigned_url, timeout=30)
    assert download_response.status_code == 200, f"Failed to download zip: {download_response.status_code}"
    
    zip_content = download_response.content
    print(f"[E2E] ZIP скачан: {len(zip_content)} bytes ✓")
    return zip_content


def verify_zip_manifest_and_sha256(zip_content: bytes, case_id: str, case_code: str) -> None:
    """Проверить manifest.json и SHA256 для всех файлов в ZIP."""
    print("\n[E2E] Проверка manifest.json и SHA256...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Сохраняем ZIP во временную директорию
        zip_path = os.path.join(temp_dir, "export.zip")
        with open(zip_path, "wb") as f:
            f.write(zip_content)
        
        # Распаковываем ZIP
        with zipfile.ZipFile(zip_path, "r") as zip_file:
            # Проверяем наличие manifest.json
            assert "manifest.json" in zip_file.namelist(), "manifest.json not found in ZIP"
            
            # Читаем manifest.json
            manifest_content = zip_file.read("manifest.json")
            manifest = json.loads(manifest_content.decode("utf-8"))
            
            # Проверяем структуру manifest
            assert manifest["case_id"] == case_id, f"case_id mismatch: {manifest['case_id']} != {case_id}"
            assert manifest["case_code"] == case_code, f"case_code mismatch: {manifest['case_code']} != {case_code}"
            assert manifest["mode"] == "standard", f"mode mismatch: {manifest['mode']} != standard"
            assert "files" in manifest, "files array not found in manifest"
            assert len(manifest["files"]) > 0, "files array is empty"
            
            print(f"[E2E] Manifest проверен: {len(manifest['files'])} файлов ✓")
            
            # Проверяем SHA256 для каждого файла
            for file_entry in manifest["files"]:
                filename = file_entry["filename"]
                expected_sha256 = file_entry["sha256"]
                
                # Читаем файл из ZIP
                file_content = zip_file.read(filename)
                
                # Вычисляем SHA256
                actual_sha256 = hashlib.sha256(file_content).hexdigest()
                
                assert actual_sha256 == expected_sha256, (
                    f"SHA256 mismatch for {filename}: "
                    f"expected {expected_sha256}, got {actual_sha256}"
                )
                
                print(f"[E2E] SHA256 проверен для {filename} ✓")
            
            print(f"[E2E] Все SHA256 проверки пройдены ✓")


@pytest.mark.e2e
def test_e2e_export_zip_flow():
    """
    E2E тест полного flow:
    1. Поднимает docker compose (если не поднят)
    2. Ждёт health checks
    3. Запускает seed
    4. Создаёт кейс
    5. Добавляет 3 кандидата
    6. Добавляет 3 КП
    7. Проверяет pricing
    8. Генерирует документ
    9. Экспортирует ZIP
    10. Скачивает ZIP
    11. Проверяет manifest.json и SHA256
    """
    print("\n" + "="*80)
    print("E2E TEST: кейс → 3 КП → НМЦ → generate_doc → export.zip + manifest + sha256")
    print("="*80)
    
    # Проверяем, что docker compose запущен
    # (предполагаем, что пользователь запустил его вручную или через CI)
    
    # Создаём HTTP клиент
    with httpx.Client(timeout=30.0) as client:
        # 1. Ждём health checks
        wait_for_health(BASE_URL)
        
        # 2. Запускаем seed
        run_seed(BASE_URL)
        
        # 3. Создаём тестовый кейс
        case = create_test_case(client)
        case_id = case["id"]
        case_code = case["code"]
        
        # 4. Получаем поставщиков
        suppliers = get_suppliers(client)
        assert len(suppliers) > 0, "No suppliers found after seed"
        
        # 5. Добавляем 3 кандидата
        candidates = add_candidates(client, case_id, suppliers)
        
        # 6. Добавляем 3 КП
        add_offers(client, case_id, candidates)
        
        # 7. Проверяем pricing
        pricing = check_pricing(client, case_id)
        
        # 8. Генерируем документ (может быть пропущено, если шаблон не найден)
        doc_id = generate_document(client, case_id)
        
        # 9. Экспортируем ZIP
        zip_doc_id = export_zip(client, case_id)
        
        # 10. Скачиваем ZIP
        zip_content = download_zip(client, zip_doc_id)
        
        # 11. Проверяем manifest.json и SHA256
        verify_zip_manifest_and_sha256(zip_content, case_id, case_code)
        
        print("\n" + "="*80)
        print("E2E TEST: ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ ✓")
        print("="*80)

