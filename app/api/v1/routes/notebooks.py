import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.notebook import (
    NotebookCreate,
    NotebookDetailResponse,
    NotebookListResponse,
    NotebookResponse,
    NotebookUpdate,
)
from app.schemas.notebook_cell import NotebookCellResponse
from app.schemas.notebook_metadata import NotebookMetadataResponse
from app.services.notebook import NotebookService

router = APIRouter()


@router.post(
    "/projects/{project_id}/notebooks",
    response_model=NotebookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Notebook",
    description="Create a new notebook within a project.",
)
async def create_notebook(
    project_id: uuid.UUID,
    data: NotebookCreate,
    db: AsyncSession = Depends(get_db),
) -> NotebookResponse:
    service = NotebookService(db)
    notebook = await service.create_notebook(project_id, data)
    return NotebookResponse.model_validate(notebook)


@router.get(
    "/projects/{project_id}/notebooks",
    response_model=NotebookListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Notebooks in Project",
    description="List all notebooks in a project.",
)
async def list_notebooks_in_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> NotebookListResponse:
    service = NotebookService(db)
    notebooks = await service.list_notebooks_by_project(project_id)
    items = [NotebookResponse.model_validate(n) for n in notebooks]
    return NotebookListResponse(items=items, total=len(items))


@router.get(
    "/notebooks/{notebook_id}",
    response_model=NotebookDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Notebook Details",
    description="Get notebook details by UUID, including cells ordered by position and metadata.",
)
async def get_notebook(
    notebook_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> NotebookDetailResponse:
    service = NotebookService(db)
    notebook = await service.get_notebook(
        notebook_id, include_cells=True, include_metadata=True
    )
    cells_resp = [
        NotebookCellResponse.model_validate(cell) for cell in notebook.cells
    ]
    meta_resp = (
        NotebookMetadataResponse.model_validate(notebook.metadata_rec)
        if notebook.metadata_rec
        else None
    )
    return NotebookDetailResponse(
        id=notebook.id,
        project_id=notebook.project_id,
        name=notebook.name,
        description=notebook.description,
        language=notebook.language,
        created_at=notebook.created_at,
        updated_at=notebook.updated_at,
        cells=cells_resp,
        metadata=meta_resp,
    )


@router.patch(
    "/notebooks/{notebook_id}",
    response_model=NotebookResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Notebook",
    description="Partially update a notebook by UUID.",
)
async def update_notebook(
    notebook_id: uuid.UUID,
    data: NotebookUpdate,
    db: AsyncSession = Depends(get_db),
) -> NotebookResponse:
    service = NotebookService(db)
    notebook = await service.update_notebook(notebook_id, data)
    return NotebookResponse.model_validate(notebook)


@router.delete(
    "/notebooks/{notebook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Notebook",
    description="Delete a notebook and cascade delete its cells and metadata.",
)
async def delete_notebook(
    notebook_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    service = NotebookService(db)
    await service.delete_notebook(notebook_id)
