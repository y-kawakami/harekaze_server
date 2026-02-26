"""Add bloom_30/bloom_50 vitality columns to entire_trees

Revision ID: 20260226001
Revises: 20260212001
Create Date: 2026-02-26

Requirements: 5.1, 5.2, 5.3
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260226001"
down_revision: Union[str, None] = "20260212001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "entire_trees",
        sa.Column("vitality_bloom_30", sa.Integer(), nullable=True),
    )
    op.add_column(
        "entire_trees",
        sa.Column("vitality_bloom_30_real", sa.Double(), nullable=True),
    )
    op.add_column(
        "entire_trees",
        sa.Column(
            "vitality_bloom_30_weight", sa.Double(), nullable=True,
        ),
    )
    op.add_column(
        "entire_trees",
        sa.Column("vitality_bloom_50", sa.Integer(), nullable=True),
    )
    op.add_column(
        "entire_trees",
        sa.Column("vitality_bloom_50_real", sa.Double(), nullable=True),
    )
    op.add_column(
        "entire_trees",
        sa.Column(
            "vitality_bloom_50_weight", sa.Double(), nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("entire_trees", "vitality_bloom_50_weight")
    op.drop_column("entire_trees", "vitality_bloom_50_real")
    op.drop_column("entire_trees", "vitality_bloom_50")
    op.drop_column("entire_trees", "vitality_bloom_30_weight")
    op.drop_column("entire_trees", "vitality_bloom_30_real")
    op.drop_column("entire_trees", "vitality_bloom_30")
