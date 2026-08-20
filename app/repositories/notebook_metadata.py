import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notebook_metadata import NotebookMetadata


class NotebookMetadataRepository:
    """Repository handling persistence operations for NotebookMetadata entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_notebook_id(
        self, notebook_id: uuid.UUID
    ) -> NotebookMetadata | None:
        """Retrieve NotebookMetadata for a specific notebook."""
        result = await self.session.execute(
            select(NotebookMetadata).where(
                NotebookMetadata.notebook_id == notebook_id
            )
        )
        return result.scalar_one_or_none()

    async def create_or_update(
        self,
        notebook_id: uuid.UUID,
        configuration: dict[str, Any],
    ) -> NotebookMetadata:
        """Create or update NotebookMetadata for a notebook."""
        metadata_rec = await self.get_by_notebook_id(notebook_id)
        if metadata_rec is None:
            metadata_rec = NotebookMetadata(
                notebook_id=notebook_id,
                configuration=configuration,
            )
            self.session.add(metadata_rec)
        else:
            metadata_rec.configuration = configuration
        await self.session.flush()
        await self.session.refresh(metadata_rec)
        return metadata_rec

    async def delete(self, notebook_id: uuid.UUID) -> bool:
        """Delete NotebookMetadata for a notebook."""
        metadata_rec = await self.get_by_notebook_id(notebook_id)
        if metadata_rec is None:
            return False
        await self.session.delete(metadata_rec)
        await self.session.flush()
        return True
