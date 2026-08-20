import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.execution.session.enums import SessionStatus


class ExecutionRequest(BaseModel):
    """Payload representing a single code execution request inside a session."""

    session_id: str
    code: str
    cell_id: Optional[str] = None
    request_id: Optional[str] = None


class ExecutionResult(BaseModel):
    """Payload representing the result of executing code inside a session."""

    session_id: str
    request_id: str
    cell_id: Optional[str] = None
    status: str = Field(..., json_schema_extra={"example": "ok"})
    result: Any = None
    stdout: str = ""
    stderr: str = ""
    traceback: Optional[str] = None
    execution_time_ms: float = 0.0


class SessionInfo(BaseModel):
    """Information model for an active Execution Session."""

    session_id: str
    notebook_id: uuid.UUID
    runtime_id: uuid.UUID
    status: SessionStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
