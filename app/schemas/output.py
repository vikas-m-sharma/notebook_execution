import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.output.enums import OutputType


class OutputEventSchema(BaseModel):
    """Payload representing a single execution output event."""

    execution_id: str
    session_id: str
    notebook_id: Optional[uuid.UUID] = None
    cell_id: Optional[str] = None
    output_type: OutputType
    content: str
    sequence: int = 1
    output_metadata: Optional[dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExecutionOutputRead(BaseModel):
    """Pydantic read model for an ExecutionOutput record."""

    id: uuid.UUID
    execution_id: str
    session_id: str
    notebook_id: Optional[uuid.UUID] = None
    cell_id: Optional[str] = None
    output_type: OutputType
    content: str
    sequence: int
    output_metadata: Optional[dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OutputMetricsSchema(BaseModel):
    """Metrics model summarizing execution outputs."""

    execution_id: str
    total_events: int = 0
    stdout_count: int = 0
    stderr_count: int = 0
    result_present: bool = False
    traceback_present: bool = False
    truncated: bool = False
    execution_time_ms: float = 0.0
