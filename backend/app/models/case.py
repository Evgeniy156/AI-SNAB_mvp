import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, DateTime, ForeignKey, Text, Boolean, Integer, Date, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Case(Base):
    """Модель кейса закупки."""
    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        default="DRAFT",
        nullable=False
    )
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        nullable=True
    )
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
    epoz_clause: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Поля закупки
    procurement_type: Mapped[str] = mapped_column(
        String(50),
        default="GOODS_SUPPLY",
        nullable=False
    )  # MANUFACTURE_AND_SUPPLY, GOODS_SUPPLY, SERVICES, WORKS, OTHER
    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    initiator_department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    planned_deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    procedure_stage: Mapped[str] = mapped_column(
        String(50),
        default="DRAFT",
        nullable=False
    )  # DRAFT, RFQ_SENT, OFFERS_COLLECTED, SB_REVIEW, SUPPLIER_SELECTED, PROCEDURE, DONE
    
    # Расчётные поля
    nmc_avg_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    validation_coeff: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    offers_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_validation_ok: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Выбор победителя
    selected_supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        nullable=True
    )
    selection_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Поля активации
    is_activated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    
    # Шаблон чек-листа
    checklist_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("checklist_templates.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    supplier: Mapped["Supplier | None"] = relationship(
        "Supplier",
        foreign_keys=[supplier_id],
        back_populates="cases"
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="case",
        cascade="all, delete-orphan"
    )
    checklist_items: Mapped[list["CaseChecklistItem"]] = relationship(
        "CaseChecklistItem",
        back_populates="case",
        cascade="all, delete-orphan"
    )
    candidates: Mapped[list["CaseCandidate"]] = relationship(
        "CaseCandidate",
        back_populates="case",
        cascade="all, delete-orphan"
    )
    rfq_requests: Mapped[list["RfqRequest"]] = relationship(
        "RfqRequest",
        back_populates="case",
        cascade="all, delete-orphan"
    )
    commercial_offers: Mapped[list["CommercialOffer"]] = relationship(
        "CommercialOffer",
        back_populates="case",
        cascade="all, delete-orphan"
    )
    security_reviews: Mapped[list["SupplierSecurityReview"]] = relationship(
        "SupplierSecurityReview",
        back_populates="case",
        cascade="all, delete-orphan"
    )
    checklist_template: Mapped["ChecklistTemplate | None"] = relationship(
        "ChecklistTemplate",
        foreign_keys=[checklist_template_id]
    )

    def __repr__(self) -> str:
        return f"<Case(id={self.id}, code={self.code!r}, title={self.title!r})>"

