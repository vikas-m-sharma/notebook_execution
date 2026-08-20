import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notebook_cell import NotebookCell


class NotebookCellRepository:
    """Repository handling persistence operations for NotebookCell entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        notebook_id: uuid.UUID,
        position: int,
        source: str = "",
        cell_type: str = "code",
    ) -> NotebookCell:
        """Create and persist a new NotebookCell in a notebook."""
        cell = NotebookCell(
            notebook_id=notebook_id,
            position=position,
            source=source,
            cell_type=cell_type,
        )
        self.session.add(cell)
        await self.session.flush()
        await self.session.refresh(cell)
        return cell

    async def get_by_id(self, cell_id: uuid.UUID) -> NotebookCell | None:
        """Retrieve a NotebookCell by its UUID."""
        result = await self.session.execute(
            select(NotebookCell).where(NotebookCell.id == cell_id)
        )
        return result.scalar_one_or_none()

    async def list_by_notebook(self, notebook_id: uuid.UUID) -> Sequence[NotebookCell]:
        """List all NotebookCells belonging to a notebook, deterministically ordered by position."""
        result = await self.session.execute(
            select(NotebookCell)
            .where(NotebookCell.notebook_id == notebook_id)
            .order_by(NotebookCell.position.asc())
        )
        return result.scalars().all()

    async def update(
        self,
        cell_id: uuid.UUID,
        source: str | None = None,
        cell_type: str | None = None,
        position: int | None = None,
    ) -> NotebookCell | None:
        """Update fields of an existing NotebookCell."""
        cell = await self.get_by_id(cell_id)
        if cell is None:
            return None
        if source is not None:
            cell.source = source
        if cell_type is not None:
            cell.cell_type = cell_type
        if position is not None:
            cell.position = position
        await self.session.flush()
        await self.session.refresh(cell)
        return cell

    async def delete(self, cell_id: uuid.UUID) -> bool:
        """Delete a NotebookCell by its UUID."""
        cell = await self.get_by_id(cell_id)
        if cell is None:
            return False
        await self.session.delete(cell)
        await self.session.flush()
        return True

    async def reorder_cells(
        self,
        notebook_id: uuid.UUID,
        cell_positions: dict[uuid.UUID, int],
    ) -> Sequence[NotebookCell]:
        """Bulk update positions of cells in a notebook."""
        cells = await self.list_by_notebook(notebook_id)
        for cell in cells:
            if cell.id in cell_positions:
                cell.position = cell_positions[cell.id]
        await self.session.flush()
        return await self.list_by_notebook(notebook_id)
