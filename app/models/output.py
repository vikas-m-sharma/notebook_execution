import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.notebook import Notebook


class ExecutionOutput(Base):
    """ExecutionOutput ORM model storing sequence-ordered output records for cell executions."""

    __tablename__ = "execution_outputs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    execution_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    session_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    notebook_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notebooks.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    cell_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    output_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    sequence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    output_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    notebook: Mapped[Optional["Notebook"]] = relationship(
        "Notebook",
        back_populates="execution_outputs",
    )

    __table_args__ = (
        Index("ix_execution_outputs_exec_seq", "execution_id", "sequence"),
        Index("ix_execution_outputs_cell_seq", "cell_id", "sequence"),
    )

    def __repr__(self) -> str:
        return (
            f"<ExecutionOutput(id={self.id}, execution_id='{self.execution_id}', "
            f"type='{self.output_type}', sequence={self.sequence})>"
        )
