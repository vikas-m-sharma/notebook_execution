import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.notebook import Notebook


class NotebookDependency(Base):
    """NotebookDependency model storing declared package dependencies for a notebook."""

    __tablename__ = "notebook_dependencies"

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
    package_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    version_specifier: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
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
        back_populates="dependencies",
    )

    __table_args__ = (
        Index("ix_notebook_dependencies_nb_pkg", "notebook_id", "package_name", unique=True),
    )

    def __repr__(self) -> str:
        return (
            f"<NotebookDependency(id={self.id}, notebook_id={self.notebook_id}, "
            f"package='{self.package_name}', specifier='{self.version_specifier}')>"
        )


class DependencyOperation(Base):
    """DependencyOperation model tracking dependency installation operations and status lifecycle."""

    __tablename__ = "dependency_operations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    operation_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )
    notebook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notebooks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    runtime_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="REQUESTED",
        index=True,
    )
    packages: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=list,
    )
    resolved_versions: Mapped[Optional[dict[str, str]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    notebook: Mapped["Notebook"] = relationship(
        "Notebook",
        back_populates="dependency_operations",
    )

    def __repr__(self) -> str:
        return (
            f"<DependencyOperation(operation_id='{self.operation_id}', "
            f"notebook_id={self.notebook_id}, status='{self.status}')>"
        )
