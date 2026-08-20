import uuid
from typing import Sequence

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.repositories.project import ProjectRepository
from app.repositories.workspace import WorkspaceRepository
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    """Service encapsulating business logic for Project operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.workspace_repository = WorkspaceRepository(session)
        self.project_repository = ProjectRepository(session)

    async def create_project(
        self, workspace_id: uuid.UUID, data: ProjectCreate
    ) -> Project:
        """Create a new Project in a Workspace, verifying Workspace existence and name uniqueness."""
        workspace = await self.workspace_repository.get_by_id(workspace_id)
        if workspace is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workspace '{workspace_id}' not found.",
            )
        projects = await self.project_repository.list_by_workspace(workspace_id)
        if any(p.name == data.name for p in projects):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Project with name '{data.name}' already exists in workspace '{workspace_id}'.",
            )
        try:
            return await self.project_repository.create(
                workspace_id=workspace_id,
                name=data.name,
                description=data.description,
            )
        except IntegrityError as exc:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Project with name '{data.name}' already exists in workspace '{workspace_id}'.",
            ) from exc

    async def get_project(self, project_id: uuid.UUID) -> Project:
        """Retrieve a Project by ID or raise HTTP 404."""
        project = await self.project_repository.get_by_id(project_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found.",
            )
        return project

    async def list_projects_by_workspace(
        self, workspace_id: uuid.UUID
    ) -> Sequence[Project]:
        """List all Projects in a Workspace, verifying Workspace existence."""
        workspace = await self.workspace_repository.get_by_id(workspace_id)
        if workspace is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workspace '{workspace_id}' not found.",
            )
        return await self.project_repository.list_by_workspace(workspace_id)

    async def update_project(
        self, project_id: uuid.UUID, data: ProjectUpdate
    ) -> Project:
        """Update an existing Project or raise HTTP 404/409."""
        project = await self.get_project(project_id)
        if data.name is not None:
            projects = await self.project_repository.list_by_workspace(project.workspace_id)
            if any(p.name == data.name and p.id != project_id for p in projects):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Project with name '{data.name}' already exists in this workspace.",
                )
        try:
            updated = await self.project_repository.update(
                project_id=project_id,
                name=data.name,
                description=data.description,
            )
            if updated is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Project '{project_id}' not found.",
                )
            return updated
        except IntegrityError as exc:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Project with name '{data.name}' already exists in this workspace.",
            ) from exc

    async def delete_project(self, project_id: uuid.UUID) -> None:
        """Delete a Project by ID or raise HTTP 404."""
        await self.get_project(project_id)
        deleted = await self.project_repository.delete(project_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found.",
            )
