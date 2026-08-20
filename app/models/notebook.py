import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.dependency import DependencyOperation, NotebookDependency
    from app.models.notebook_cell import NotebookCell
    from app.models.notebook_metadata import NotebookMetadata
    from app.models.output import ExecutionOutput
    from app.models.project import Project


class Notebook(Base):
    """Notebook model representing an analytical notebook within a project."""

    __tablename__ = "notebooks"

    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_notebook_project_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    language: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="python",
        server_default="python",
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
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="notebooks",
    )
    cells: Mapped[list["NotebookCell"]] = relationship(
        "NotebookCell",
        back_populates="notebook",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="NotebookCell.position",
    )
    metadata_rec: Mapped[Optional["NotebookMetadata"]] = relationship(
        "NotebookMetadata",
        back_populates="notebook",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    execution_outputs: Mapped[list["ExecutionOutput"]] = relationship(
        "ExecutionOutput",
        back_populates="notebook",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    dependencies: Mapped[list["NotebookDependency"]] = relationship(
        "NotebookDependency",
        back_populates="notebook",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    dependency_operations: Mapped[list["DependencyOperation"]] = relationship(
        "DependencyOperation",
        back_populates="notebook",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Notebook(id={self.id}, name='{self.name}', language='{self.language}')>"
