"""API роутер для документов."""
from typing import List
import uuid
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.document import DocumentOut
from app.schemas.document_generate import (
    DocumentGenerateRequest,
    DocumentGenerateResponse
)
from app.services.documents import list_documents, create_document_with_file
from app.services.agent_tools import generate_doc

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=List[DocumentOut])
def get_documents(
    case_id: uuid.UUID | None = Query(None, description="Фильтр по кейсу"),
    db: Session = Depends(get_db)
):
    """Получить список документов."""
    documents = list_documents(db, case_id=case_id)
    # Преобразуем в DocumentOut
    result = []
    for doc in documents:
        result.append(DocumentOut(
            id=doc.id,
            case_id=doc.case_id,
            case_code=doc.case.code if doc.case else None,
            category_id=doc.category_id,
            category_key=doc.category.key if doc.category else None,
            category_name=doc.category.name if doc.category else None,
            original_filename=doc.original_filename,
            storage_bucket=doc.storage_bucket,
            storage_key=doc.storage_key,
            status=doc.status,
            created_at=doc.created_at,
        ))
    return result


@router.post("/upload", response_model=DocumentOut, status_code=201)
def upload_document(
    case_id: str = Form(...),
    category_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Загрузить документ в MinIO и создать запись в БД."""
    document = create_document_with_file(
        db=db,
        case_id=case_id,
        category_id=category_id,
        file=file,
    )
    return DocumentOut(
        id=document.id,
        case_id=document.case_id,
        case_code=document.case.code if document.case else None,
        category_id=document.category_id,
        category_key=document.category.key if document.category else None,
        category_name=document.category.name if document.category else None,
        original_filename=document.original_filename,
        storage_bucket=document.storage_bucket,
        storage_key=document.storage_key,
        status=document.status,
        created_at=document.created_at,
    )


@router.post("/generate", response_model=DocumentGenerateResponse, status_code=201)
def generate_document_endpoint(
    request: DocumentGenerateRequest,
    db: Session = Depends(get_db)
):
    """Сгенерировать документ по шаблону."""
    result = generate_doc(db, request.case_id, request.template_key)
    
    if not result["ok"]:
        raise HTTPException(
            status_code=400,
            detail=result.get("reason", "Ошибка генерации документа")
        )
    
    return DocumentGenerateResponse(
        document_id=result["document_id"],
        status="DONE"
    )


@router.get("/{document_id}/download-url", response_class=JSONResponse)
def get_document_download_url(
    document_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Получить presigned URL для скачивания документа."""
    from app.models.document import Document
    from app.services.storage import presigned_get_url
    
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")
    
    if document.status != "DONE":
        raise HTTPException(
            status_code=400,
            detail=f"Документ не готов к скачиванию (статус: {document.status})"
        )
    
    try:
        url = presigned_get_url(document.storage_bucket, document.storage_key, expires=3600)
        return {"url": url, "filename": document.original_filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации ссылки: {str(e)}")
