import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import Workspace


class WorkspaceRepository:
    """Repository handling persistence operations for Workspace entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, name: str, description: str | None = None) -> Workspace:
        """Create and persist a new Workspace."""
        workspace = Workspace(name=name, description=description)
        self.session.add(workspace)
        await self.session.flush()
        await self.session.refresh(workspace)
        return workspace

    async def get_by_id(self, workspace_id: uuid.UUID) -> Workspace | None:
        """Retrieve a Workspace by its UUID."""
        result = await self.session.execute(
            select(Workspace).where(Workspace.id == workspace_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> Sequence[Workspace]:
        """List all workspaces ordered by creation date."""
        result = await self.session.execute(
            select(Workspace).order_by(Workspace.created_at.desc())
        )
        return result.scalars().all()

    async def update(
        self,
        workspace_id: uuid.UUID,
        name: str | None = None,
        description: str | None = None,
    ) -> Workspace | None:
        """Update fields of an existing Workspace."""
        workspace = await self.get_by_id(workspace_id)
        if workspace is None:
            return None
        if name is not None:
            workspace.name = name
        if description is not None:
            workspace.description = description
        await self.session.flush()
        await self.session.refresh(workspace)
        return workspace

    async def delete(self, workspace_id: uuid.UUID) -> bool:
        """Delete a Workspace by its UUID."""
        workspace = await self.get_by_id(workspace_id)
        if workspace is None:
            return False
        await self.session.delete(workspace)
        await self.session.flush()
        return True
