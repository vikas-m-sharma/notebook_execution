import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class DependencyCreate(BaseModel):
    """Schema for declaring a notebook package dependency."""

    package_name: str = Field(..., max_length=255, description="PyPI package name (e.g. pandas, numpy).")
    version_specifier: Optional[str] = Field(None, max_length=255, description="Optional version specifier (e.g. ==2.2.3, >=2.0).")


class DependencyUpdate(BaseModel):
    """Schema for updating a notebook package dependency version specifier."""

    version_specifier: Optional[str] = Field(None, max_length=255, description="Updated version specifier (e.g. ==2.2.3).")


class DependencyResponse(BaseModel):
    """Schema representing a persisted notebook package dependency."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    notebook_id: uuid.UUID
    package_name: str
    version_specifier: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DependencyListResponse(BaseModel):
    """List response schema for notebook dependencies."""

    items: list[DependencyResponse]
    total: int


class DependencyInstallRequest(BaseModel):
    """Schema for requesting dependency installation for a notebook."""

    timeout_seconds: Optional[float] = Field(
        120.0, ge=1.0, le=600.0, description="Optional installation timeout in seconds (1.0 to 600.0s)."
    )


class DependencyOperationResponse(BaseModel):
    """Schema representing a dependency installation operation lifecycle record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    operation_id: str
    notebook_id: uuid.UUID
    session_id: Optional[str] = None
    runtime_id: Optional[str] = None
    status: str
    packages: list[dict[str, Any]]
    resolved_versions: Optional[dict[str, str]] = None
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
