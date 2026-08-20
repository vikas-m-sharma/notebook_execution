import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.notebook_cell import (
    NotebookCellCreate,
    NotebookCellListResponse,
    NotebookCellResponse,
    NotebookCellUpdate,
)
from app.services.notebook_cell import NotebookCellService

router = APIRouter()


@router.post(
    "/notebooks/{notebook_id}/cells",
    response_model=NotebookCellResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Cell",
    description="Create a new cell in a notebook.",
)
async def create_cell(
    notebook_id: uuid.UUID,
    data: NotebookCellCreate,
    db: AsyncSession = Depends(get_db),
) -> NotebookCellResponse:
    service = NotebookCellService(db)
    cell = await service.create_cell(notebook_id, data)
    return NotebookCellResponse.model_validate(cell)


@router.get(
    "/notebooks/{notebook_id}/cells",
    response_model=NotebookCellListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Cells in Notebook",
    description="List all cells in a notebook ordered by position.",
)
async def list_cells_in_notebook(
    notebook_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> NotebookCellListResponse:
    service = NotebookCellService(db)
    cells = await service.list_cells_by_notebook(notebook_id)
    items = [NotebookCellResponse.model_validate(c) for c in cells]
    return NotebookCellListResponse(items=items, total=len(items))


@router.get(
    "/notebooks/{notebook_id}/cells/{cell_id}",
    response_model=NotebookCellResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Cell",
    description="Get details of a specific cell in a notebook by UUID.",
)
async def get_cell(
    notebook_id: uuid.UUID,
    cell_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> NotebookCellResponse:
    service = NotebookCellService(db)
    cell = await service.get_cell(notebook_id, cell_id)
    return NotebookCellResponse.model_validate(cell)


@router.patch(
    "/notebooks/{notebook_id}/cells/{cell_id}",
    response_model=NotebookCellResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Cell",
    description="Partially update a cell in a notebook by UUID.",
)
async def update_cell(
    notebook_id: uuid.UUID,
    cell_id: uuid.UUID,
    data: NotebookCellUpdate,
    db: AsyncSession = Depends(get_db),
) -> NotebookCellResponse:
    service = NotebookCellService(db)
    cell = await service.update_cell(notebook_id, cell_id, data)
    return NotebookCellResponse.model_validate(cell)


@router.delete(
    "/notebooks/{notebook_id}/cells/{cell_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Cell",
    description="Delete a specific cell from a notebook.",
)
async def delete_cell(
    notebook_id: uuid.UUID,
    cell_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    service = NotebookCellService(db)
    await service.delete_cell(notebook_id, cell_id)
