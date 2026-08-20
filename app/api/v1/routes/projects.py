import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.project import ProjectService

router = APIRouter()


@router.post(
    "/workspaces/{workspace_id}/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Project",
    description="Create a new project within a workspace.",
)
async def create_project(
    workspace_id: uuid.UUID,
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    service = ProjectService(db)
    project = await service.create_project(workspace_id, data)
    return ProjectResponse.model_validate(project)


@router.get(
    "/workspaces/{workspace_id}/projects",
    response_model=ProjectListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Projects in Workspace",
    description="List all projects in a workspace.",
)
async def list_projects_in_workspace(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ProjectListResponse:
    service = ProjectService(db)
    projects = await service.list_projects_by_workspace(workspace_id)
    items = [ProjectResponse.model_validate(p) for p in projects]
    return ProjectListResponse(items=items, total=len(items))


@router.get(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Project",
    description="Get project details by UUID.",
)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    service = ProjectService(db)
    project = await service.get_project(project_id)
    return ProjectResponse.model_validate(project)


@router.patch(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Project",
    description="Partially update a project by UUID.",
)
async def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    service = ProjectService(db)
    project = await service.update_project(project_id, data)
    return ProjectResponse.model_validate(project)


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Project",
    description="Delete a project and cascade delete its notebooks and cells.",
)
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    service = ProjectService(db)
    await service.delete_project(project_id)
