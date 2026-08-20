"""Phase 10 Data Connectors schema migration

Revision ID: 0005_data_connectors
Revises: 0004_dependency_management
Create Date: 2026-08-16 19:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0005_data_connectors'
down_revision: Union[str, None] = '0004_dependency_management'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create credentials table
    op.create_table(
        'credentials',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('credential_id', sa.String(length=64), nullable=False),
        sa.Column('credential_type', sa.String(length=64), nullable=False),
        sa.Column('encrypted_payload', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('credential_id')
    )
    op.create_index(op.f('ix_credentials_credential_id'), 'credentials', ['credential_id'], unique=True)

    # 2. Create connectors table
    op.create_table(
        'connectors',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('connector_type', sa.String(length=64), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False),
        sa.Column('configuration', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
        sa.Column('credential_id', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='CREATED'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_connectors_name'), 'connectors', ['name'], unique=True)
    op.create_index(op.f('ix_connectors_connector_type'), 'connectors', ['connector_type'], unique=False)
    op.create_index(op.f('ix_connectors_category'), 'connectors', ['category'], unique=False)
    op.create_index(op.f('ix_connectors_credential_id'), 'connectors', ['credential_id'], unique=False)
    op.create_index(op.f('ix_connectors_status'), 'connectors', ['status'], unique=False)


def downgrade() -> None:
    # Drop connectors table
    op.drop_index(op.f('ix_connectors_status'), table_name='connectors')
    op.drop_index(op.f('ix_connectors_credential_id'), table_name='connectors')
    op.drop_index(op.f('ix_connectors_category'), table_name='connectors')
    op.drop_index(op.f('ix_connectors_connector_type'), table_name='connectors')
    op.drop_index(op.f('ix_connectors_name'), table_name='connectors')
    op.drop_table('connectors')

    # Drop credentials table
    op.drop_index(op.f('ix_credentials_credential_id'), table_name='credentials')
    op.drop_table('credentials')
