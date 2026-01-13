"""add_initial_annotator

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
Create Date: 2026-01-13 18:10:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 初期アノテーターアカウントを作成
    # パスワード: annotation2026
    op.execute(
        """
        INSERT INTO annotators (username, hashed_password, created_at, updated_at)
        VALUES (
            'annotator',
            '$2b$12$3vwh8/hgXWOiyHSFzBdh0eaynagULJNoJUO4dLRnedpK0LU94WZLG',
            NOW(),
            NOW()
        )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM annotators WHERE username = 'annotator'
        """
    )
