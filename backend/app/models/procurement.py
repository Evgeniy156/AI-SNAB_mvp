import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, Text, Boolean, Integer, Date, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.case import Case
    from app.models.supplier import Supplier
    from app.models.document import Document


class CaseCandidate(Base):
    """Кандидат (организация/поставщик) в закупке."""
    __tablename__ = "case_candidates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False
    )
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        nullable=True
    )
    org_name: Mapped[str] = mapped_column(String(255), nullable=False)
    inn: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        default="NEW",
        nullable=False
    )  # NEW, RFQ_SENT, OFFER_RECEIVED, REFUSED, NO_RESPONSE
    rank_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    rank_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    case: Mapped["Case"] = relationship(
        "Case",
        back_populates="candidates"
    )
    supplier: Mapped["Supplier | None"] = relationship(
        "Supplier"
    )
    rfq_requests: Mapped[list["RfqRequest"]] = relationship(
        "RfqRequest",
        back_populates="candidate",
        cascade="all, delete-orphan"
    )
    commercial_offers: Mapped[list["CommercialOffer"]] = relationship(
        "CommercialOffer",
        back_populates="candidate",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CaseCandidate(id={self.id}, org_name={self.org_name!r}, case_id={self.case_id})>"


class RfqRequest(Base):
    """Запрос коммерческого предложения (RFQ)."""
    __tablename__ = "rfq_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("case_candidates.id", ondelete="CASCADE"),
        nullable=False
    )
    channel: Mapped[str] = mapped_column(String(50), nullable=False)  # EMAIL, PHONE, PORTAL, OTHER
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=datetime.utcnow,
        nullable=False
    )
    result: Mapped[str] = mapped_column(
        String(50),
        default="SENT",
        nullable=False
    )  # SENT, RECEIVED_OFFER, REFUSAL, NO_RESPONSE
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    case: Mapped["Case"] = relationship(
        "Case",
        back_populates="rfq_requests"
    )
    candidate: Mapped["CaseCandidate"] = relationship(
        "CaseCandidate",
        back_populates="rfq_requests"
    )
    evidence_document: Mapped["Document | None"] = relationship(
        "Document",
        foreign_keys=[evidence_document_id]
    )

    def __repr__(self) -> str:
        return f"<RfqRequest(id={self.id}, candidate_id={self.candidate_id}, channel={self.channel!r})>"


class CommercialOffer(Base):
    """Коммерческое предложение (КП)."""
    __tablename__ = "commercial_offers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("case_candidates.id", ondelete="CASCADE"),
        nullable=False
    )
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        nullable=True
    )  # Денормализация для удобства
    price_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="RUB", nullable=False)
    vat_included: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delivery_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    case: Mapped["Case"] = relationship(
        "Case",
        back_populates="commercial_offers"
    )
    candidate: Mapped["CaseCandidate"] = relationship(
        "CaseCandidate",
        back_populates="commercial_offers"
    )
    supplier: Mapped["Supplier | None"] = relationship(
        "Supplier"
    )
    document: Mapped["Document | None"] = relationship(
        "Document",
        foreign_keys=[document_id]
    )

    def __repr__(self) -> str:
        return f"<CommercialOffer(id={self.id}, price_total={self.price_total}, case_id={self.case_id})>"


class SupplierSecurityReview(Base):
    """Проверка службы безопасности (СБ) поставщика для закупки."""
    __tablename__ = "supplier_security_reviews"
    __table_args__ = (
        UniqueConstraint('case_id', 'supplier_id', name='uq_case_supplier_security_review'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="NOT_STARTED",
        nullable=False
    )  # NOT_STARTED, IN_PROGRESS, APPROVED, REJECTED
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    case: Mapped["Case"] = relationship(
        "Case",
        back_populates="security_reviews"
    )
    supplier: Mapped["Supplier"] = relationship(
        "Supplier"
    )
    document: Mapped["Document | None"] = relationship(
        "Document",
        foreign_keys=[document_id]
    )

    def __repr__(self) -> str:
        return f"<SupplierSecurityReview(id={self.id}, case_id={self.case_id}, supplier_id={self.supplier_id}, status={self.status!r})>"

