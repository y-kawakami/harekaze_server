"""add bloom dates to entire_trees

Revision ID: 20260314001
Revises: 20260226001
Create Date: 2026-03-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260314001"
down_revision: Union[str, None] = "20260226001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "entire_trees",
        sa.Column(
            "flowering_date",
            sa.Date(),
            nullable=True,
            comment="開花日",
        ),
    )
    op.add_column(
        "entire_trees",
        sa.Column(
            "bloom_30_date",
            sa.Date(),
            nullable=True,
            comment="3分咲き日",
        ),
    )
    op.add_column(
        "entire_trees",
        sa.Column(
            "bloom_50_date",
            sa.Date(),
            nullable=True,
            comment="5分咲き日",
        ),
    )
    op.add_column(
        "entire_trees",
        sa.Column(
            "full_bloom_date",
            sa.Date(),
            nullable=True,
            comment="満開開始日",
        ),
    )
    op.add_column(
        "entire_trees",
        sa.Column(
            "full_bloom_end_date",
            sa.Date(),
            nullable=True,
            comment="満開終了日",
        ),
    )


def downgrade() -> None:
    op.drop_column("entire_trees", "full_bloom_end_date")
    op.drop_column("entire_trees", "full_bloom_date")
    op.drop_column("entire_trees", "bloom_50_date")
    op.drop_column("entire_trees", "bloom_30_date")
    op.drop_column("entire_trees", "flowering_date")
