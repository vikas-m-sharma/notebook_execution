import uuid
from typing import Sequence

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notebook_cell import NotebookCell
from app.repositories.notebook import NotebookRepository
from app.repositories.notebook_cell import NotebookCellRepository
from app.schemas.notebook_cell import NotebookCellCreate, NotebookCellUpdate

SUPPORTED_CELL_TYPES = {"code", "markdown"}


class NotebookCellService:
    """Service encapsulating business logic for NotebookCell operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.notebook_repository = NotebookRepository(session)
        self.cell_repository = NotebookCellRepository(session)

    def _validate_cell_type(self, cell_type: str) -> str:
        """Validate supported notebook cell type."""
        cell_type_normalized = cell_type.lower()
        if cell_type_normalized not in SUPPORTED_CELL_TYPES:
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported cell type '{cell_type}'. Supported cell types: {sorted(list(SUPPORTED_CELL_TYPES))}.",
            )
        return cell_type_normalized

    async def create_cell(
        self, notebook_id: uuid.UUID, data: NotebookCellCreate
    ) -> NotebookCell:
        """Create a new NotebookCell in a Notebook, verifying Notebook existence and position uniqueness."""
        notebook = await self.notebook_repository.get_by_id(notebook_id)
        if notebook is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Notebook '{notebook_id}' not found.",
            )

        cell_type = self._validate_cell_type(data.cell_type)

        existing_cells = await self.cell_repository.list_by_notebook(notebook_id)
        if any(c.position == data.position for c in existing_cells):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cell at position {data.position} already exists in notebook '{notebook_id}'.",
            )

        try:
            return await self.cell_repository.create(
                notebook_id=notebook_id,
                position=data.position,
                source=data.source,
                cell_type=cell_type,
            )
        except IntegrityError as exc:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cell at position {data.position} already exists in notebook '{notebook_id}'.",
            ) from exc

    async def get_cell(
        self, notebook_id: uuid.UUID, cell_id: uuid.UUID
    ) -> NotebookCell:
        """Retrieve a specific NotebookCell belonging to a Notebook or raise HTTP 404."""
        notebook = await self.notebook_repository.get_by_id(notebook_id)
        if notebook is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Notebook '{notebook_id}' not found.",
            )
        cell = await self.cell_repository.get_by_id(cell_id)
        if cell is None or cell.notebook_id != notebook_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cell '{cell_id}' not found in notebook '{notebook_id}'.",
            )
        return cell

    async def list_cells_by_notebook(
        self, notebook_id: uuid.UUID
    ) -> Sequence[NotebookCell]:
        """List all NotebookCells in a Notebook ordered by position, verifying Notebook existence."""
        notebook = await self.notebook_repository.get_by_id(notebook_id)
        if notebook is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Notebook '{notebook_id}' not found.",
            )
        return await self.cell_repository.list_by_notebook(notebook_id)

    async def update_cell(
        self,
        notebook_id: uuid.UUID,
        cell_id: uuid.UUID,
        data: NotebookCellUpdate,
    ) -> NotebookCell:
        """Update an existing NotebookCell or raise HTTP 404/409/422."""
        await self.get_cell(notebook_id, cell_id)
        cell_type = (
            self._validate_cell_type(data.cell_type)
            if data.cell_type is not None
            else None
        )

        if data.position is not None:
            existing_cells = await self.cell_repository.list_by_notebook(notebook_id)
            if any(c.position == data.position and c.id != cell_id for c in existing_cells):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Position {data.position} conflicts with an existing cell in notebook '{notebook_id}'.",
                )

        try:
            updated = await self.cell_repository.update(
                cell_id=cell_id,
                source=data.source,
                cell_type=cell_type,
                position=data.position,
            )
            if updated is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Cell '{cell_id}' not found.",
                )
            return updated
        except IntegrityError as exc:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Position {data.position} conflicts with an existing cell in notebook '{notebook_id}'.",
            ) from exc

    async def delete_cell(
        self, notebook_id: uuid.UUID, cell_id: uuid.UUID
    ) -> None:
        """Delete a NotebookCell by ID or raise HTTP 404."""
        await self.get_cell(notebook_id, cell_id)
        deleted = await self.cell_repository.delete(cell_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cell '{cell_id}' not found.",
            )
