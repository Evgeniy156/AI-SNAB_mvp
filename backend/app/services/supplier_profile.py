"""Сервисы для работы с профилем поставщика (карточка предприятия)."""
import uuid
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.supplier import Supplier
from app.models.supplier_profile import (
    SupplierProfile,
    OkvedCode,
    SupplierOkved,
    SupplierEquipment,
    SupplierCertificate
)


def get_or_create_supplier_profile(db: Session, supplier_id: uuid.UUID) -> SupplierProfile:
    """Получить или создать профиль поставщика."""
    profile = db.query(SupplierProfile).filter(
        SupplierProfile.supplier_id == supplier_id
    ).first()
    
    if not profile:
        profile = SupplierProfile(supplier_id=supplier_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    
    return profile


def update_supplier_profile(
    db: Session,
    supplier_id: uuid.UUID,
    **kwargs
) -> SupplierProfile:
    """Обновить профиль поставщика."""
    profile = get_or_create_supplier_profile(db, supplier_id)
    
    # Обновляем только переданные поля
    for key, value in kwargs.items():
        if hasattr(profile, key) and value is not None:
            setattr(profile, key, value)
    
    db.commit()
    db.refresh(profile)
    return profile


def set_supplier_okved(db: Session, supplier_id: uuid.UUID, codes: List[str]) -> List[OkvedCode]:
    """
    Установить коды ОКВЭД для поставщика.
    
    codes: список строк с кодами (например, ["25.11", "25.12"])
    """
    # Удаляем старые связи
    db.query(SupplierOkved).filter(
        SupplierOkved.supplier_id == supplier_id
    ).delete()
    
    # Создаем новые коды и связи
    result_codes = []
    for code_str in codes:
        code_str = code_str.strip()
        if not code_str:
            continue
        
        # Находим или создаем код ОКВЭД
        okved = db.query(OkvedCode).filter(OkvedCode.code == code_str).first()
        if not okved:
            okved = OkvedCode(code=code_str, name=None)
            db.add(okved)
            db.flush()
        
        # Создаем связь
        link = SupplierOkved(supplier_id=supplier_id, okved_id=okved.id)
        db.add(link)
        result_codes.append(okved)
    
    db.commit()
    return result_codes


def get_supplier_okved(db: Session, supplier_id: uuid.UUID) -> List[OkvedCode]:
    """Получить коды ОКВЭД поставщика."""
    links = db.query(SupplierOkved).filter(
        SupplierOkved.supplier_id == supplier_id
    ).all()
    
    return [link.okved_code for link in links]


def add_supplier_equipment(
    db: Session,
    supplier_id: uuid.UUID,
    name: str,
    model: str | None = None,
    qty: int | None = None,
    notes: str | None = None
) -> SupplierEquipment:
    """Добавить оборудование поставщику."""
    equipment = SupplierEquipment(
        supplier_id=supplier_id,
        name=name,
        model=model,
        qty=qty,
        notes=notes
    )
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    return equipment


def delete_supplier_equipment(db: Session, equipment_id: uuid.UUID, supplier_id: uuid.UUID) -> None:
    """Удалить оборудование поставщика."""
    equipment = db.query(SupplierEquipment).filter(
        SupplierEquipment.id == equipment_id,
        SupplierEquipment.supplier_id == supplier_id
    ).first()
    
    if not equipment:
        raise HTTPException(status_code=404, detail="Оборудование не найдено")
    
    db.delete(equipment)
    db.commit()


def add_supplier_certificate(
    db: Session,
    supplier_id: uuid.UUID,
    cert_type: str,
    number: str | None = None,
    issued_by: str | None = None,
    valid_from: str | None = None,
    valid_to: str | None = None,
    notes: str | None = None
) -> SupplierCertificate:
    """Добавить сертификат поставщику."""
    from datetime import datetime
    
    # Парсим даты если переданы строки
    valid_from_date = None
    valid_to_date = None
    if valid_from:
        try:
            valid_from_date = datetime.strptime(valid_from, "%Y-%m-%d").date()
        except ValueError:
            pass
    if valid_to:
        try:
            valid_to_date = datetime.strptime(valid_to, "%Y-%m-%d").date()
        except ValueError:
            pass
    
    certificate = SupplierCertificate(
        supplier_id=supplier_id,
        cert_type=cert_type,
        number=number,
        issued_by=issued_by,
        valid_from=valid_from_date,
        valid_to=valid_to_date,
        notes=notes
    )
    db.add(certificate)
    db.commit()
    db.refresh(certificate)
    return certificate


def delete_supplier_certificate(db: Session, certificate_id: uuid.UUID, supplier_id: uuid.UUID) -> None:
    """Удалить сертификат поставщика."""
    certificate = db.query(SupplierCertificate).filter(
        SupplierCertificate.id == certificate_id,
        SupplierCertificate.supplier_id == supplier_id
    ).first()
    
    if not certificate:
        raise HTTPException(status_code=404, detail="Сертификат не найден")
    
    db.delete(certificate)
    db.commit()


def get_supplier_context(db: Session, supplier_id: uuid.UUID) -> Dict[str, Any]:
    """
    Получить полный контекст поставщика для экспорта/генерации документов.
    
    Возвращает JSON-совместимый словарь со всеми данными поставщика.
    """
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail=f"Поставщик с ID '{supplier_id}' не найден")
    
    profile = db.query(SupplierProfile).filter(
        SupplierProfile.supplier_id == supplier_id
    ).first()
    
    okved_codes = get_supplier_okved(db, supplier_id)
    equipment = db.query(SupplierEquipment).filter(
        SupplierEquipment.supplier_id == supplier_id
    ).all()
    certificates = db.query(SupplierCertificate).filter(
        SupplierCertificate.supplier_id == supplier_id
    ).all()
    
    # Документы поставщика (только метаданные)
    from app.models.document import Document
    documents = db.query(Document).filter(
        Document.supplier_id == supplier_id
    ).all()
    
    context = {
        "supplier": {
            "id": str(supplier.id),
            "name": supplier.name,
            "inn": supplier.inn,
            "kpp": supplier.kpp,
            "address_index": supplier.address_index,
            "address": supplier.address,
            "created_at": supplier.created_at.isoformat() if supplier.created_at else None,
            "updated_at": supplier.updated_at.isoformat() if supplier.updated_at else None,
        },
        "profile": None,
        "okved_codes": [{"code": code.code, "name": code.name} for code in okved_codes],
        "equipment": [
            {
                "id": str(eq.id),
                "name": eq.name,
                "model": eq.model,
                "qty": eq.qty,
                "notes": eq.notes
            }
            for eq in equipment
        ],
        "certificates": [
            {
                "id": str(cert.id),
                "cert_type": cert.cert_type,
                "number": cert.number,
                "issued_by": cert.issued_by,
                "valid_from": cert.valid_from.isoformat() if cert.valid_from else None,
                "valid_to": cert.valid_to.isoformat() if cert.valid_to else None,
                "notes": cert.notes
            }
            for cert in certificates
        ],
        "flags": {
            "has_qms": profile.has_qms if profile else False,
            "works_with_goz": profile.works_with_goz if profile else False,
            "goz_secret_clearance": profile.goz_secret_clearance if profile else None,
        },
        "documents": [
            {
                "id": str(doc.id),
                "category_key": doc.category.key if doc.category else None,
                "original_filename": doc.original_filename,
                "status": doc.status,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
            }
            for doc in documents
        ]
    }
    
    if profile:
        context["profile"] = {
            "full_name": profile.full_name,
            "short_name": profile.short_name,
            "ogrn": profile.ogrn,
            "okpo": profile.okpo,
            "okato": profile.okato,
            "kpp": profile.kpp,
            "inn": profile.inn,
            "legal_address": profile.legal_address,
            "fact_address": profile.fact_address,
            "mail_address": profile.mail_address,
            "postal_code": profile.postal_code,
            "website": profile.website,
            "email": profile.email,
            "phone": profile.phone,
            "contact_person": profile.contact_person,
            "contact_position": profile.contact_position,
            "business_description": profile.business_description,
            "main_products_services": profile.main_products_services,
            "industries": profile.industries,
            "production_sites": profile.production_sites,
            "capacity_description": profile.capacity_description,
            "equipment_summary": profile.equipment_summary,
            "headcount_total": profile.headcount_total,
            "headcount_engineering": profile.headcount_engineering,
            "headcount_production": profile.headcount_production,
            "headcount_quality": profile.headcount_quality,
            "key_specialists": profile.key_specialists,
            "has_qms": profile.has_qms,
            "qms_standards": profile.qms_standards,
            "certifications_summary": profile.certifications_summary,
            "works_with_goz": profile.works_with_goz,
            "goz_experience": profile.goz_experience,
            "goz_secret_clearance": profile.goz_secret_clearance,
            "executed_contracts_count": profile.executed_contracts_count,
            "key_customers": profile.key_customers,
            "similar_deliveries": profile.similar_deliveries,
            "bank_name": profile.bank_name,
            "bank_bik": profile.bank_bik,
            "bank_account": profile.bank_account,
            "corr_account": profile.corr_account,
            "signatory_fio": profile.signatory_fio,
            "signatory_position": profile.signatory_position,
            "signatory_basis": profile.signatory_basis,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        }
    
    return context

