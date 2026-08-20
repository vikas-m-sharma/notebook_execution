import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.notebook import Notebook


class NotebookRepository:
    """Repository handling persistence operations for Notebook entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        project_id: uuid.UUID,
        name: str,
        description: str | None = None,
        language: str = "python",
    ) -> Notebook:
        """Create and persist a new Notebook associated with a Project."""
        notebook = Notebook(
            project_id=project_id,
            name=name,
            description=description,
            language=language,
        )
        self.session.add(notebook)
        await self.session.flush()
        await self.session.refresh(notebook)
        return notebook

    async def get_by_id(
        self,
        notebook_id: uuid.UUID,
        include_cells: bool = False,
        include_metadata: bool = False,
    ) -> Notebook | None:
        """Retrieve a Notebook by its UUID, optionally eager loading cells and metadata."""
        stmt = select(Notebook).where(Notebook.id == notebook_id)
        if include_cells:
            stmt = stmt.options(selectinload(Notebook.cells))
        if include_metadata:
            stmt = stmt.options(selectinload(Notebook.metadata_rec))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_project(self, project_id: uuid.UUID) -> Sequence[Notebook]:
        """List all Notebooks belonging to a Project."""
        result = await self.session.execute(
            select(Notebook)
            .where(Notebook.project_id == project_id)
            .order_by(Notebook.name.asc())
        )
        return result.scalars().all()

    async def update(
        self,
        notebook_id: uuid.UUID,
        name: str | None = None,
        description: str | None = None,
        language: str | None = None,
    ) -> Notebook | None:
        """Update fields of an existing Notebook."""
        notebook = await self.get_by_id(notebook_id)
        if notebook is None:
            return None
        if name is not None:
            notebook.name = name
        if description is not None:
            notebook.description = description
        if language is not None:
            notebook.language = language
        await self.session.flush()
        await self.session.refresh(notebook)
        return notebook

    async def delete(self, notebook_id: uuid.UUID) -> bool:
        """Delete a Notebook by its UUID."""
        notebook = await self.get_by_id(notebook_id)
        if notebook is None:
            return False
        await self.session.delete(notebook)
        await self.session.flush()
        return True
