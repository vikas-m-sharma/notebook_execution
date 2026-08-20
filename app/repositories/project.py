import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project


class ProjectRepository:
    """Repository handling persistence operations for Project entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        workspace_id: uuid.UUID,
        name: str,
        description: str | None = None,
    ) -> Project:
        """Create and persist a new Project associated with a Workspace."""
        project = Project(
            workspace_id=workspace_id,
            name=name,
            description=description,
        )
        self.session.add(project)
        await self.session.flush()
        await self.session.refresh(project)
        return project

    async def get_by_id(self, project_id: uuid.UUID) -> Project | None:
        """Retrieve a Project by its UUID."""
        result = await self.session.execute(
            select(Project).where(Project.id == project_id)
        )
        return result.scalar_one_or_none()

    async def list_by_workspace(self, workspace_id: uuid.UUID) -> Sequence[Project]:
        """List all Projects belonging to a Workspace."""
        result = await self.session.execute(
            select(Project)
            .where(Project.workspace_id == workspace_id)
            .order_by(Project.name.asc())
        )
        return result.scalars().all()

    async def update(
        self,
        project_id: uuid.UUID,
        name: str | None = None,
        description: str | None = None,
    ) -> Project | None:
        """Update fields of an existing Project."""
        project = await self.get_by_id(project_id)
        if project is None:
            return None
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        await self.session.flush()
        await self.session.refresh(project)
        return project

    async def delete(self, project_id: uuid.UUID) -> bool:
        """Delete a Project by its UUID."""
        project = await self.get_by_id(project_id)
        if project is None:
            return False
        await self.session.delete(project)
        await self.session.flush()
        return True
