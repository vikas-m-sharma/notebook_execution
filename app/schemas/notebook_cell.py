import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class NotebookCellCreate(BaseModel):
    position: int = Field(..., ge=0, json_schema_extra={"example": 0})
    cell_type: str = Field("code", json_schema_extra={"example": "code"})
    source: str = Field("", json_schema_extra={"example": "import pandas as pd"})


class NotebookCellUpdate(BaseModel):
    position: Optional[int] = Field(None, ge=0)
    cell_type: Optional[str] = None
    source: Optional[str] = None


class NotebookCellResponse(BaseModel):
    id: uuid.UUID
    notebook_id: uuid.UUID
    position: int
    cell_type: str
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotebookCellListResponse(BaseModel):
    items: list[NotebookCellResponse]
    total: int
