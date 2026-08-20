import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notebook_metadata import NotebookMetadata
from app.repositories.notebook import NotebookRepository
from app.repositories.notebook_metadata import NotebookMetadataRepository
from app.schemas.notebook_metadata import NotebookMetadataUpdate


class NotebookMetadataService:
    """Service encapsulating business logic for NotebookMetadata operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.notebook_repository = NotebookRepository(session)
        self.metadata_repository = NotebookMetadataRepository(session)

    async def get_metadata(self, notebook_id: uuid.UUID) -> NotebookMetadata:
        """Retrieve NotebookMetadata for a Notebook or raise HTTP 404."""
        notebook = await self.notebook_repository.get_by_id(notebook_id)
        if notebook is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Notebook '{notebook_id}' not found.",
            )
        metadata_rec = await self.metadata_repository.get_by_notebook_id(notebook_id)
        if metadata_rec is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Metadata for notebook '{notebook_id}' not found.",
            )
        return metadata_rec

    async def update_metadata(
        self, notebook_id: uuid.UUID, data: NotebookMetadataUpdate
    ) -> NotebookMetadata:
        """Create or update NotebookMetadata for a Notebook."""
        notebook = await self.notebook_repository.get_by_id(notebook_id)
        if notebook is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Notebook '{notebook_id}' not found.",
            )
        return await self.metadata_repository.create_or_update(
            notebook_id=notebook_id,
            configuration=data.configuration,
        )
