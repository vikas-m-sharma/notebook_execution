import uuid
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.output import ExecutionOutput
from app.schemas.output import OutputEventSchema


class ExecutionOutputRepository:
    """Async repository for execution output persistence and retrieval."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, event: OutputEventSchema) -> ExecutionOutput:
        """Create and persist a single ExecutionOutput record."""
        output = ExecutionOutput(
            execution_id=event.execution_id,
            session_id=event.session_id,
            notebook_id=event.notebook_id,
            cell_id=event.cell_id,
            output_type=event.output_type.value if hasattr(event.output_type, "value") else str(event.output_type),
            content=event.content,
            sequence=event.sequence,
            output_metadata=event.output_metadata,
        )
        self.session.add(output)
        await self.session.flush()
        await self.session.refresh(output)
        return output

    async def bulk_create(self, events: Sequence[OutputEventSchema]) -> list[ExecutionOutput]:
        """Bulk create and persist multiple ExecutionOutput records."""
        outputs = []
        for event in events:
            output = ExecutionOutput(
                execution_id=event.execution_id,
                session_id=event.session_id,
                notebook_id=event.notebook_id,
                cell_id=event.cell_id,
                output_type=event.output_type.value if hasattr(event.output_type, "value") else str(event.output_type),
                content=event.content,
                sequence=event.sequence,
                output_metadata=event.output_metadata,
            )
            self.session.add(output)
            outputs.append(output)

        await self.session.flush()
        for output in outputs:
            await self.session.refresh(output)
        return outputs

    async def list_by_execution_id(self, execution_id: str) -> Sequence[ExecutionOutput]:
        """Retrieve sequence-ordered outputs for a given execution_id."""
        stmt = (
            select(ExecutionOutput)
            .where(ExecutionOutput.execution_id == execution_id)
            .order_by(ExecutionOutput.sequence.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_cell_id(self, cell_id: str) -> Sequence[ExecutionOutput]:
        """Retrieve sequence-ordered outputs for a given cell_id."""
        stmt = (
            select(ExecutionOutput)
            .where(ExecutionOutput.cell_id == cell_id)
            .order_by(ExecutionOutput.sequence.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
