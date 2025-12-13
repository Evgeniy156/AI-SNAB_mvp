"""API роутер для поставщиков."""
from typing import List, Dict, Any
import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.supplier import SupplierCreate, SupplierOut
from app.services.suppliers import list_suppliers, create_supplier
from app.services.supplier_profile import get_supplier_context

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.get("", response_model=List[SupplierOut])
def get_suppliers(db: Session = Depends(get_db)):
    """Получить список всех поставщиков."""
    return list_suppliers(db)


@router.post("", response_model=SupplierOut, status_code=201)
def create_supplier_endpoint(
    supplier_data: SupplierCreate,
    db: Session = Depends(get_db)
):
    """Создать нового поставщика."""
    supplier = create_supplier(
        db=db,
        name=supplier_data.name,
        inn=supplier_data.inn,
        kpp=supplier_data.kpp,
        address_index=supplier_data.address_index,
        address=supplier_data.address,
    )
    return supplier


@router.get("/{supplier_id}/context", response_class=JSONResponse)
def get_supplier_context_endpoint(
    supplier_id: uuid.UUID,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Получить полный контекст поставщика для экспорта/генерации документов."""
    return get_supplier_context(db, supplier_id)

