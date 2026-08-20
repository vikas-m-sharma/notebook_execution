import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.execution.enums import ExecutionStatus


class ExecutionRequestPayload(BaseModel):
    """Payload for submitting a code execution request."""

    session_id: str
    code: str
    cell_id: Optional[str] = None
    notebook_id: Optional[uuid.UUID] = None
    timeout: Optional[float] = Field(default=30.0, ge=0.1, le=3600.0)


class ExecutionResultPayload(BaseModel):
    """Response payload summarizing an execution result."""

    execution_id: str
    request_id: str
    session_id: str
    cell_id: Optional[str] = None
    status: ExecutionStatus
    stdout: str = ""
    stderr: str = ""
    traceback: Optional[str] = None
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0


class ExecutionTask(BaseModel):
    """Internal model tracking live cell execution status and metadata."""

    execution_id: str = Field(
        default_factory=lambda: f"exec-{uuid.uuid4().hex[:12]}"
    )
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )
    session_id: str
    notebook_id: Optional[uuid.UUID] = None
    cell_id: Optional[str] = None
    code: str
    status: ExecutionStatus = ExecutionStatus.QUEUED
    timeout_seconds: float = 30.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    stdout: str = ""
    stderr: str = ""
    traceback: Optional[str] = None
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0

    model_config = ConfigDict(from_attributes=True)
