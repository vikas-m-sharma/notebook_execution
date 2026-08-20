"""Phase 1 initial baseline migration

Revision ID: 0001_baseline
Revises: 
Create Date: 2026-08-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001_baseline'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Initial baseline upgrade. No business tables created in Phase 1."""
    pass


def downgrade() -> None:
    """Initial baseline downgrade."""
    pass
