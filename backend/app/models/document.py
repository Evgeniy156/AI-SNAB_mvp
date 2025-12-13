import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.case import Case
    from app.models.document_category import DocumentCategory
    from app.models.supplier import Supplier


class Document(Base):
    """Модель документа (кейса или поставщика)."""
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=True
    )
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=True
    )
    doc_type: Mapped[str] = mapped_column(String(50), default="CASE", nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_categories.id", ondelete="RESTRICT"),
        nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(nullable=True)
    storage_bucket: Mapped[str] = mapped_column(String(100), default="aisnab-files", nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        default="IN_PROGRESS",
        nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    extracted_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    case: Mapped["Case"] = relationship(
        "Case",
        back_populates="documents"
    )
    category: Mapped["DocumentCategory | None"] = relationship(
        "DocumentCategory",
        back_populates="documents"
    )
    supplier: Mapped["Supplier | None"] = relationship(
        "Supplier",
        back_populates="documents"
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, original_filename={self.original_filename!r}, case_id={self.case_id})>"

