import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dependency import DependencyOperation, NotebookDependency


class NotebookDependencyRepository:
    """Async repository for managing NotebookDependency persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        notebook_id: uuid.UUID,
        package_name: str,
        version_specifier: Optional[str] = None,
    ) -> NotebookDependency:
        """Create a new notebook dependency record."""
        dep = NotebookDependency(
            notebook_id=notebook_id,
            package_name=package_name,
            version_specifier=version_specifier,
        )
        self.session.add(dep)
        await self.session.flush()
        await self.session.refresh(dep)
        return dep

    async def get_by_id(self, dep_id: uuid.UUID) -> Optional[NotebookDependency]:
        """Retrieve a dependency record by primary key UUID."""
        stmt = select(NotebookDependency).where(NotebookDependency.id == dep_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_notebook_and_package(
        self, notebook_id: uuid.UUID, package_name: str
    ) -> Optional[NotebookDependency]:
        """Retrieve a dependency record by notebook ID and package name."""
        stmt = select(NotebookDependency).where(
            NotebookDependency.notebook_id == notebook_id,
            NotebookDependency.package_name == package_name,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_by_notebook_id(self, notebook_id: uuid.UUID) -> Sequence[NotebookDependency]:
        """List all dependencies declared for a given notebook."""
        stmt = (
            select(NotebookDependency)
            .where(NotebookDependency.notebook_id == notebook_id)
            .order_by(NotebookDependency.package_name.asc())
        )
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def update(
        self, dep_id: uuid.UUID, version_specifier: Optional[str]
    ) -> Optional[NotebookDependency]:
        """Update version specifier for an existing dependency."""
        dep = await self.get_by_id(dep_id)
        if not dep:
            return None
        dep.version_specifier = version_specifier
        await self.session.flush()
        await self.session.refresh(dep)
        return dep

    async def delete(self, dep_id: uuid.UUID) -> bool:
        """Delete a dependency record by UUID."""
        dep = await self.get_by_id(dep_id)
        if not dep:
            return False
        await self.session.delete(dep)
        await self.session.flush()
        return True


class DependencyOperationRepository:
    """Async repository for managing DependencyOperation lifecycle persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        operation_id: str,
        notebook_id: uuid.UUID,
        packages: list[dict],
        session_id: Optional[str] = None,
        runtime_id: Optional[str] = None,
        status: str = "REQUESTED",
    ) -> DependencyOperation:
        """Create a new dependency installation operation record."""
        op_rec = DependencyOperation(
            operation_id=operation_id,
            notebook_id=notebook_id,
            session_id=session_id,
            runtime_id=runtime_id,
            status=status,
            packages=packages,
            started_at=datetime.now(timezone.utc),
        )
        self.session.add(op_rec)
        await self.session.flush()
        await self.session.refresh(op_rec)
        return op_rec

    async def get_by_operation_id(self, operation_id: str) -> Optional[DependencyOperation]:
        """Retrieve an operation record by operation string ID."""
        stmt = select(DependencyOperation).where(DependencyOperation.operation_id == operation_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_by_notebook_id(self, notebook_id: uuid.UUID) -> Sequence[DependencyOperation]:
        """List all dependency operations for a given notebook ordered by start time descending."""
        stmt = (
            select(DependencyOperation)
            .where(DependencyOperation.notebook_id == notebook_id)
            .order_by(DependencyOperation.started_at.desc())
        )
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def update_status(
        self,
        operation_id: str,
        status: str,
        resolved_versions: Optional[dict[str, str]] = None,
        error_message: Optional[str] = None,
        completed_at: Optional[datetime] = None,
    ) -> Optional[DependencyOperation]:
        """Update lifecycle status and resolution details of a dependency operation."""
        op_rec = await self.get_by_operation_id(operation_id)
        if not op_rec:
            return None
        op_rec.status = status
        if resolved_versions is not None:
            op_rec.resolved_versions = resolved_versions
        if error_message is not None:
            op_rec.error_message = error_message
        if completed_at is not None:
            op_rec.completed_at = completed_at
        elif status in ("READY", "FAILED", "CANCELLED"):
            op_rec.completed_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(op_rec)
        return op_rec
