"""Add revoked_tokens.updated_at (present in the model, missing from migration 001).

Revision ID: 003_revoked_tokens_updated_at
Revises: 002_soft_delete
Create Date: 2026-10-02
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003_revoked_tokens_updated_at'
down_revision: Union[str, None] = '002_soft_delete'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('revoked_tokens', sa.Column('updated_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('revoked_tokens', 'updated_at')
