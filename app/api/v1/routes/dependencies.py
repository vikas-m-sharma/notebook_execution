import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.exceptions import DependencyValidationError
from app.dependencies.manager import DependencyManager
from app.schemas.dependency import (
    DependencyCreate,
    DependencyListResponse,
    DependencyOperationResponse,
    DependencyResponse,
    DependencyUpdate,
)

router = APIRouter()


@router.post(
    "/notebooks/{notebook_id}/dependencies",
    response_model=DependencyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Declare Notebook Dependency",
    description="Declare a Python package dependency constraint for a notebook.",
)
async def declare_dependency(
    notebook_id: uuid.UUID,
    data: DependencyCreate,
    db: AsyncSession = Depends(get_db),
) -> DependencyResponse:
    manager = DependencyManager(db)
    try:
        dep = await manager.declare_dependency(
            notebook_id=notebook_id,
            package_name=data.package_name,
            version_specifier=data.version_specifier,
        )
        await db.commit()
        return DependencyResponse.model_validate(dep)
    except DependencyValidationError as err:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err


@router.get(
    "/notebooks/{notebook_id}/dependencies",
    response_model=DependencyListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Notebook Dependencies",
    description="List all declared package dependencies for a notebook.",
)
async def list_dependencies(
    notebook_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DependencyListResponse:
    manager = DependencyManager(db)
    deps = await manager.list_dependencies(notebook_id)
    items = [DependencyResponse.model_validate(d) for d in deps]
    return DependencyListResponse(items=items, total=len(items))


@router.patch(
    "/notebooks/{notebook_id}/dependencies/{dependency_id}",
    response_model=DependencyResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Notebook Dependency",
    description="Update version specifier constraint for a notebook dependency.",
)
async def update_dependency(
    notebook_id: uuid.UUID,
    dependency_id: uuid.UUID,
    data: DependencyUpdate,
    db: AsyncSession = Depends(get_db),
) -> DependencyResponse:
    manager = DependencyManager(db)
    dep = await manager.dep_repo.get_by_id(dependency_id)
    if not dep or dep.notebook_id != notebook_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dependency '{dependency_id}' not found for notebook '{notebook_id}'.",
        )

    try:
        updated = await manager.dep_repo.update(dependency_id, data.version_specifier)
        await db.commit()
        return DependencyResponse.model_validate(updated)
    except DependencyValidationError as err:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err


@router.delete(
    "/notebooks/{notebook_id}/dependencies/{dependency_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Notebook Dependency",
    description="Delete a declared package dependency from a notebook.",
)
async def delete_dependency(
    notebook_id: uuid.UUID,
    dependency_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    manager = DependencyManager(db)
    dep = await manager.dep_repo.get_by_id(dependency_id)
    if not dep or dep.notebook_id != notebook_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dependency '{dependency_id}' not found for notebook '{notebook_id}'.",
        )
    await manager.delete_dependency(dependency_id)
    await db.commit()


@router.get(
    "/dependency-operations/{operation_id}",
    response_model=DependencyOperationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Dependency Operation",
    description="Get details and current status lifecycle of a dependency operation.",
)
async def get_dependency_operation(
    operation_id: str,
    db: AsyncSession = Depends(get_db),
) -> DependencyOperationResponse:
    manager = DependencyManager(db)
    op_rec = await manager.op_repo.get_by_operation_id(operation_id)
    if not op_rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dependency operation '{operation_id}' not found.",
        )
    return DependencyOperationResponse.model_validate(op_rec)
