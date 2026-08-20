import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.notebook_metadata import (
    NotebookMetadataResponse,
    NotebookMetadataUpdate,
)
from app.services.notebook_metadata import NotebookMetadataService

router = APIRouter()


@router.get(
    "/notebooks/{notebook_id}/metadata",
    response_model=NotebookMetadataResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Notebook Metadata",
    description="Get execution/configuration metadata for a notebook.",
)
async def get_notebook_metadata(
    notebook_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> NotebookMetadataResponse:
    service = NotebookMetadataService(db)
    metadata = await service.get_metadata(notebook_id)
    return NotebookMetadataResponse.model_validate(metadata)


@router.patch(
    "/notebooks/{notebook_id}/metadata",
    response_model=NotebookMetadataResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Notebook Metadata",
    description="Create or update execution/configuration metadata for a notebook.",
)
async def update_notebook_metadata(
    notebook_id: uuid.UUID,
    data: NotebookMetadataUpdate,
    db: AsyncSession = Depends(get_db),
) -> NotebookMetadataResponse:
    service = NotebookMetadataService(db)
    metadata = await service.update_metadata(notebook_id, data)
    return NotebookMetadataResponse.model_validate(metadata)
