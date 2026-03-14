"""add version column to trees

Revision ID: 20260314002
Revises: 20260314001
Create Date: 2026-03-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260314002"
down_revision: Union[str, None] = "20260314001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "trees",
        sa.Column(
            "version",
            sa.Integer(),
            server_default="202501",
            nullable=False,
            comment="年度バージョン",
        ),
    )
    op.create_index(
        "ix_trees_version", "trees", ["version"]
    )


def downgrade() -> None:
    op.drop_index("ix_trees_version", table_name="trees")
    op.drop_column("trees", "version")
