import uuid
from typing import Sequence

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import Workspace
from app.repositories.workspace import WorkspaceRepository
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate


class WorkspaceService:
    """Service encapsulating business logic for Workspace operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = WorkspaceRepository(session)

    async def create_workspace(self, data: WorkspaceCreate) -> Workspace:
        """Create a new Workspace, verifying name uniqueness."""
        workspaces = await self.repository.list_all()
        if any(w.name == data.name for w in workspaces):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Workspace with name '{data.name}' already exists.",
            )
        try:
            return await self.repository.create(
                name=data.name,
                description=data.description,
            )
        except IntegrityError as exc:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Workspace with name '{data.name}' already exists.",
            ) from exc

    async def get_workspace(self, workspace_id: uuid.UUID) -> Workspace:
        """Retrieve a Workspace by ID or raise HTTP 404."""
        workspace = await self.repository.get_by_id(workspace_id)
        if workspace is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workspace '{workspace_id}' not found.",
            )
        return workspace

    async def list_workspaces(self) -> Sequence[Workspace]:
        """List all Workspaces."""
        return await self.repository.list_all()

    async def update_workspace(
        self, workspace_id: uuid.UUID, data: WorkspaceUpdate
    ) -> Workspace:
        """Update an existing Workspace or raise HTTP 404/409."""
        await self.get_workspace(workspace_id)
        if data.name is not None:
            workspaces = await self.repository.list_all()
            if any(w.name == data.name and w.id != workspace_id for w in workspaces):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Workspace with name '{data.name}' already exists.",
                )
        try:
            updated = await self.repository.update(
                workspace_id=workspace_id,
                name=data.name,
                description=data.description,
            )
            if updated is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Workspace '{workspace_id}' not found.",
                )
            return updated
        except IntegrityError as exc:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Workspace with name '{data.name}' already exists.",
            ) from exc

    async def delete_workspace(self, workspace_id: uuid.UUID) -> None:
        """Delete a Workspace by ID or raise HTTP 404."""
        await self.get_workspace(workspace_id)
        deleted = await self.repository.delete(workspace_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workspace '{workspace_id}' not found.",
            )
