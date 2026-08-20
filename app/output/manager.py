import uuid
from typing import Any, Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.output.enums import OutputType
from app.output.publisher import OutputPublisher
from app.repositories.output import ExecutionOutputRepository
from app.schemas.output import (
    ExecutionOutputRead,
    OutputEventSchema,
    OutputMetricsSchema,
)


class OutputManager:
    """Output Manager for capturing, normalizing, sequence ordering, truncating, publishing, and persisting execution outputs."""

    DEFAULT_MAX_OUTPUT_SIZE: int = 100_000  # 100 KB max content length per event

    def __init__(
        self,
        publisher: Optional[OutputPublisher] = None,
        max_output_size: int = DEFAULT_MAX_OUTPUT_SIZE,
    ) -> None:
        self.publisher: OutputPublisher = publisher or OutputPublisher()
        self.max_output_size: int = max_output_size

    def create_output_events(
        self,
        execution_id: str,
        session_id: str,
        notebook_id: Optional[uuid.UUID] = None,
        cell_id: Optional[str] = None,
        stdout: str = "",
        stderr: str = "",
        traceback: Optional[str] = None,
        status: str = "ok",
        execution_time_ms: float = 0.0,
    ) -> tuple[list[OutputEventSchema], OutputMetricsSchema]:
        """Normalize raw execution output strings into a sequence of OutputEvent objects and compute metrics."""
        events: list[OutputEventSchema] = []
        seq = 1
        stdout_count = 0
        stderr_count = 0
        result_present = False
        traceback_present = False
        is_truncated = False

        def _truncate_if_needed(text: str) -> tuple[str, bool]:
            if len(text.encode("utf-8")) > self.max_output_size:
                truncated_text = text[: self.max_output_size] + "\n[OUTPUT TRUNCATED - SIZE LIMIT EXCEEDED]"
                return truncated_text, True
            return text, False

        # 1. Process STDOUT
        if stdout:
            stdout_count += 1
            content, trunc = _truncate_if_needed(stdout)
            if trunc:
                is_truncated = True
            events.append(
                OutputEventSchema(
                    execution_id=execution_id,
                    session_id=session_id,
                    notebook_id=notebook_id,
                    cell_id=cell_id,
                    output_type=OutputType.STDOUT,
                    content=content,
                    sequence=seq,
                    output_metadata={"truncated": trunc, "stream": "stdout"},
                )
            )
            seq += 1

        # 2. Process STDERR
        if stderr:
            stderr_count += 1
            content, trunc = _truncate_if_needed(stderr)
            if trunc:
                is_truncated = True
            events.append(
                OutputEventSchema(
                    execution_id=execution_id,
                    session_id=session_id,
                    notebook_id=notebook_id,
                    cell_id=cell_id,
                    output_type=OutputType.STDERR,
                    content=content,
                    sequence=seq,
                    output_metadata={"truncated": trunc, "stream": "stderr"},
                )
            )
            seq += 1

        # 3. Process TRACEBACK if execution failed
        if traceback:
            traceback_present = True
            content, trunc = _truncate_if_needed(traceback)
            if trunc:
                is_truncated = True
            events.append(
                OutputEventSchema(
                    execution_id=execution_id,
                    session_id=session_id,
                    notebook_id=notebook_id,
                    cell_id=cell_id,
                    output_type=OutputType.TRACEBACK,
                    content=content,
                    sequence=seq,
                    output_metadata={"truncated": trunc, "status": status},
                )
            )
            seq += 1

        # 4. If execution succeeded and stdout was not present, emit RESULT tag
        if status in ("ok", "succeeded") and not stdout and not traceback:
            result_present = True
            events.append(
                OutputEventSchema(
                    execution_id=execution_id,
                    session_id=session_id,
                    notebook_id=notebook_id,
                    cell_id=cell_id,
                    output_type=OutputType.RESULT,
                    content="Success",
                    sequence=seq,
                    output_metadata={"truncated": False},
                )
            )
            seq += 1

        metrics = OutputMetricsSchema(
            execution_id=execution_id,
            total_events=len(events),
            stdout_count=stdout_count,
            stderr_count=stderr_count,
            result_present=result_present,
            traceback_present=traceback_present,
            truncated=is_truncated,
            execution_time_ms=execution_time_ms,
        )

        return events, metrics

    async def process_and_persist_events(
        self,
        db_session: AsyncSession,
        events: Sequence[OutputEventSchema],
    ) -> list[ExecutionOutputRead]:
        """Publish events to streaming subscribers and persist to PostgreSQL database."""
        repo = ExecutionOutputRepository(db_session)

        # 1. Stream events
        for event in events:
            await self.publisher.publish(event)

        # 2. Persist to PostgreSQL
        created_records = await repo.bulk_create(events)
        return [ExecutionOutputRead.model_validate(rec) for rec in created_records]

    async def get_outputs_by_execution(
        self,
        db_session: AsyncSession,
        execution_id: str,
    ) -> list[ExecutionOutputRead]:
        """Retrieve sequence-ordered outputs for execution_id from database."""
        repo = ExecutionOutputRepository(db_session)
        records = await repo.list_by_execution_id(execution_id)
        return [ExecutionOutputRead.model_validate(rec) for rec in records]

    async def get_outputs_by_cell(
        self,
        db_session: AsyncSession,
        cell_id: str,
    ) -> list[ExecutionOutputRead]:
        """Retrieve sequence-ordered outputs for cell_id from database."""
        repo = ExecutionOutputRepository(db_session)
        records = await repo.list_by_cell_id(cell_id)
        return [ExecutionOutputRead.model_validate(rec) for rec in records]
