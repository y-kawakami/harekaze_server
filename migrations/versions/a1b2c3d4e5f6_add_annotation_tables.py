"""add_annotation_tables

Revision ID: a1b2c3d4e5f6
Revises: ff4a3030df36
Create Date: 2026-01-13 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'ff4a3030df36'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # annotators テーブルの作成
    op.create_table(
        'annotators',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username')
    )

    # vitality_annotations テーブルの作成
    op.create_table(
        'vitality_annotations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('entire_tree_id', sa.Integer(), nullable=False),
        sa.Column('vitality_value', sa.Integer(), nullable=False),
        sa.Column('annotator_id', sa.Integer(), nullable=False),
        sa.Column('annotated_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['entire_tree_id'], ['entire_trees.id']),
        sa.ForeignKeyConstraint(['annotator_id'], ['annotators.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('entire_tree_id')
    )

    # インデックスの作成
    op.create_index(
        'idx_vitality_annotations_entire_tree_id',
        'vitality_annotations',
        ['entire_tree_id']
    )
    op.create_index(
        'idx_vitality_annotations_vitality_value',
        'vitality_annotations',
        ['vitality_value']
    )
    op.create_index(
        'idx_vitality_annotations_annotator_id',
        'vitality_annotations',
        ['annotator_id']
    )


def downgrade() -> None:
    # インデックスの削除
    op.drop_index(
        'idx_vitality_annotations_annotator_id',
        table_name='vitality_annotations'
    )
    op.drop_index(
        'idx_vitality_annotations_vitality_value',
        table_name='vitality_annotations'
    )
    op.drop_index(
        'idx_vitality_annotations_entire_tree_id',
        table_name='vitality_annotations'
    )

    # テーブルの削除
    op.drop_table('vitality_annotations')
    op.drop_table('annotators')
