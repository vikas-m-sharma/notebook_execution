import uuid
from typing import Sequence

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.output.manager import OutputManager
from app.schemas.output import ExecutionOutputRead

router = APIRouter(prefix="", tags=["Execution Outputs"])
output_manager = OutputManager()


@router.get(
    "/executions/{execution_id}/outputs",
    response_model=list[ExecutionOutputRead],
    status_code=status.HTTP_200_OK,
    summary="Get Execution Outputs",
    description="Retrieve sequence-ordered execution output records for a specific execution_id.",
)
async def get_execution_outputs(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
) -> Sequence[ExecutionOutputRead]:
    """Retrieve outputs for execution_id."""
    return await output_manager.get_outputs_by_execution(db, execution_id)


@router.get(
    "/notebooks/{notebook_id}/cells/{cell_id}/outputs",
    response_model=list[ExecutionOutputRead],
    status_code=status.HTTP_200_OK,
    summary="Get Cell Outputs",
    description="Retrieve sequence-ordered execution output records for a specific notebook cell_id.",
)
async def get_cell_outputs(
    notebook_id: uuid.UUID,
    cell_id: str,
    db: AsyncSession = Depends(get_db),
) -> Sequence[ExecutionOutputRead]:
    """Retrieve outputs for cell_id."""
    return await output_manager.get_outputs_by_cell(db, cell_id)
