"""Add fullview_validation_logs table

Revision ID: 20260212001
Revises: 20260127001
Create Date: 2026-02-12

Requirements: 運用要件（NG 画像・判定結果の永続化）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260212001"
down_revision: Union[str, None] = "20260127001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fullview_validation_logs",
        sa.Column(
            "id", sa.Integer(),
            primary_key=True, autoincrement=True,
        ),
        sa.Column(
            "uid", sa.String(36),
            unique=True, nullable=False,
        ),
        sa.Column(
            "image_obj_key", sa.String(255),
            nullable=False, comment="S3 画像キー",
        ),
        sa.Column(
            "is_valid", sa.Boolean(),
            nullable=False,
            comment="判定結果（True=OK, False=NG）",
        ),
        sa.Column(
            "reason", sa.Text(),
            nullable=False, comment="判定理由",
        ),
        sa.Column(
            "confidence", sa.Double(),
            nullable=False,
            comment="信頼度（0.0〜1.0）",
        ),
        sa.Column(
            "model_id", sa.String(255),
            nullable=False,
            comment="使用した Bedrock モデル ID",
        ),
        sa.Column(
            "created_at", sa.DateTime(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_fvlog_is_valid",
        "fullview_validation_logs",
        ["is_valid"],
    )
    op.create_index(
        "idx_fvlog_created_at",
        "fullview_validation_logs",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_fvlog_created_at",
        table_name="fullview_validation_logs",
    )
    op.drop_index(
        "idx_fvlog_is_valid",
        table_name="fullview_validation_logs",
    )
    op.drop_table("fullview_validation_logs")
