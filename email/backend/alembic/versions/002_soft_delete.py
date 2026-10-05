"""Add soft delete (deleted_at) to emails table.

Revision ID: 002_soft_delete
Revises: 001_initial_schema
Create Date: 2026-09-30
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_soft_delete'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add soft delete column to emails
    op.add_column('emails', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    op.create_index('ix_emails_deleted_at', 'emails', ['deleted_at'])


def downgrade() -> None:
    op.drop_index('ix_emails_deleted_at', table_name='emails')
    op.drop_column('emails', 'deleted_at')
