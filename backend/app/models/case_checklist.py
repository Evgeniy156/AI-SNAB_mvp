import uuid
from datetime import datetime, date
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, Text, Date, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.case import Case
    from app.models.document import Document
    from app.models.checklist_template import ChecklistTemplateItem


class CaseChecklistItem(Base):
    """Экземпляр пункта чек-листа для конкретного кейса."""
    __tablename__ = "case_checklist_items"
    __table_args__ = (
        UniqueConstraint('case_id', 'template_item_id', name='uq_case_checklist_item'),
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
    template_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("checklist_template_items.id", ondelete="CASCADE"),
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="TODO",
        nullable=False
    )  # TODO, DONE, NA
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    doc_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    doc_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    case: Mapped["Case"] = relationship(
        "Case",
        back_populates="checklist_items"
    )
    template_item: Mapped["ChecklistTemplateItem"] = relationship(
        "ChecklistTemplateItem",
        back_populates="case_items"
    )
    documents: Mapped[list["CaseChecklistItemDocument"]] = relationship(
        "CaseChecklistItemDocument",
        back_populates="checklist_item",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CaseChecklistItem(id={self.id}, case_id={self.case_id}, status={self.status!r})>"


class CaseChecklistItemDocument(Base):
    """Связь между пунктом чек-листа и документом кейса."""
    __tablename__ = "case_checklist_item_documents"
    __table_args__ = (
        UniqueConstraint('case_checklist_item_id', 'document_id', name='uq_checklist_item_document'),
    )

    case_checklist_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("case_checklist_items.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False
    )

    # Relationships
    checklist_item: Mapped["CaseChecklistItem"] = relationship(
        "CaseChecklistItem",
        back_populates="documents"
    )
    document: Mapped["Document"] = relationship(
        "Document"
    )

    def __repr__(self) -> str:
        return f"<CaseChecklistItemDocument(item_id={self.case_checklist_item_id}, doc_id={self.document_id})>"

