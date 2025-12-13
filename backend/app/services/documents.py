"""Service слой для работы с документами."""
from typing import List
import uuid
import os
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, UploadFile
from app.models.document import Document
from app.models.document_category import DocumentCategory
from app.models.case import Case
from app.services.storage import ensure_bucket_exists, upload_file
from app.core.settings import settings


def list_documents(
    db: Session,
    case_id: uuid.UUID | None = None,
    supplier_id: uuid.UUID | None = None
) -> List[Document]:
    """Получить список документов с подгрузкой case/supplier и category."""
    query = db.query(Document).options(
        joinedload(Document.case),
        joinedload(Document.supplier),
        joinedload(Document.category)
    )
    if case_id:
        query = query.filter(Document.case_id == case_id)
    if supplier_id:
        query = query.filter(Document.supplier_id == supplier_id)
    return query.order_by(Document.created_at.desc()).all()


def create_document_with_file(
    db: Session,
    category_id: uuid.UUID | str,
    file: UploadFile,
    case_id: uuid.UUID | str | None = None,
    supplier_id: uuid.UUID | str | None = None,
    bucket_name: str | None = None
) -> Document:
    """
    Создать новый документ с загрузкой файла в MinIO.
    
    Документ должен относиться либо к case_id, либо к supplier_id (ровно один).
    """
    # Валидация: ровно один из case_id или supplier_id должен быть указан
    if not case_id and not supplier_id:
        raise HTTPException(status_code=400, detail="Необходимо указать либо case_id, либо supplier_id")
    if case_id and supplier_id:
        raise HTTPException(status_code=400, detail="Нельзя указать одновременно case_id и supplier_id")
    
    # Преобразуем IDs в UUID
    if isinstance(category_id, str):
        category_id = uuid.UUID(category_id)
    case_uuid = None
    supplier_uuid = None
    
    if case_id:
        if isinstance(case_id, str):
            case_uuid = uuid.UUID(case_id)
        else:
            case_uuid = case_id
        # Проверяем, что кейс существует
        case = db.query(Case).filter(Case.id == case_uuid).first()
        if not case:
            raise HTTPException(status_code=404, detail=f"Кейс с ID '{case_uuid}' не найден")
        doc_type = "CASE"
        entity = case
        entity_code = case.code
    else:
        if isinstance(supplier_id, str):
            supplier_uuid = uuid.UUID(supplier_id)
        else:
            supplier_uuid = supplier_id
        # Проверяем, что поставщик существует
        from app.models.supplier import Supplier
        supplier = db.query(Supplier).filter(Supplier.id == supplier_uuid).first()
        if not supplier:
            raise HTTPException(status_code=404, detail=f"Поставщик с ID '{supplier_uuid}' не найден")
        doc_type = "SUPPLIER"
        entity = supplier
        entity_code = supplier.name.replace(" ", "_")[:50]  # Безопасное имя для пути
    
    # Проверяем, что категория существует и активна
    category = db.query(DocumentCategory).filter(
        DocumentCategory.id == category_id,
        DocumentCategory.is_active == True
    ).first()
    if not category:
        raise HTTPException(status_code=400, detail=f"Категория с ID '{category_id}' не найдена или неактивна")
    
    # Определяем bucket
    if not bucket_name:
        bucket_name = settings.minio_bucket_files
    
    # Создаем запись в БД со статусом IN_PROGRESS
    document = Document(
        case_id=case_uuid,
        supplier_id=supplier_uuid,
        category_id=category_id,
        doc_type=doc_type,
        original_filename=file.filename,
        content_type=file.content_type,
        storage_bucket=bucket_name,
        storage_key="",  # Временно пустой, заполним после загрузки
        status="IN_PROGRESS",
    )
    db.add(document)
    db.flush()  # Получаем ID документа
    
    try:
        # Убеждаемся что bucket существует
        ensure_bucket_exists(bucket_name)
        
        # Генерируем storage_key
        safe_filename = os.path.basename(file.filename)
        safe_filename = "".join(c if c.isalnum() or c in "._-" else "_" for c in safe_filename)
        if case_uuid:
            storage_key = f"cases/{entity_code}/{category.key}/{document.id.hex}_{safe_filename}"
        else:
            storage_key = f"suppliers/{supplier_uuid}/{document.id.hex}_{safe_filename}"
        
        # Читаем содержимое файла
        file_content = file.file.read()
        size_bytes = len(file_content)
        
        # Загружаем в MinIO
        content_type = file.content_type or "application/octet-stream"
        upload_file(bucket_name, storage_key, file_content, content_type)
        
        # Обновляем документ (storage_key и size_bytes, но НЕ ставим DONE)
        document.storage_key = storage_key
        document.size_bytes = size_bytes
        # Статус остается IN_PROGRESS - обработка будет в воркере
        db.commit()
        db.refresh(document)
        
        # Ставим задачу в очередь на обработку
        from app.services.queue import get_queue
        from app.jobs.documents import process_document
        queue = get_queue()
        queue.enqueue(process_document, document.id)
        
        # Подгружаем relationships
        if case_uuid:
            db.refresh(document, ["case", "category"])
        else:
            db.refresh(document, ["supplier", "category"])
        return document
    except Exception as e:
        # В случае ошибки сохраняем статус ERROR
        document.status = "ERROR"
        document.error_message = str(e)[:500]
        db.commit()
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки файла: {str(e)}")

