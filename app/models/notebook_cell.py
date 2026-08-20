import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.notebook import Notebook


class NotebookCell(Base):
    """NotebookCell model representing an individual code or markdown cell in a notebook."""

    __tablename__ = "notebook_cells"

    __table_args__ = (
        UniqueConstraint("notebook_id", "position", name="uq_notebook_cell_position"),
        Index("idx_cell_notebook_position", "notebook_id", "position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    notebook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notebooks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    cell_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="code",
    )
    source: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    notebook: Mapped["Notebook"] = relationship(
        "Notebook",
        back_populates="cells",
    )

    def __repr__(self) -> str:
        return f"<NotebookCell(id={self.id}, notebook_id={self.notebook_id}, position={self.position}, type='{self.cell_type}')>"
