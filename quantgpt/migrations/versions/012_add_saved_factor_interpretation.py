"""add LLM interpretation snapshot to saved factors

Revision ID: 012
Revises: 011
Create Date: 2026-08-26
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("saved_factors", sa.Column("interpretation", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("saved_factors", "interpretation")
