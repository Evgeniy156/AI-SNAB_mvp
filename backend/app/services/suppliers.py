"""Service слой для работы с поставщиками."""
from typing import List
from sqlalchemy.orm import Session
from app.models.supplier import Supplier


def list_suppliers(db: Session) -> List[Supplier]:
    """Получить список всех поставщиков, отсортированных по дате создания (новые первые)."""
    return db.query(Supplier).order_by(Supplier.created_at.desc()).all()


def create_supplier(db: Session, name: str, inn: str | None = None, kpp: str | None = None,
                    address_index: str | None = None, address: str | None = None) -> Supplier:
    """Создать нового поставщика."""
    supplier = Supplier(
        name=name,
        inn=inn,
        kpp=kpp,
        address_index=address_index,
        address=address,
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier

