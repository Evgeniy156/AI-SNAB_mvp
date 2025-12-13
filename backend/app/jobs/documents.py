"""Jobs для обработки документов."""
import uuid
import time
from app.db.session import SessionLocal
from app.models.document import Document


def process_document(document_id: uuid.UUID | str) -> None:
    """
    Обработать документ: имитировать обработку и установить статус DONE.
    
    Args:
        document_id: UUID документа для обработки
    """
    # Преобразуем в UUID если строка
    if isinstance(document_id, str):
        document_id = uuid.UUID(document_id)
    
    db = SessionLocal()
    try:
        # Находим документ
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            # Документ не найден - просто выходим
            return
        
        # Устанавливаем статус IN_PROGRESS (на всякий случай)
        document.status = "IN_PROGRESS"
        db.commit()
        
        # Имитируем обработку (например, OCR, извлечение полей и т.д.)
        time.sleep(1)
        
        # Устанавливаем статус DONE
        document.status = "DONE"
        document.error_message = None
        db.commit()
        
    except Exception as e:
        # В случае ошибки устанавливаем статус ERROR
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.status = "ERROR"
                document.error_message = str(e)[:500]
                db.commit()
        except Exception:
            # Если не удалось обновить - просто логируем (в production можно использовать logger)
            pass
        raise
    finally:
        db.close()

