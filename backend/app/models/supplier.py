import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Supplier(Base):
    """Модель поставщика."""
    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    inn: Mapped[str | None] = mapped_column(String(12), nullable=True)
    kpp: Mapped[str | None] = mapped_column(String(9), nullable=True)
    address_index: Mapped[str | None] = mapped_column(String(10), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    contacts: Mapped[list["SupplierContact"]] = relationship(
        "SupplierContact",
        back_populates="supplier",
        cascade="all, delete-orphan"
    )
    cases: Mapped[list["Case"]] = relationship(
        "Case",
        foreign_keys="Case.supplier_id",
        back_populates="supplier",
        primaryjoin="Supplier.id == Case.supplier_id"
    )
    profile: Mapped["SupplierProfile | None"] = relationship(
        "SupplierProfile",
        back_populates="supplier",
        uselist=False,
        cascade="all, delete-orphan"
    )
    okved_codes: Mapped[list["SupplierOkved"]] = relationship(
        "SupplierOkved",
        back_populates="supplier",
        cascade="all, delete-orphan"
    )
    equipment: Mapped[list["SupplierEquipment"]] = relationship(
        "SupplierEquipment",
        back_populates="supplier",
        cascade="all, delete-orphan"
    )
    certificates: Mapped[list["SupplierCertificate"]] = relationship(
        "SupplierCertificate",
        back_populates="supplier",
        cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="supplier"
    )

    def __repr__(self) -> str:
        return f"<Supplier(id={self.id}, name={self.name!r})>"


class SupplierContact(Base):
    """Модель контакта поставщика."""
    __tablename__ = "supplier_contacts"

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
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    supplier: Mapped["Supplier"] = relationship(
        "Supplier",
        back_populates="contacts"
    )

    def __repr__(self) -> str:
        return f"<SupplierContact(id={self.id}, full_name={self.full_name!r}, supplier_id={self.supplier_id})>"

