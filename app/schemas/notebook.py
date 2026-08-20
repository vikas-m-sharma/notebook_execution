import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.notebook_cell import NotebookCellResponse
from app.schemas.notebook_metadata import NotebookMetadataResponse


class NotebookCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, json_schema_extra={"example": "Fraud Analysis"})
    description: Optional[str] = Field(None, max_length=2048, json_schema_extra={"example": "Fraud detection analysis notebook"})
    language: str = Field("python", max_length=50, json_schema_extra={"example": "python"})


class NotebookUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2048)
    language: Optional[str] = Field(None, max_length=50)


class NotebookResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: Optional[str] = None
    language: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotebookDetailResponse(NotebookResponse):
    cells: list[NotebookCellResponse] = Field(default_factory=list)
    metadata: Optional[NotebookMetadataResponse] = None


class NotebookListResponse(BaseModel):
    items: list[NotebookResponse]
    total: int
