"""add_role_and_is_ready_columns

Revision ID: c1d2e3f4a5b6
Revises: b1c2d3e4f5a6
Create Date: 2026-01-16 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # annotators テーブルに role カラムを追加
    # デフォルト値 'annotator' で既存レコードも更新される
    op.add_column(
        'annotators',
        sa.Column('role', sa.String(length=20), nullable=False,
                  server_default='annotator')
    )

    # vitality_annotations テーブルに is_ready カラムを追加
    # デフォルト値 FALSE で既存レコードも更新される
    op.add_column(
        'vitality_annotations',
        sa.Column('is_ready', sa.Boolean(), nullable=False,
                  server_default=sa.text('FALSE'))
    )

    # vitality_value カラムを NULL 許容に変更
    # is_ready のみ設定する場合のため
    op.alter_column(
        'vitality_annotations',
        'vitality_value',
        existing_type=sa.Integer(),
        nullable=True
    )

    # is_ready カラムにインデックスを作成
    op.create_index(
        'idx_vitality_annotations_is_ready',
        'vitality_annotations',
        ['is_ready']
    )


def downgrade() -> None:
    # is_ready インデックスを削除
    op.drop_index(
        'idx_vitality_annotations_is_ready',
        table_name='vitality_annotations'
    )

    # vitality_value カラムを NOT NULL に戻す
    # 注意: NULL 値が存在する場合はエラーになる
    op.alter_column(
        'vitality_annotations',
        'vitality_value',
        existing_type=sa.Integer(),
        nullable=False
    )

    # is_ready カラムを削除
    op.drop_column('vitality_annotations', 'is_ready')

    # role カラムを削除
    op.drop_column('annotators', 'role')
