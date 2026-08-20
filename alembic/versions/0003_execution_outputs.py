"""Phase 8 Execution Outputs schema migration

Revision ID: 0003_execution_outputs
Revises: 0002_notebook_store
Create Date: 2026-08-16 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0003_execution_outputs'
down_revision: Union[str, None] = '0002_notebook_store'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'execution_outputs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('execution_id', sa.String(length=64), nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('notebook_id', sa.UUID(), nullable=True),
        sa.Column('cell_id', sa.String(length=64), nullable=True),
        sa.Column('output_type', sa.String(length=32), nullable=False),
        sa.Column('content', sa.Text(), nullable=False, server_default=''),
        sa.Column('sequence', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('output_metadata', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['notebook_id'], ['notebooks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_execution_outputs_execution_id'), 'execution_outputs', ['execution_id'], unique=False)
    op.create_index(op.f('ix_execution_outputs_session_id'), 'execution_outputs', ['session_id'], unique=False)
    op.create_index(op.f('ix_execution_outputs_notebook_id'), 'execution_outputs', ['notebook_id'], unique=False)
    op.create_index(op.f('ix_execution_outputs_cell_id'), 'execution_outputs', ['cell_id'], unique=False)
    op.create_index(op.f('ix_execution_outputs_output_type'), 'execution_outputs', ['output_type'], unique=False)
    op.create_index('ix_execution_outputs_exec_seq', 'execution_outputs', ['execution_id', 'sequence'], unique=False)
    op.create_index('ix_execution_outputs_cell_seq', 'execution_outputs', ['cell_id', 'sequence'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_execution_outputs_cell_seq', table_name='execution_outputs')
    op.drop_index('ix_execution_outputs_exec_seq', table_name='execution_outputs')
    op.drop_index(op.f('ix_execution_outputs_output_type'), table_name='execution_outputs')
    op.drop_index(op.f('ix_execution_outputs_cell_id'), table_name='execution_outputs')
    op.drop_index(op.f('ix_execution_outputs_notebook_id'), table_name='execution_outputs')
    op.drop_index(op.f('ix_execution_outputs_session_id'), table_name='execution_outputs')
    op.drop_index(op.f('ix_execution_outputs_execution_id'), table_name='execution_outputs')
    op.drop_table('execution_outputs')
