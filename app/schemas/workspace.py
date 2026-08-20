import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, json_schema_extra={"example": "Data Engineering"})
    description: Optional[str] = Field(None, max_length=2048, json_schema_extra={"example": "Data engineering workspace"})


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2048)


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkspaceListResponse(BaseModel):
    items: list[WorkspaceResponse]
    total: int
