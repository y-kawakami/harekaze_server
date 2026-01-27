"""Add bloom_status column to entire_trees table

Revision ID: 20260127001
Revises:
Create Date: 2026-01-27

Requirements: 2.3
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260127001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # bloom_status カラムを追加
    op.add_column(
        "entire_trees",
        sa.Column("bloom_status", sa.String(20), nullable=True)
    )
    # インデックスを作成
    op.create_index(
        "idx_entire_trees_bloom_status",
        "entire_trees",
        ["bloom_status"]
    )


def downgrade() -> None:
    # インデックスを削除
    op.drop_index("idx_entire_trees_bloom_status", table_name="entire_trees")
    # カラムを削除
    op.drop_column("entire_trees", "bloom_status")
