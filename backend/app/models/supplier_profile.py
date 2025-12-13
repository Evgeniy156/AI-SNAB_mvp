import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, Text, Boolean, Integer, Date, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.supplier import Supplier


class SupplierProfile(Base):
    """Профиль поставщика (карточка предприятия) - 1:1 с Supplier."""
    __tablename__ = "supplier_profiles"
    __table_args__ = (
        UniqueConstraint('supplier_id', name='uq_supplier_profile_supplier_id'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    # Юридические данные
    full_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    ogrn: Mapped[str | None] = mapped_column(String(20), nullable=True)
    okpo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    okato: Mapped[str | None] = mapped_column(String(20), nullable=True)
    kpp: Mapped[str | None] = mapped_column(String(9), nullable=True)
    inn: Mapped[str | None] = mapped_column(String(12), nullable=True)
    legal_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    fact_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    mail_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Контакты
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    contact_person: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_position: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Деятельность
    business_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    main_products_services: Mapped[str | None] = mapped_column(Text, nullable=True)
    industries: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Производство / мощности
    production_sites: Mapped[str | None] = mapped_column(Text, nullable=True)
    capacity_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    equipment_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Персонал
    headcount_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    headcount_engineering: Mapped[int | None] = mapped_column(Integer, nullable=True)
    headcount_production: Mapped[int | None] = mapped_column(Integer, nullable=True)
    headcount_quality: Mapped[int | None] = mapped_column(Integer, nullable=True)
    key_specialists: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Качество / СМК
    has_qms: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    qms_standards: Mapped[str | None] = mapped_column(String(255), nullable=True)
    certifications_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ГОЗ
    works_with_goz: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    goz_experience: Mapped[str | None] = mapped_column(Text, nullable=True)
    goz_secret_clearance: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Опыт поставок
    executed_contracts_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    key_customers: Mapped[str | None] = mapped_column(Text, nullable=True)
    similar_deliveries: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Финансы / банки
    bank_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bank_bik: Mapped[str | None] = mapped_column(String(20), nullable=True)
    bank_account: Mapped[str | None] = mapped_column(String(50), nullable=True)
    corr_account: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Подписант
    signatory_fio: Mapped[str | None] = mapped_column(String(255), nullable=True)
    signatory_position: Mapped[str | None] = mapped_column(String(255), nullable=True)
    signatory_basis: Mapped[str | None] = mapped_column(String(255), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    supplier: Mapped["Supplier"] = relationship(
        "Supplier",
        back_populates="profile"
    )

    def __repr__(self) -> str:
        return f"<SupplierProfile(supplier_id={self.supplier_id})>"


class OkvedCode(Base):
    """Справочник кодов ОКВЭД."""
    __tablename__ = "okved_codes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    suppliers: Mapped[list["SupplierOkved"]] = relationship(
        "SupplierOkved",
        back_populates="okved_code"
    )

    def __repr__(self) -> str:
        return f"<OkvedCode(id={self.id}, code={self.code!r})>"


class SupplierOkved(Base):
    """Связь поставщика с кодами ОКВЭД (M:N)."""
    __tablename__ = "supplier_okved"
    __table_args__ = (
        UniqueConstraint('supplier_id', 'okved_id', name='uq_supplier_okved'),
    )

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False
    )
    okved_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("okved_codes.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False
    )

    # Relationships
    supplier: Mapped["Supplier"] = relationship(
        "Supplier",
        back_populates="okved_codes"
    )
    okved_code: Mapped["OkvedCode"] = relationship(
        "OkvedCode",
        back_populates="suppliers"
    )

    def __repr__(self) -> str:
        return f"<SupplierOkved(supplier_id={self.supplier_id}, okved_id={self.okved_id})>"


class SupplierEquipment(Base):
    """Оборудование поставщика."""
    __tablename__ = "supplier_equipment"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    supplier: Mapped["Supplier"] = relationship(
        "Supplier",
        back_populates="equipment"
    )

    def __repr__(self) -> str:
        return f"<SupplierEquipment(id={self.id}, name={self.name!r}, supplier_id={self.supplier_id})>"


class SupplierCertificate(Base):
    """Сертификаты и СМК поставщика."""
    __tablename__ = "supplier_certificates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False
    )
    cert_type: Mapped[str] = mapped_column(String(100), nullable=False)  # ISO9001, ГОСТ РВ, СТО, лицензия
    number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    issued_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    valid_from: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    supplier: Mapped["Supplier"] = relationship(
        "Supplier",
        back_populates="certificates"
    )

    def __repr__(self) -> str:
        return f"<SupplierCertificate(id={self.id}, cert_type={self.cert_type!r}, supplier_id={self.supplier_id})>"

