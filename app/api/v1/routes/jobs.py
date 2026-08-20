import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.jobs.exceptions import (
    JobCancellationError,
    JobConcurrencyError,
    JobExecutionError,
    JobNotFoundError,
    JobValidationError,
    ScheduleValidationError,
)
from app.jobs.manager import JobManager
from app.schemas.job import (
    CreateJobRequest,
    JobExecutionListResponse,
    JobExecutionResponse,
    JobListResponse,
    JobResponse,
    UpdateJobRequest,
)

router = APIRouter()


@router.post(
    "/jobs",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Scheduled or Manual Job",
    description="Create a new job definition associated with a notebook.",
)
async def create_job(
    data: CreateJobRequest,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    manager = JobManager(db)
    try:
        job = await manager.create_job(
            name=data.name,
            notebook_id=data.notebook_id,
            workspace_id=data.workspace_id,
            project_id=data.project_id,
            description=data.description,
            schedule_type=data.schedule_type,
            cron_expression=data.cron_expression,
            tz_name=data.timezone,
            concurrency_policy=data.concurrency_policy,
            max_retries=data.max_retries,
            retry_delay_seconds=data.retry_delay_seconds,
            parameters=data.parameters,
        )
        await db.commit()
        return JobResponse.model_validate(job)
    except (JobValidationError, ScheduleValidationError) as err:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err


@router.get(
    "/jobs",
    response_model=JobListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Jobs",
    description="List jobs optionally filtered by workspace, project, or notebook.",
)
async def list_jobs(
    workspace_id: Optional[uuid.UUID] = None,
    project_id: Optional[uuid.UUID] = None,
    notebook_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
) -> JobListResponse:
    manager = JobManager(db)
    jobs = await manager.list_jobs(
        workspace_id=workspace_id,
        project_id=project_id,
        notebook_id=notebook_id,
    )
    items = [JobResponse.model_validate(j) for j in jobs]
    return JobListResponse(items=items, total=len(items))


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Job Details",
    description="Retrieve job definition details by UUID.",
)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    manager = JobManager(db)
    try:
        job = await manager.get_job(job_id)
        return JobResponse.model_validate(job)
    except JobNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err


@router.patch(
    "/jobs/{job_id}",
    response_model=JobResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Job",
    description="Update job configuration or schedule.",
)
async def update_job(
    job_id: uuid.UUID,
    data: UpdateJobRequest,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    manager = JobManager(db)
    try:
        updated = await manager.update_job(
            job_id=job_id,
            name=data.name,
            description=data.description,
            schedule_type=data.schedule_type,
            cron_expression=data.cron_expression,
            tz_name=data.timezone,
            concurrency_policy=data.concurrency_policy,
            max_retries=data.max_retries,
            retry_delay_seconds=data.retry_delay_seconds,
            parameters=data.parameters,
        )
        await db.commit()
        return JobResponse.model_validate(updated)
    except JobNotFoundError as err:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except (JobValidationError, ScheduleValidationError) as err:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err


@router.delete(
    "/jobs/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Job",
    description="Delete job definition record.",
)
async def delete_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    manager = JobManager(db)
    try:
        await manager.delete_job(job_id)
        await db.commit()
    except JobNotFoundError as err:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err


@router.post(
    "/jobs/{job_id}/run",
    response_model=JobExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger Manual Job Execution",
    description="Manually trigger notebook execution for a job.",
)
async def trigger_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> JobExecutionResponse:
    manager = JobManager(db)
    try:
        history = await manager.trigger_job_execution(job_id, trigger_type="MANUAL")
        await db.commit()
        return JobExecutionResponse.model_validate(history)
    except JobNotFoundError as err:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except JobConcurrencyError as err:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(err),
        ) from err
    except (JobValidationError, JobExecutionError) as err:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err


@router.post(
    "/jobs/{job_id}/pause",
    response_model=JobResponse,
    status_code=status.HTTP_200_OK,
    summary="Pause Job",
    description="Pause job schedule evaluation.",
)
async def pause_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    manager = JobManager(db)
    try:
        paused = await manager.pause_job(job_id)
        await db.commit()
        return JobResponse.model_validate(paused)
    except JobNotFoundError as err:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err


@router.post(
    "/jobs/{job_id}/resume",
    response_model=JobResponse,
    status_code=status.HTTP_200_OK,
    summary="Resume Job",
    description="Resume job schedule evaluation.",
)
async def resume_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    manager = JobManager(db)
    try:
        resumed = await manager.resume_job(job_id)
        await db.commit()
        return JobResponse.model_validate(resumed)
    except JobNotFoundError as err:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err


@router.post(
    "/jobs/{job_id}/cancel/{execution_id}",
    response_model=JobExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel Job Execution",
    description="Cancel active running execution for a job.",
)
async def cancel_job_execution(
    job_id: uuid.UUID,
    execution_id: str,
    db: AsyncSession = Depends(get_db),
) -> JobExecutionResponse:
    manager = JobManager(db)
    try:
        cancelled = await manager.cancel_job_execution(job_id, execution_id)
        await db.commit()
        return JobExecutionResponse.model_validate(cancelled)
    except (JobNotFoundError, JobCancellationError) as err:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err


@router.get(
    "/jobs/{job_id}/executions",
    response_model=JobExecutionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Job Executions",
    description="Retrieve execution history records for a job.",
)
async def list_job_executions(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> JobExecutionListResponse:
    manager = JobManager(db)
    try:
        executions = await manager.list_job_executions(job_id)
        items = [JobExecutionResponse.model_validate(e) for e in executions]
        return JobExecutionListResponse(items=items, total=len(items))
    except JobNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
