import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class ChecklistTemplate(Base):
    """Шаблон чек-листа закупочной процедуры."""
    __tablename__ = "checklist_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    items: Mapped[list["ChecklistTemplateItem"]] = relationship(
        "ChecklistTemplateItem",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="ChecklistTemplateItem.sort_order"
    )

    def __repr__(self) -> str:
        return f"<ChecklistTemplate(id={self.id}, key={self.key!r}, name={self.name!r})>"


class ChecklistTemplateItem(Base):
    """Пункт шаблона чек-листа."""
    __tablename__ = "checklist_template_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("checklist_templates.id", ondelete="CASCADE"),
        nullable=False
    )
    section: Mapped[str] = mapped_column(String(200), nullable=False)
    group_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(nullable=False)
    hint: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Relationships
    template: Mapped["ChecklistTemplate"] = relationship(
        "ChecklistTemplate",
        back_populates="items"
    )
    case_items: Mapped[list["CaseChecklistItem"]] = relationship(
        "CaseChecklistItem",
        back_populates="template_item"
    )

    def __repr__(self) -> str:
        t = (self.title or "")[:50]
        return f"<ChecklistTemplateItem(id={self.id}, title={t!r})>"

