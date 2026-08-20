import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceListResponse,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from app.services.workspace import WorkspaceService

router = APIRouter()


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Workspace",
    description="Create a new top-level workspace.",
)
async def create_workspace(
    data: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
) -> WorkspaceResponse:
    service = WorkspaceService(db)
    workspace = await service.create_workspace(data)
    return WorkspaceResponse.model_validate(workspace)


@router.get(
    "",
    response_model=WorkspaceListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Workspaces",
    description="List all workspaces.",
)
async def list_workspaces(
    db: AsyncSession = Depends(get_db),
) -> WorkspaceListResponse:
    service = WorkspaceService(db)
    workspaces = await service.list_workspaces()
    items = [WorkspaceResponse.model_validate(w) for w in workspaces]
    return WorkspaceListResponse(items=items, total=len(items))


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Workspace",
    description="Get workspace details by UUID.",
)
async def get_workspace(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> WorkspaceResponse:
    service = WorkspaceService(db)
    workspace = await service.get_workspace(workspace_id)
    return WorkspaceResponse.model_validate(workspace)


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Workspace",
    description="Partially update a workspace by UUID.",
)
async def update_workspace(
    workspace_id: uuid.UUID,
    data: WorkspaceUpdate,
    db: AsyncSession = Depends(get_db),
) -> WorkspaceResponse:
    service = WorkspaceService(db)
    workspace = await service.update_workspace(workspace_id, data)
    return WorkspaceResponse.model_validate(workspace)


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Workspace",
    description="Delete a workspace and cascade delete its projects, notebooks, and cells.",
)
async def delete_workspace(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    service = WorkspaceService(db)
    await service.delete_workspace(workspace_id)
