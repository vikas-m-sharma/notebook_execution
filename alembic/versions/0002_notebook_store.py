"""Phase 2 Notebook Store schema migration

Revision ID: 0002_notebook_store
Revises: 0001_baseline
Create Date: 2026-08-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0002_notebook_store'
down_revision: Union[str, None] = '0001_baseline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create workspaces table
    op.create_table(
        'workspaces',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workspaces_name'), 'workspaces', ['name'], unique=True)

    # 2. Create projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'name', name='uq_project_workspace_name')
    )
    op.create_index(op.f('ix_projects_workspace_id'), 'projects', ['workspace_id'], unique=False)

    # 3. Create notebooks table
    op.create_table(
        'notebooks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('language', sa.String(length=50), nullable=False, server_default='python'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'name', name='uq_notebook_project_name')
    )
    op.create_index(op.f('ix_notebooks_project_id'), 'notebooks', ['project_id'], unique=False)

    # 4. Create notebook_cells table
    op.create_table(
        'notebook_cells',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('notebook_id', sa.UUID(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('cell_type', sa.String(length=50), nullable=False, server_default='code'),
        sa.Column('source', sa.Text(), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['notebook_id'], ['notebooks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('notebook_id', 'position', name='uq_notebook_cell_position')
    )
    op.create_index(op.f('ix_notebook_cells_notebook_id'), 'notebook_cells', ['notebook_id'], unique=False)
    op.create_index('idx_cell_notebook_position', 'notebook_cells', ['notebook_id', 'position'], unique=False)

    # 5. Create notebook_metadata table
    op.create_table(
        'notebook_metadata',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('notebook_id', sa.UUID(), nullable=False),
        sa.Column('configuration', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['notebook_id'], ['notebooks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('notebook_id')
    )
    op.create_index(op.f('ix_notebook_metadata_notebook_id'), 'notebook_metadata', ['notebook_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_notebook_metadata_notebook_id'), table_name='notebook_metadata')
    op.drop_table('notebook_metadata')
    op.drop_index('idx_cell_notebook_position', table_name='notebook_cells')
    op.drop_index(op.f('ix_notebook_cells_notebook_id'), table_name='notebook_cells')
    op.drop_table('notebook_cells')
    op.drop_index(op.f('ix_notebooks_project_id'), table_name='notebooks')
    op.drop_table('notebooks')
    op.drop_index(op.f('ix_projects_workspace_id'), table_name='projects')
    op.drop_table('projects')
    op.drop_index(op.f('ix_workspaces_name'), table_name='workspaces')
    op.drop_table('workspaces')
