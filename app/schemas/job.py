import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class CreateJobRequest(BaseModel):
    """Schema for creating a new Job definition."""

    name: str = Field(..., min_length=1, max_length=255, description="Unique job identifier name (e.g. 'daily-sales-report').")
    notebook_id: uuid.UUID = Field(..., description="Target notebook UUID to execute.")
    workspace_id: Optional[uuid.UUID] = Field(None, description="Parent workspace UUID.")
    project_id: Optional[uuid.UUID] = Field(None, description="Parent project UUID.")
    description: Optional[str] = Field(None, max_length=2048, description="Detailed job description.")
    schedule_type: str = Field("ONE_TIME", max_length=50, description="Scheduling strategy (ONE_TIME or CRON).")
    cron_expression: Optional[str] = Field(None, max_length=100, description="5-field cron expression (e.g. '0 2 * * *').")
    timezone: str = Field("UTC", max_length=100, description="Explicit timezone identifier (e.g. 'Asia/Kolkata', 'UTC').")
    concurrency_policy: str = Field("PREVENT_OVERLAP", max_length=50, description="Concurrency policy (ALLOW_CONCURRENT or PREVENT_OVERLAP).")
    max_retries: int = Field(0, ge=0, le=10, description="Maximum execution retry attempts.")
    retry_delay_seconds: int = Field(60, ge=0, le=3600, description="Delay in seconds between retries.")
    parameters: Optional[dict[str, Any]] = Field(None, description="Runtime execution parameters provided to notebook context.")


class UpdateJobRequest(BaseModel):
    """Schema for updating an existing Job definition."""

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Updated job name.")
    description: Optional[str] = Field(None, max_length=2048, description="Updated job description.")
    schedule_type: Optional[str] = Field(None, max_length=50, description="Updated schedule type.")
    cron_expression: Optional[str] = Field(None, max_length=100, description="Updated cron expression.")
    timezone: Optional[str] = Field(None, max_length=100, description="Updated timezone.")
    concurrency_policy: Optional[str] = Field(None, max_length=50, description="Updated concurrency policy.")
    max_retries: Optional[int] = Field(None, ge=0, le=10, description="Updated max retries.")
    retry_delay_seconds: Optional[int] = Field(None, ge=0, le=3600, description="Updated retry delay in seconds.")
    parameters: Optional[dict[str, Any]] = Field(None, description="Updated runtime parameters.")


class JobResponse(BaseModel):
    """Schema representing a Job definition."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: Optional[str] = None
    workspace_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    notebook_id: uuid.UUID
    status: str
    schedule_type: str
    cron_expression: Optional[str] = None
    timezone: str
    concurrency_policy: str
    max_retries: int
    retry_delay_seconds: int
    parameters: dict[str, Any]
    next_run_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class JobListResponse(BaseModel):
    """Schema for listing Jobs."""

    items: list[JobResponse]
    total: int


class JobExecutionResponse(BaseModel):
    """Schema representing a Job execution history record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    execution_id: str
    status: str
    trigger_type: str
    retry_count: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    error_message: Optional[str] = None
    created_at: datetime


class JobExecutionListResponse(BaseModel):
    """Schema for listing Job execution history records."""

    items: list[JobExecutionResponse]
    total: int
