import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NotebookMetadataUpdate(BaseModel):
    configuration: dict[str, Any] = Field(..., json_schema_extra={"example": {"timeout_seconds": 600, "dependencies": ["pandas"]}})


class NotebookMetadataResponse(BaseModel):
    id: uuid.UUID
    notebook_id: uuid.UUID
    configuration: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
