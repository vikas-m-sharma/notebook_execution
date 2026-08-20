"""Phase 11 Job Manager schema migration

Revision ID: 0006_job_manager
Revises: 0005_data_connectors
Create Date: 2026-08-16 19:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0006_job_manager'
down_revision: Union[str, None] = '0005_data_connectors'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create jobs table
    op.create_table(
        'jobs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('workspace_id', sa.UUID(), nullable=True),
        sa.Column('project_id', sa.UUID(), nullable=True),
        sa.Column('notebook_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='ACTIVE'),
        sa.Column('schedule_type', sa.String(length=32), nullable=False, server_default='ONE_TIME'),
        sa.Column('cron_expression', sa.String(length=128), nullable=True),
        sa.Column('timezone', sa.String(length=64), nullable=False, server_default='UTC'),
        sa.Column('concurrency_policy', sa.String(length=32), nullable=False, server_default='PREVENT_OVERLAP'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('retry_delay_seconds', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('parameters', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_jobs_name'), 'jobs', ['name'], unique=True)
    op.create_index(op.f('ix_jobs_workspace_id'), 'jobs', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_jobs_project_id'), 'jobs', ['project_id'], unique=False)
    op.create_index(op.f('ix_jobs_notebook_id'), 'jobs', ['notebook_id'], unique=False)
    op.create_index(op.f('ix_jobs_status'), 'jobs', ['status'], unique=False)
    op.create_index(op.f('ix_jobs_schedule_type'), 'jobs', ['schedule_type'], unique=False)
    op.create_index(op.f('ix_jobs_next_run_at'), 'jobs', ['next_run_at'], unique=False)

    # 2. Create job_executions table
    op.create_table(
        'job_executions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('job_id', sa.UUID(), nullable=False),
        sa.Column('execution_id', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='QUEUED'),
        sa.Column('trigger_type', sa.String(length=32), nullable=False, server_default='MANUAL'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_job_executions_job_id'), 'job_executions', ['job_id'], unique=False)
    op.create_index(op.f('ix_job_executions_execution_id'), 'job_executions', ['execution_id'], unique=False)
    op.create_index(op.f('ix_job_executions_status'), 'job_executions', ['status'], unique=False)


def downgrade() -> None:
    # Drop job_executions table
    op.drop_index(op.f('ix_job_executions_status'), table_name='job_executions')
    op.drop_index(op.f('ix_job_executions_execution_id'), table_name='job_executions')
    op.drop_index(op.f('ix_job_executions_job_id'), table_name='job_executions')
    op.drop_table('job_executions')

    # Drop jobs table
    op.drop_index(op.f('ix_jobs_next_run_at'), table_name='jobs')
    op.drop_index(op.f('ix_jobs_schedule_type'), table_name='jobs')
    op.drop_index(op.f('ix_jobs_status'), table_name='jobs')
    op.drop_index(op.f('ix_jobs_notebook_id'), table_name='jobs')
    op.drop_index(op.f('ix_jobs_project_id'), table_name='jobs')
    op.drop_index(op.f('ix_jobs_workspace_id'), table_name='jobs')
    op.drop_index(op.f('ix_jobs_name'), table_name='jobs')
    op.drop_table('jobs')
