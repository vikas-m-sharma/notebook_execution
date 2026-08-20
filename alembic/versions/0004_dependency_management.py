"""Phase 9 Dependency Management schema migration

Revision ID: 0004_dependency_management
Revises: 0003_execution_outputs
Create Date: 2026-08-16 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0004_dependency_management'
down_revision: Union[str, None] = '0003_execution_outputs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create notebook_dependencies table
    op.create_table(
        'notebook_dependencies',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('notebook_id', sa.UUID(), nullable=False),
        sa.Column('package_name', sa.String(length=128), nullable=False),
        sa.Column('version_specifier', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['notebook_id'], ['notebooks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notebook_dependencies_notebook_id'), 'notebook_dependencies', ['notebook_id'], unique=False)
    op.create_index(op.f('ix_notebook_dependencies_package_name'), 'notebook_dependencies', ['package_name'], unique=False)
    op.create_index('ix_notebook_dependencies_nb_pkg', 'notebook_dependencies', ['notebook_id', 'package_name'], unique=True)

    # 2. Create dependency_operations table
    op.create_table(
        'dependency_operations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('operation_id', sa.String(length=64), nullable=False),
        sa.Column('notebook_id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=True),
        sa.Column('runtime_id', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='REQUESTED'),
        sa.Column('packages', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
        sa.Column('resolved_versions', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['notebook_id'], ['notebooks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('operation_id')
    )
    op.create_index(op.f('ix_dependency_operations_operation_id'), 'dependency_operations', ['operation_id'], unique=True)
    op.create_index(op.f('ix_dependency_operations_notebook_id'), 'dependency_operations', ['notebook_id'], unique=False)
    op.create_index(op.f('ix_dependency_operations_session_id'), 'dependency_operations', ['session_id'], unique=False)
    op.create_index(op.f('ix_dependency_operations_runtime_id'), 'dependency_operations', ['runtime_id'], unique=False)
    op.create_index(op.f('ix_dependency_operations_status'), 'dependency_operations', ['status'], unique=False)


def downgrade() -> None:
    # Drop dependency_operations table
    op.drop_index(op.f('ix_dependency_operations_status'), table_name='dependency_operations')
    op.drop_index(op.f('ix_dependency_operations_runtime_id'), table_name='dependency_operations')
    op.drop_index(op.f('ix_dependency_operations_session_id'), table_name='dependency_operations')
    op.drop_index(op.f('ix_dependency_operations_notebook_id'), table_name='dependency_operations')
    op.drop_index(op.f('ix_dependency_operations_operation_id'), table_name='dependency_operations')
    op.drop_table('dependency_operations')

    # Drop notebook_dependencies table
    op.drop_index('ix_notebook_dependencies_nb_pkg', table_name='notebook_dependencies')
    op.drop_index(op.f('ix_notebook_dependencies_package_name'), table_name='notebook_dependencies')
    op.drop_index(op.f('ix_notebook_dependencies_notebook_id'), table_name='notebook_dependencies')
    op.drop_table('notebook_dependencies')
